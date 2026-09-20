"""Manipulation → distribution research on 1m candles.

Model (ICT power-of-three / Judas swing):
  1. Manipulation: price sweeps a liquidity level (PDH/PDL, session H/L,
     swing point) — breaks it, takes the stops...
  2. ...then closes back through the level within CONFIRM_N bars (failed
     breakout = confirmed manipulation).
  3. Distribution: the real move runs the OTHER way, reputedly 1x-2.5x the
     manipulation move, toward the nearest opposite liquidity, at a slower
     pace than the manipulation spike.

This script measures those claims and prints the numbers:
  - manipulation rate (confirmed sweeps vs genuine breakouts)
  - distribution-leg multiple of the manipulation move (P(>=1x)..P(>=3x))
  - % reaching the nearest opposite liquidity level
  - velocity ratio (manipulation speed / distribution speed)
  - trade expectancy: enter at confirmation close, SL beyond the sweep
    extreme, TP at k * manipulation — for k in 1.0/1.5/2.0/2.5

Usage:
  python manipulation_research.py            # XAUUSD (GC=F) 1m, last ~25d
  python manipulation_research.py --btc      # BTC_USD 1m parquet (~18 months)
"""

from dataclasses import dataclass, field
import sys

import pandas as pd

BTC_PARQUET = ("/Users/anilmaity/PycharmProjects/Kronos/KronosStrategies/"
               "btc_research/cache/BTC_USD_1m.parquet")

SWING_K = 10          # fractal half-width for swing levels
CONFIRM_N = 15        # bars allowed to close back through the level
LEG_LOOKBACK = 30     # bars before the break defining the manipulation leg origin
HORIZON = 240         # bars tracked after confirmation (4h)
LEVEL_TTL = 1440      # swing/session level lifetime in bars (1 day)
TARGETS = (1.0, 1.5, 2.0, 2.5)
SESSIONS = (("asia", 0, 7), ("london", 7, 12), ("ny", 12, 21))  # UTC hours


@dataclass
class Level:
    price: float
    side: str            # 'high' (buy-side liquidity) | 'low' (sell-side)
    kind: str            # 'PD' | 'session' | 'swing'
    born: int
    break_i: int | None = None
    extreme: float = 0.0


@dataclass
class Event:
    conf_i: int
    direction: str       # 'down' = high swept -> expect down move
    kind: str
    level: float
    extreme: float
    m_pen: float         # extreme beyond level
    m_leg: float         # full manipulation leg (origin -> extreme)
    manip_bars: int
    entry: float         # confirmation close
    stats: dict = field(default_factory=dict)


def fetch_xau_1m() -> pd.DataFrame:
    import yfinance as yf
    frames = []
    for back in range(4):
        df = yf.download("GC=F", interval="1m",
                         start=pd.Timestamp.utcnow().floor("D") - pd.Timedelta(days=7 * (back + 1) - 1),
                         end=pd.Timestamp.utcnow() - pd.Timedelta(days=7 * back),
                         progress=False, auto_adjust=True)
        if len(df):
            frames.append(df)
    df = pd.concat(frames)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()
    df = df[~df.index.duplicated()].sort_index()
    df.index = df.index.tz_convert("UTC")
    return df.reset_index(names="time")


def load_btc_1m() -> pd.DataFrame:
    df = pd.read_parquet(BTC_PARQUET)[["time", "open", "high", "low", "close"]]
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.sort_values("time").reset_index(drop=True)


def precompute_swings(df: pd.DataFrame, k: int = SWING_K):
    hi, lo = df["high"].values, df["low"].values
    hmax = df["high"].rolling(2 * k + 1, center=True).max().values
    lmin = df["low"].rolling(2 * k + 1, center=True).min().values
    swing_hi = (hi == hmax)
    swing_lo = (lo == lmin)
    return swing_hi, swing_lo


def run(df: pd.DataFrame) -> tuple[list[Event], int]:
    t = df["time"]
    day = t.dt.floor("D").values
    hour = t.dt.hour.values
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    n = len(df)
    swing_hi, swing_lo = precompute_swings(df)

    levels: list[Level] = []
    events: list[Event] = []
    breakouts = 0

    # prior-day and per-session running extremes
    cur_day = None
    day_hi = day_lo = None
    pd_hi = pd_lo = None
    sess_state = {}   # name -> [hi, lo, active]

    for i in range(n):
        # ---- day rollover: prior-day levels
        if day[i] != cur_day:
            if day_hi is not None:
                pd_hi, pd_lo = day_hi, day_lo
                levels = [lv for lv in levels if lv.kind != "PD"]
                levels.append(Level(pd_hi, "high", "PD", i))
                levels.append(Level(pd_lo, "low", "PD", i))
            cur_day, day_hi, day_lo = day[i], h[i], l[i]
            sess_state = {}
        else:
            day_hi, day_lo = max(day_hi, h[i]), min(day_lo, l[i])

        # ---- session rollover: completed-session levels
        for name, start, end in SESSIONS:
            if start <= hour[i] < end:
                st = sess_state.setdefault(name, [h[i], l[i]])
                st[0], st[1] = max(st[0], h[i]), min(st[1], l[i])
            elif name in sess_state and hour[i] >= end:
                st = sess_state.pop(name)
                levels.append(Level(st[0], "high", "session", i))
                levels.append(Level(st[1], "low", "session", i))

        # ---- swing levels (confirmed k bars later -> no lookahead)
        j = i - SWING_K
        if j >= 0:
            if swing_hi[j]:
                levels.append(Level(h[j], "high", "swing", i))
            if swing_lo[j]:
                levels.append(Level(l[j], "low", "swing", i))

        # ---- sweep state machine
        confirmed_here: list[tuple[Level, float]] = []
        kill: list[Level] = []
        for lv in levels:
            if lv.kind != "PD" and i - lv.born > LEVEL_TTL:
                kill.append(lv)
                continue
            if lv.break_i is None:
                if lv.side == "high" and h[i] > lv.price:
                    lv.break_i, lv.extreme = i, h[i]
                elif lv.side == "low" and l[i] < lv.price:
                    lv.break_i, lv.extreme = i, l[i]
            else:
                lv.extreme = max(lv.extreme, h[i]) if lv.side == "high" else min(lv.extreme, l[i])
                back_through = c[i] < lv.price if lv.side == "high" else c[i] > lv.price
                if back_through:
                    confirmed_here.append((lv, lv.extreme))
                    kill.append(lv)
                elif i - lv.break_i >= CONFIRM_N:
                    breakouts += 1
                    kill.append(lv)
        for lv in kill:
            levels.remove(lv)

        # ---- record one event per confirmation bar (deepest penetration wins)
        if confirmed_here:
            lv, extreme = max(confirmed_here, key=lambda x: abs(x[1] - x[0].price))
            m_pen = abs(extreme - lv.price)
            if m_pen <= 0:
                continue
            lo0 = max(0, lv.break_i - LEG_LOOKBACK)
            if lv.side == "high":
                origin = l[lo0: lv.break_i + 1].min()
                m_leg = extreme - origin
                direction = "down"
            else:
                origin = h[lo0: lv.break_i + 1].max()
                m_leg = origin - extreme
                direction = "up"
            events.append(Event(
                conf_i=i, direction=direction, kind=lv.kind, level=lv.price,
                extreme=extreme, m_pen=m_pen, m_leg=m_leg,
                manip_bars=i - lv.break_i + 1, entry=c[i],
                stats={"nearest_liq": nearest_opposite(levels, c[i], direction)},
            ))

    # ---- forward measurement per event
    for ev in events:
        fwd_end = min(ev.conf_i + HORIZON, n)
        fh, fl = h[ev.conf_i + 1: fwd_end], l[ev.conf_i + 1: fwd_end]
        if not len(fh):
            ev.stats["valid"] = False
            continue
        ev.stats["valid"] = True
        sign = -1 if ev.direction == "down" else 1
        mfe = (ev.entry - fl.min()) if sign < 0 else (fh.max() - ev.entry)
        ev.stats["mfe"] = mfe
        ev.stats["mult_pen"] = mfe / ev.m_pen
        ev.stats["mult_leg"] = mfe / ev.m_leg if ev.m_leg > 0 else float("nan")
        nl = ev.stats["nearest_liq"]
        ev.stats["reached_liq"] = (nl is not None and
                                   ((fl.min() <= nl) if sign < 0 else (fh.max() >= nl)))
        # speed: manipulation pts/bar vs distribution pts/bar (to MFE point)
        mfe_bar = (fl.argmin() if sign < 0 else fh.argmax()) + 1
        ev.stats["v_manip"] = ev.m_leg / ev.manip_bars
        ev.stats["v_dist"] = mfe / mfe_bar
        # trade sim: SL beyond extreme (+10% of pen buffer), TP at k*m_pen
        stop = ev.extreme - sign * 0.1 * ev.m_pen
        risk = abs(stop - ev.entry)
        for k in TARGETS:
            tp = ev.entry + sign * k * ev.m_pen
            outcome = None
            for x in range(len(fh)):
                hit_sl = fh[x] >= stop if sign < 0 else fl[x] <= stop
                hit_tp = fl[x] <= tp if sign < 0 else fh[x] >= tp
                if hit_sl and hit_tp:
                    outcome = "SL"     # conservative: both in one bar
                elif hit_sl:
                    outcome = "SL"
                elif hit_tp:
                    outcome = "TP"
                if outcome:
                    break
            ev.stats[f"t{k}"] = outcome or "NONE"
            ev.stats[f"r{k}"] = (k * ev.m_pen / risk) if risk > 0 else float("nan")
    return events, breakouts


def nearest_opposite(levels: list[Level], px: float, direction: str) -> float | None:
    if direction == "down":
        below = [lv.price for lv in levels if lv.side == "low" and lv.price < px]
        return max(below) if below else None
    above = [lv.price for lv in levels if lv.side == "high" and lv.price > px]
    return min(above) if above else None


def report(events: list[Event], breakouts: int, label: str) -> None:
    ev = [e for e in events if e.stats.get("valid")]
    total_breaks = len(events) + breakouts
    print(f"\n══ {label} ══")
    print(f"level breaks={total_breaks}  confirmed manipulations={len(events)} "
          f"({100 * len(events) / max(1, total_breaks):.0f}%)  genuine breakouts={breakouts}")
    if not ev:
        return
    s = pd.DataFrame([e.stats | {"kind": e.kind, "dir": e.direction,
                                 "m_pen": e.m_pen, "m_leg": e.m_leg} for e in ev])
    print(f"\nmanipulation size: pen median={s.m_pen.median():.2f}  "
          f"leg median={s.m_leg.median():.2f}")
    print("\ndistribution multiple of manipulation (MFE within 4h):")
    for col, name in (("mult_pen", "vs penetration"), ("mult_leg", "vs full leg")):
        q = s[col].quantile([.25, .5, .75])
        probs = "  ".join(f"P(>={k}x)={100 * (s[col] >= k).mean():.0f}%"
                          for k in (1, 1.5, 2, 2.5, 3))
        print(f"  {name:15s} median={q[.5]:.2f}x  IQR={q[.25]:.2f}-{q[.75]:.2f}x   {probs}")
    has_liq = s.nearest_liq.notna()
    print(f"\nreached nearest opposite liquidity: "
          f"{100 * s[has_liq].reached_liq.mean():.0f}% "
          f"(of {has_liq.sum()} events with a mapped target)")
    vr = (s.v_manip / s.v_dist).replace([float("inf")], float("nan")).dropna()
    print(f"speed: manipulation is {vr.median():.1f}x faster than distribution "
          f"(median; IQR {vr.quantile(.25):.1f}-{vr.quantile(.75):.1f}x)")
    print("\ntrade sim — entry at confirmation close, SL 10% beyond sweep extreme:")
    for k in TARGETS:
        col, rcol = s[f"t{k}"], s[f"r{k}"]
        done = col.isin(["TP", "SL"])
        wr = (col[done] == "TP").mean() if done.any() else 0
        rr = rcol[done].median() if done.any() else float("nan")
        expc = wr * rr - (1 - wr)
        print(f"  TP {k}x pen:  WR={100 * wr:.0f}%  medianR={rr:.2f}  "
              f"expectancy={expc:+.2f}R  (resolved {done.sum()}/{len(s)})")
    print("\nby level kind:")
    for kind, g in s.groupby("kind"):
        print(f"  {kind:8s} n={len(g):4d}  median mult_pen={g.mult_pen.median():.2f}x  "
              f"P(>=1x)={100 * (g.mult_pen >= 1).mean():.0f}%")


if __name__ == "__main__":
    if "--btc" in sys.argv:
        df, label = load_btc_1m(), "BTC_USD 1m (parquet)"
    else:
        df, label = fetch_xau_1m(), "XAUUSD (GC=F) 1m"
    print(f"{label}: {len(df):,} bars  {df['time'].iloc[0]} → {df['time'].iloc[-1]}")
    events, breakouts = run(df)
    report(events, breakouts, label)
    out = pd.DataFrame([{
        "time": df["time"].iloc[e.conf_i], "dir": e.direction, "kind": e.kind,
        "level": e.level, "extreme": e.extreme, "m_pen": e.m_pen, "m_leg": e.m_leg,
        "manip_bars": e.manip_bars, **e.stats} for e in events])
    name = "manip_events_btc.csv" if "--btc" in sys.argv else "manip_events_xau.csv"
    out.to_csv(name, index=False)
    print(f"\nsaved {name} ({len(out)} events)")
