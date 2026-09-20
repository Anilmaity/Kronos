"""
s9x_bt_s95_session_breakout.py
------------------------------
Validation backtest of the REAL strategy module
KronosStrategies/strategies/backtest_strategies/s95_session_breakout.py
(kronos_s95_session_breakout) on XAUUSD M5 mid data (reports/xau_m5_3y.csv).

Faithfulness notes
- Imports the real module and drives its get_signal(w1m, w5m, w15m, now_utc)
  causally, once per closed M5 bar, with now_utc = bar close time.
- The strategy ONLY reads w5m and now_utc (w1m / w15m never touched in the
  code), so w1m/w15m are passed as None -- no M1 synthesis needed.
- Live runner (research_runner.py) calls get_signal even while a position is
  open and place_entry then rejects on max_concurrent=1; that consumes the
  module's per-session _fired dedup. Replicated here: get_signal is always
  called, and its signal is DISCARDED if a position is open.
- cooldown_s=300 == one M5 bar == our call cadence, so it is inherently
  honoured.

Costs (per task spec): 0.20-pt spread cost per round trip, $4.90/lot RT
commission => $0.49 at 0.10 lot, $10/pt at 0.10 lot, conservative same-bar
SL-first, 0.05-pt extra slippage on SL exits. TIME_EXIT (240 min) closes at
the open of the first bar at/after the deadline (position monitor behaviour).

Params are FROZEN as coded. Separate +-20% robustness probes on _RR and
_MAX_RANGE_PTS are reported but not used for the verdict.

Gated-vs-all-day comparison: the module's own session windows (London 07:00,
NY 13:30 UTC) vs a naive all-day variant = identical trigger with "session
opens" anchored every 135 min from 00:00 UTC (same 15-min range + 2h entry
window structure, covering the whole day).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

STRAT_DIR = r"E:\Projects\Kronos\KronosStrategies\strategies"
sys.path.insert(0, STRAT_DIR)

import backtest_strategies.s95_session_breakout as strat  # noqa: E402

HERE = Path(__file__).resolve().parent
CSV = HERE / "reports" / "xau_m5_3y.csv"
OUT_JSON = HERE / "reports" / "s95_session_breakout_validation.json"
OUT_MD = HERE / "reports" / "s95_session_breakout_validation.md"

SPREAD_PTS = 0.20          # full RT spread cost, points
SL_SLIP_PTS = 0.05         # extra adverse slippage on SL exits
COMMISSION_USD = 0.49      # $4.90/lot RT at 0.10 lot
USD_PER_PT = 10.0          # 0.10 lot XAUUSD
WINDOW = 200               # bars passed to get_signal (needs same-day bars only)

TRAIN = ("2023-01-01", "2025-01-01")   # [start, end)
TEST = ("2025-01-01", "2026-07-01")

ALLDAY_SESSIONS = {f"A{i:02d}": m for i, m in enumerate(range(0, 1440, 135))}


def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV)
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close"})
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
    return df


def entry_window_mask(close_min_of_day: np.ndarray, sessions: dict) -> np.ndarray:
    """Bars whose CLOSE time falls inside some session's entry window
    [open+15, open+135) -- the only times get_signal can return a signal."""
    m = np.zeros(len(close_min_of_day), dtype=bool)
    for open_m in sessions.values():
        lo, hi = open_m + 15, open_m + 15 + 120
        m |= (close_min_of_day >= lo) & (close_min_of_day < hi)
    return m


def run_engine(df: pd.DataFrame, sessions: dict | None = None) -> list[dict]:
    """Causal replay. Returns trade list. Patches strat._SESSIONS if given."""
    orig_sessions = strat._SESSIONS
    if sessions is not None:
        strat._SESSIONS = sessions
    strat.reset_state()

    close_times = df["time"] + pd.Timedelta(minutes=5)  # tz-aware, for get_signal
    times_naive = df["time"].dt.tz_localize(None)
    close_naive = close_times.dt.tz_localize(None)
    times = times_naive.to_numpy()                      # datetime64[ns] (UTC)
    ct = close_naive.to_numpy()
    cmod = (close_times.dt.hour * 60 + close_times.dt.minute).to_numpy()
    eligible = entry_window_mask(cmod, sessions or strat._SESSIONS)
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    opens = df["open"].to_numpy()
    closes = df["close"].to_numpy()

    trades: list[dict] = []
    pos = None  # dict(side, entry, sl, tp, deadline, entry_time, reason)

    n = len(df)
    for i in range(n):
        # ── exits first (position monitor runs continuously) ────────────────
        if pos is not None:
            exit_px = exit_reason = None
            if times[i] >= pos["deadline"]:
                exit_px, exit_reason = opens[i], "TIME_EXIT"
            elif pos["side"] == "BUY":
                if lows[i] <= pos["sl"]:
                    exit_px, exit_reason = pos["sl"], "SL"       # SL-first
                elif highs[i] >= pos["tp"]:
                    exit_px, exit_reason = pos["tp"], "TP"
            else:
                if highs[i] >= pos["sl"]:
                    exit_px, exit_reason = pos["sl"], "SL"
                elif lows[i] <= pos["tp"]:
                    exit_px, exit_reason = pos["tp"], "TP"
            if exit_px is not None:
                trades.append(close_trade(pos, exit_px, exit_reason, ct[i]))
                pos = None

        # ── signal on this closed bar ────────────────────────────────────────
        if not eligible[i]:
            continue
        w5m = df.iloc[max(0, i - WINDOW + 1): i + 1]
        now_utc = close_times.iloc[i]
        sig = strat.get_signal(None, w5m, None, now_utc)
        if sig is None:
            continue
        if pos is not None:
            continue  # live: place_entry rejects on max_concurrent=1; _fired consumed
        pos = {
            "side": sig.side,
            "entry": sig.entry_price,
            "sl": sig.stop_loss,
            "tp": sig.take_profit,
            "entry_time": close_naive.iloc[i],
            "deadline": (close_naive.iloc[i]
                         + pd.Timedelta(minutes=sig.max_hold_min)).to_numpy(),
            "reason": sig.reason,
        }

    if pos is not None:  # force-close at data end
        trades.append(close_trade(pos, closes[-1], "EOD_FORCE", ct[-1]))

    strat._SESSIONS = orig_sessions
    strat.reset_state()
    return trades


def close_trade(pos, exit_px, reason, exit_time) -> dict:
    d = 1.0 if pos["side"] == "BUY" else -1.0
    gross = (float(exit_px) - pos["entry"]) * d
    net_pts = gross - SPREAD_PTS - (SL_SLIP_PTS if reason == "SL" else 0.0)
    return {
        "entry_time": str(pos["entry_time"]),
        "exit_time": str(pd.Timestamp(exit_time)),
        "side": pos["side"],
        "entry": pos["entry"],
        "sl": pos["sl"],
        "tp": pos["tp"],
        "exit": float(exit_px),
        "exit_reason": reason,
        "signal": pos["reason"],
        "gross_pts": round(gross, 3),
        "net_pts": round(net_pts, 3),
        "net_usd": round(net_pts * USD_PER_PT - COMMISSION_USD, 2),
    }


def metrics(trades: list[dict]) -> dict:
    if not trades:
        return {"trades": 0, "net_usd": 0.0, "pf": None, "expectancy_usd": None}
    pnl = np.array([t["net_usd"] for t in trades])
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    eq = np.cumsum(pnl)
    dd = float(np.max(np.maximum.accumulate(eq) - eq))
    months = defaultdict(float)
    for t in trades:
        months[t["exit_time"][:7]] += t["net_usd"]
    net = float(pnl.sum())
    max_month = max(months.values()) if months else 0.0
    reasons = defaultdict(int)
    sess = defaultdict(lambda: {"n": 0, "usd": 0.0})
    for t in trades:
        reasons[t["exit_reason"]] += 1
        s = t["signal"].split("_")[1]
        sess[s]["n"] += 1
        sess[s]["usd"] = round(sess[s]["usd"] + t["net_usd"], 2)
    return {
        "trades": int(len(pnl)),
        "wins": int((pnl > 0).sum()),
        "win_rate": round(float((pnl > 0).mean()), 4),
        "net_pts": round(float(sum(t["net_pts"] for t in trades)), 2),
        "net_usd": round(net, 2),
        "expectancy_usd": round(float(pnl.mean()), 3),
        "pf": (round(float(wins.sum() / -losses.sum()), 3)
               if losses.sum() < 0 else None),
        "avg_win_usd": round(float(wins.mean()), 2) if len(wins) else None,
        "avg_loss_usd": round(float(losses.mean()), 2) if len(losses) else None,
        "max_dd_usd": round(dd, 2),
        "exit_reasons": dict(reasons),
        "by_session": {k: v for k, v in sess.items()},
        "monthly_net_usd": {k: round(v, 2) for k, v in sorted(months.items())},
        "max_month_usd": round(max_month, 2),
        "max_month_share_of_net": (round(max_month / net, 3) if net > 0 else None),
        "long_short": {
            "long": int(sum(1 for t in trades if t["side"] == "BUY")),
            "short": int(sum(1 for t in trades if t["side"] == "SELL")),
        },
    }


def slice_period(df, period):
    lo = pd.Timestamp(period[0], tz="UTC")
    hi = pd.Timestamp(period[1], tz="UTC")
    return df[(df["time"] >= lo) & (df["time"] < hi)].reset_index(drop=True)


def main():
    df = load_data()
    print(f"data: {len(df)} bars  {df['time'].iloc[0]} .. {df['time'].iloc[-1]}")

    results = {"strategy": strat.NAME, "data": str(CSV),
               "costs": {"spread_pts": SPREAD_PTS, "sl_slip_pts": SL_SLIP_PTS,
                         "commission_usd_rt": COMMISSION_USD, "usd_per_pt": USD_PER_PT,
                         "lot": 0.10},
               "periods": {"train": TRAIN, "test": TEST}}

    for tag, period in (("train", TRAIN), ("test", TEST)):
        d = slice_period(df, period)
        tr = run_engine(d)
        results[f"gated_{tag}"] = metrics(tr)
        results[f"gated_{tag}_trades"] = tr
        print(f"gated {tag}: {results[f'gated_{tag}']['trades']} trades  "
              f"net ${results[f'gated_{tag}']['net_usd']}")

    # naive all-day variant (same trigger, opens every 135 min)
    for tag, period in (("train", TRAIN), ("test", TEST)):
        d = slice_period(df, period)
        tr = run_engine(d, sessions=ALLDAY_SESSIONS)
        results[f"allday_{tag}"] = metrics(tr)
        print(f"allday {tag}: {results[f'allday_{tag}']['trades']} trades  "
              f"net ${results[f'allday_{tag}']['net_usd']}")

    # robustness probes (+-20% on _RR and _MAX_RANGE_PTS), gated, both periods
    rob = {}
    for pname, base in (("_RR", strat._RR), ("_MAX_RANGE_PTS", strat._MAX_RANGE_PTS)):
        for mult in (0.8, 1.2):
            setattr(strat, pname, base * mult)
            key = f"{pname}={base * mult:g}"
            rob[key] = {}
            for tag, period in (("train", TRAIN), ("test", TEST)):
                tr = run_engine(slice_period(df, period))
                m = metrics(tr)
                rob[key][tag] = {k: m.get(k) for k in
                                 ("trades", "net_usd", "pf", "expectancy_usd", "win_rate")}
            setattr(strat, pname, base)
            print(f"robust {key}: test net ${rob[key]['test']['net_usd']}")
    results["robustness_gated"] = rob

    OUT_JSON.write_text(json.dumps(results, indent=1))
    print(f"saved {OUT_JSON}")


if __name__ == "__main__":
    main()
