"""s5x_session_range.py — session-structure plays with tight structural stops.

Sub-models (all signals on 1-min resampled MID closes, mapped back to S5 bars;
engine executes from S5 bar signal_i+1, so everything is causal):

  (a) asia  — Asia range (00:00-06:00 UTC) sweep-and-reclaim fade in 07:00-10:00.
              Sweep = 1m high/low beyond the range extreme; reclaim = 1m close back
              inside. Fade toward the midpoint. SL beyond sweep extreme (structural,
              buffered) OR fixed-pt (comparison). TP = range mid or quarter-line.
              Hold <= 8h.
  (b) ny    — NY-open 15-min range (13:30-13:45 UTC). First excursion decides:
              close beyond = break -> maker retest limit at the range edge;
              close back inside = false-break fade toward mid / opposite edge.
              SL beyond the range / the false-break extreme. Hold <= 4h.
  (c) roll  — Rollover fade 22:00-23:59 UTC: burst >= X pts within 10 min is faded
              back to the pre-burst price. SL fixed 2-3 pts or structural beyond
              the burst extreme. Hold <= 2h.

Sweep is TRAIN-ONLY for selection; test block reported verbatim once at the end.
"""
from __future__ import annotations

import time as _clock

import numpy as np
import pandas as pd

import s5_engine as eng

T0 = _clock.time()

HOLD_A = 5760   # 8h in S5 bars
HOLD_B = 2880   # 4h
HOLD_C = 1440   # 2h

print("loading S5 ...", flush=True)
df = eng.load_s5()
times = df["time"].values
n_s5 = len(df)

m1 = eng.resample(df, "1min").reset_index()          # time = minute start
m_end = m1["time"].values + np.timedelta64(60, "s")   # minute close time
m1["sig_i"] = np.searchsorted(times, m_end) - 1       # last S5 bar closed <= minute close
m1 = m1[m1["sig_i"] >= 0].reset_index(drop=True)
di = pd.DatetimeIndex(m1["time"])
m1["date"] = di.normalize()
m1["hh"] = di.hour
m1["mm"] = di.minute
print(f"  {n_s5} S5 bars, {len(m1)} 1-min bars  ({_clock.time()-T0:.1f}s)", flush=True)

# ─────────────────────────────── event generation ───────────────────────────────

def asia_events() -> list[dict]:
    """One sweep-reclaim event max per side per day."""
    evs = []
    for _, day in m1.groupby("date", sort=True):
        asia = day[(day.hh >= 0) & (day.hh < 6)]
        if len(asia) < 180:
            continue
        ah, al = float(asia.h.max()), float(asia.l.min())
        rng = ah - al
        if rng < 1.0:
            continue
        amid = (ah + al) / 2.0
        win = day[(day.hh >= 7) & (day.hh < 10)]
        swept_hi, hi_ext, done_s = False, -np.inf, False
        swept_lo, lo_ext, done_l = False, np.inf, False
        for r in win.itertuples():
            if not done_s:
                if r.h > ah:
                    swept_hi, hi_ext = True, max(hi_ext, r.h)
                if swept_hi and r.c < ah:
                    evs.append(dict(sig_i=int(r.sig_i), side="sell", ext=hi_ext,
                                    edge=ah, mid=amid, rng=rng, ref=float(r.c)))
                    done_s = True
            if not done_l:
                if r.l < al:
                    swept_lo, lo_ext = True, min(lo_ext, r.l)
                if swept_lo and r.c > al:
                    evs.append(dict(sig_i=int(r.sig_i), side="buy", ext=lo_ext,
                                    edge=al, mid=amid, rng=rng, ref=float(r.c)))
                    done_l = True
            if done_s and done_l:
                break
    return evs


def ny_events() -> list[dict]:
    """First excursion beyond the 13:30-13:45 range decides brt vs fade. One/day."""
    evs = []
    for _, day in m1.groupby("date", sort=True):
        orb = day[(day.hh == 13) & (day.mm >= 30) & (day.mm < 45)]
        if len(orb) < 10:
            continue
        orh, orl = float(orb.h.max()), float(orb.l.min())
        rng = orh - orl
        if rng < 0.5:
            continue
        mid = (orh + orl) / 2.0
        win = day[((day.hh == 13) & (day.mm >= 45)) | ((day.hh >= 14) & (day.hh < 16))]
        for r in win.itertuples():
            up, dn = r.h > orh, r.l < orl
            if not (up or dn):
                continue
            if up and dn:      # both sides in one minute — ambiguous, skip day
                break
            base = dict(orh=orh, orl=orl, rng=rng, mid=mid, sig_i=int(r.sig_i))
            if up:
                if r.c > orh:   # confirmed break up -> retest long
                    evs.append(dict(base, mode="brt", side="buy", ref=float(r.c)))
                else:           # false break up -> fade short
                    evs.append(dict(base, mode="fade", side="sell", ext=float(r.h), ref=float(r.c)))
            else:
                if r.c < orl:
                    evs.append(dict(base, mode="brt", side="sell", ref=float(r.c)))
                else:
                    evs.append(dict(base, mode="fade", side="buy", ext=float(r.l), ref=float(r.c)))
            break               # first excursion only
    return evs


def roll_events(burst_pts: float) -> list[dict]:
    """22:00-23:59 UTC: fade a >=burst_pts move over the last 10 contiguous minutes."""
    evs = []
    for _, day in m1.groupby("date", sort=True):
        win = day[day.hh >= 22].reset_index(drop=True)
        if len(win) < 15:
            continue
        c, h, l = win.c.values, win.h.values, win.l.values
        tt, si = win.time.values, win.sig_i.values
        cooldown = -1
        for j in range(10, len(win)):
            if j <= cooldown:
                continue
            if (tt[j] - tt[j - 10]) > np.timedelta64(11, "m"):
                continue        # gap — not a real 10-min window
            move = c[j] - c[j - 10]
            if move >= burst_pts:
                evs.append(dict(sig_i=int(si[j]), side="sell", pre=float(c[j - 10]),
                                ext=float(h[j - 9:j + 1].max()), ref=float(c[j])))
                cooldown = j + 15
            elif move <= -burst_pts:
                evs.append(dict(sig_i=int(si[j]), side="buy", pre=float(c[j - 10]),
                                ext=float(l[j - 9:j + 1].min()), ref=float(c[j])))
                cooldown = j + 15
    return evs


EV_A = asia_events()
EV_B = ny_events()
EV_C = {bp: roll_events(bp) for bp in (1.5, 2.0, 2.5)}
print(f"events: asia={len(EV_A)}  ny={len(EV_B)}  "
      f"roll={{{', '.join(f'{k}:{len(v)}' for k, v in EV_C.items())}}}  "
      f"({_clock.time()-T0:.1f}s)", flush=True)

# ─────────────────────────────── intent builders ───────────────────────────────

def build_asia(sl_mode: str, buf_or_fix: float, tp_mode: str) -> list[eng.OrderIntent]:
    its = []
    for e in EV_A:
        s = e["side"] == "sell"
        if sl_mode == "struct":
            sl = e["ext"] + buf_or_fix if s else e["ext"] - buf_or_fix
        else:
            sl = e["ref"] + buf_or_fix if s else e["ref"] - buf_or_fix
        if tp_mode == "mid":
            tp = e["mid"]
        else:  # quarter-line: halfway between the swept edge and the mid
            tp = e["edge"] - 0.25 * e["rng"] if s else e["edge"] + 0.25 * e["rng"]
        if s and not (tp < e["ref"] - 0.10 and sl > e["ref"] + 0.05):
            continue
        if not s and not (tp > e["ref"] + 0.10 and sl < e["ref"] - 0.05):
            continue
        its.append(eng.OrderIntent(signal_i=e["sig_i"], side=e["side"], tp=tp, sl=sl,
                                   max_hold_bars=HOLD_A, lot=0.10, tag="asia"))
    return its


def build_ny(mode: str, buf: float, tp_mode_or_mult) -> list[eng.OrderIntent]:
    its = []
    for e in EV_B:
        if e["mode"] != mode:
            continue
        s = e["side"] == "sell"
        if mode == "fade":
            sl = e["ext"] + buf if s else e["ext"] - buf
            if tp_mode_or_mult == "mid":
                tp = e["mid"]
            else:  # opposite edge
                tp = e["orl"] if s else e["orh"]
            if s and not (tp < e["ref"] - 0.10 and sl > e["ref"] + 0.05):
                continue
            if not s and not (tp > e["ref"] + 0.10 and sl < e["ref"] - 0.05):
                continue
            its.append(eng.OrderIntent(signal_i=e["sig_i"], side=e["side"], tp=tp, sl=sl,
                                       max_hold_bars=HOLD_B, lot=0.10, tag="ny_fade"))
        else:  # brt — maker retest limit at the broken edge
            edge = e["orh"] if not s else e["orl"]
            sl = (e["orl"] - buf) if not s else (e["orh"] + buf)
            tpm = float(tp_mode_or_mult)
            tp = edge + tpm * e["rng"] if not s else edge - tpm * e["rng"]
            its.append(eng.OrderIntent(signal_i=e["sig_i"], side=e["side"], tp=tp, sl=sl,
                                       max_hold_bars=HOLD_B, lot=0.10,
                                       entry_type="maker", limit_price=edge,
                                       entry_ttl_bars=720, tag="ny_brt"))
    return its


def build_roll(bp: float, sl_mode: str, sl_val: float) -> list[eng.OrderIntent]:
    its = []
    for e in EV_C[bp]:
        s = e["side"] == "sell"
        tp = e["pre"]
        if sl_mode == "struct":
            sl = e["ext"] + sl_val if s else e["ext"] - sl_val
        else:
            sl = e["ref"] + sl_val if s else e["ref"] - sl_val
        if s and not (tp < e["ref"] - 0.20 and sl > e["ref"] + 0.05):
            continue
        if not s and not (tp > e["ref"] + 0.20 and sl < e["ref"] - 0.05):
            continue
        its.append(eng.OrderIntent(signal_i=e["sig_i"], side=e["side"], tp=tp, sl=sl,
                                   max_hold_bars=HOLD_C, lot=0.10, tag="roll"))
    return its

# ─────────────────────────────── the sweep (TRAIN-selected) ───────────────────────────────

configs = []
for sl_mode, v in (("struct", 0.3), ("struct", 0.5), ("struct", 1.0),
                   ("fixed", 2.0), ("fixed", 3.0)):
    for tp in ("mid", "q"):
        configs.append(dict(sub="asia", params=dict(sl_mode=sl_mode, sl_val=v, tp=tp),
                            build=lambda sm=sl_mode, vv=v, t=tp: build_asia(sm, vv, t)))
for buf in (0.3, 0.5, 1.0):
    for tp in ("mid", "opp"):
        configs.append(dict(sub="ny_fade", params=dict(buf=buf, tp=tp),
                            build=lambda b=buf, t=tp: build_ny("fade", b, t)))
for buf in (0.3, 0.5):
    for tpm in (0.5, 1.0):
        configs.append(dict(sub="ny_brt", params=dict(buf=buf, tp_mult=tpm),
                            build=lambda b=buf, t=tpm: build_ny("brt", b, t)))
for bp in (1.5, 2.0, 2.5):
    for sl_mode, v in (("fixed", 2.0), ("fixed", 3.0), ("struct", 0.5), ("struct", 1.0)):
        configs.append(dict(sub="roll", params=dict(burst=bp, sl_mode=sl_mode, sl_val=v),
                            build=lambda bb=bp, sm=sl_mode, vv=v: build_roll(bb, sm, vv)))

print(f"sweeping {len(configs)} configs ...", flush=True)
table = []
for i, cfg in enumerate(configs):
    intents = cfg["build"]()
    fills = eng.simulate(df, intents, spread_model=0.20)
    name = f"{cfg['sub']}:" + ",".join(f"{k}={v}" for k, v in cfg["params"].items())
    st = eng.stats(df, fills, name)
    row = dict(name=name, sub=cfg["sub"], params=cfg["params"],
               n_intents=len(intents),
               train=st.get("train_jan_apr", {}), test=st.get("test_may_jul", {}),
               full=st.get("full", {}))
    table.append(row)
    tr = row["train"]
    print(f"  [{i+1:2d}/{len(configs)}] {name:55s} train: n={tr.get('trades',0):3d} "
          f"wr={tr.get('win_rate','-'):>5} net={tr.get('net','-'):>8} "
          f"exp={tr.get('expectancy','-'):>7}", flush=True)

# selection on TRAIN only (low-frequency family: require >=40 train trades)
elig = [r for r in table if r["train"].get("trades", 0) >= 40]
elig.sort(key=lambda r: r["train"]["expectancy"], reverse=True)
best = elig[:3]

print("\n---- TOP 3 BY TRAIN EXPECTANCY (test read once, verbatim) ----")
for r in best:
    print(f"\n{r['name']}")
    print(f"  TRAIN: {r['train']}")
    print(f"  TEST : {r['test']}")

# worst-case robustness: feed spread for the single best config
feed_row = None
if best:
    b = best[0]
    cfg = next(c for c in configs
               if f"{c['sub']}:" + ",".join(f"{k}={v}" for k, v in c["params"].items()) == b["name"])
    fills = eng.simulate(df, cfg["build"](), spread_model="feed")
    feed_row = eng.stats(df, fills, b["name"] + " [feed]")
    print(f"\nFEED-SPREAD robustness for {b['name']}:")
    print(f"  TRAIN: {feed_row.get('train_jan_apr')}")
    print(f"  TEST : {feed_row.get('test_may_jul')}")

payload = dict(
    family="session_range",
    spread_model=0.20,
    commission_per_lot_rt=4.9,
    lot=0.10,
    n_configs=len(configs),
    events=dict(asia=len(EV_A), ny=len(EV_B),
                roll={str(k): len(v) for k, v in EV_C.items()}),
    sweep_table=table,
    best_by_train_expectancy=[r["name"] for r in best],
    feed_robustness_best=feed_row,
)
path = eng.save_result("session_range", payload)
print(f"\nsaved -> {path}   total {_clock.time()-T0:.1f}s")
