"""body-close-confirmation (guests: AP gjoRPszj-Qk, $niper 5aRB_ZY3474) -> gate_test.

Claim: once a wick has pierced a level (and the body closed back), the level counts as
broken only when a later body closes beyond that WICK's extreme, not merely beyond the
level. The concept's second measurable: "difference in outcome between entering on the
level break versus on the body close beyond the wick". claim '+': the wick-extreme close
is the better break entry.

Reading (declared before the first run):
  * 15m bars; level = a fractal 2/2 swing low (bearish break) / swing high (bullish),
    known at the close of the bar two after it; watched for 96 bars (24h) after confirmation.
  * First bar to trade beyond the level must be a WICK-only pierce (closes back on the
    original side), else no setup (the level was never defended). The reference extreme
    is the furthest wick of all wick-only pierces before the first body close beyond the
    level ("no rule for how many wicks accumulate" -> declared: running extreme).
  * Level arm (mask False): the first 15m body close beyond the level, when that close is
    NOT also beyond the wick extreme (setups where the two coincide are dropped - both
    rules take the same trade there).
  * Wick arm (mask True): the first later 15m close beyond the wick extreme, same window.
  * Both arms: trade in the break direction at the next M1 open after the bar's close;
    stop at the breaking bar's opposite extreme (its high for a short); 2R; hold 150 min.
  * cluster = the level id.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _common import swings22, from_ns  # noqa: E402

CID = "body-close-confirmation"
TF = "15min"
WATCH = 96
RR = 2.0
MAX_HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "beyond_wick",
        "level_id", "level_px", "wick_px"]


def _scan_short(h, l, c, sl_idx, n):
    """Bearish breaks of swing lows (bullish handled by the caller via negation)."""
    rows = []
    for i in sl_idx:
        L = l[i]
        j0 = i + 3
        j1 = min(n, i + 3 + WATCH)
        wick = None
        k_level = -1
        for j in range(j0, j1):
            if wick is None:
                if l[j] < L:
                    if c[j] < L:
                        break          # body close through with no prior wick defence
                    wick = l[j]
                continue
            if k_level < 0:
                if c[j] < L:
                    if c[j] < wick:
                        break          # level close == wick close: rules agree, drop
                    k_level = j
                    rows.append((i, j, False, L, wick))
                elif l[j] < wick:
                    wick = l[j]        # another wick-only pierce extends the reference
                continue
            if c[j] < wick:
                rows.append((i, j, True, L, wick))
                break
    return rows


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    if len(b) < 10:
        return pd.DataFrame(columns=COLS)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = b["close_time"].values.astype("datetime64[ns]").astype(np.int64)
    n = len(b)
    sh, sl = swings22(h, l)
    out = []
    for sgn, (hh, ll, cc), idx in ((-1, (h, l, c), np.flatnonzero(sl)),
                                   (1, (-l, -h, -c), np.flatnonzero(sh))):
        for (i, j, bw, L, W) in _scan_short(hh, ll, cc, idx, n):
            # stop = breaking bar's opposite extreme; in mirrored space hh[j] is that
            stop = hh[j] if sgn == -1 else -hh[j]
            out.append((int(ct[j]), sgn, stop, bw, int(ct[i]) * sgn, L if sgn == -1 else -L,
                        W if sgn == -1 else -W))
    if not out:
        return pd.DataFrame(columns=COLS)
    o_ = pd.DataFrame(out, columns=["t", "direction", "stop_px", "beyond_wick", "level_id",
                                    "level_px", "wick_px"])
    dec = from_ns(o_["t"].to_numpy())
    ev = pd.DataFrame({"decision_time": dec, "available_at": dec,
                       "direction": o_["direction"].astype(int).to_numpy(),
                       "stop_px": o_["stop_px"].to_numpy(float), "rr": RR,
                       "beyond_wick": o_["beyond_wick"].astype(bool).to_numpy(),
                       "level_id": o_["level_id"].astype(np.int64).to_numpy(),
                       "level_px": o_["level_px"].to_numpy(float),
                       "wick_px": o_["wick_px"].to_numpy(float)})
    return ev.sort_values(["decision_time", "level_id"]).reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}_w{WATCH}_rr2", lambda: detect(cl.load_m1()))
    print(len(ev), ev["beyond_wick"].value_counts().to_dict())
    print(ev.head())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "beyond_wick", mask_available_at="decision_time",
                       max_hold=MAX_HOLD, cluster="level_id")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "complement"):
        print(k, res.get(k))
    op = {"rules": [
        "15m fractal 2/2 swing lows/highs as levels, watched 96 bars after confirmation",
        "setup: first bar beyond the level is a wick-only pierce; reference = furthest wick of "
        "the wick-only pierces before the first body close beyond the level",
        "level arm: first 15m close beyond the level that is not beyond the wick extreme "
        "(coinciding setups dropped)",
        "wick arm: first later 15m close beyond the wick extreme",
        "trade the break direction at the next M1 open; stop at the breaking bar's opposite "
        "extreme; 2R; hold 150 min",
        "gate_test: wick-arm rows vs level-arm rows, control-adjusted, clustered by level"],
        "params": {"tf": TF, "watch_bars": WATCH, "rr": RR, "max_hold": MAX_HOLD,
                   "swing": "fractal 2/2", "stop": "breaking bar's opposite extreme"}}
    src = {"tf": "declared-before-run: 'no timeframe on which it should be evaluated'; 15m "
                 "from the concept's ltf list (fractal: true)",
           "watch_bars": "declared-before-run: level watched 96 bars (24h)",
           "rr": "declared-before-run: targets not stated; 2R (phase3 primary)",
           "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13)",
           "swing": "phase3: swing fractal left=2, right=2 (preregistration 1.16)",
           "stop": "declared-before-run: 'Stop: Not specified by this concept alone'; the "
                   "breaking candle's far extreme"}
    notes = ("Gate measures entry QUALITY only: setups where the wick-extreme close never comes "
             "are trades AP avoids; that avoided-loss benefit is not in a mean-R comparison.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
