"""realistic-r-expectations — is the 4H/15m model, fixed 2R, no management, a real edge?

The concept's benchmark: "4-hour / 15-minute model, gold, fixed 2R: 63R over 48 trades,
63% win rate", and "expect roughly 50% at 1:2; 2R breaks even at 34%"; the fixed-outcome
variant "take 2R or -1R and do not manage the position in between". The claim that is
decidable from OHLC is that this unmanaged fixed-2R book on gold delivers positive
expectancy beyond what random entries with the same geometry deliver (a raw win rate is
never read — trap 3; it is printed for the notes only).

Operationalisation (4H/15m pair, spec §1.2 table):
  * 4H bias from the previous-candle engine (spec §2.3), read on the LAST CLOSED 4H
    candle C vs the one before it P (forex 4H grid, spec §1.4 / phase 3):
      continuation: C takes P.high and closes above it -> bullish; takes P.low and closes
      below -> bearish. reversal: takes P.high only and closes back inside -> bearish;
      takes P.low only and closes back inside -> bullish. Both sides taken / inside bar
      -> no bias (no trade).
  * entry: 15m CISD in the bias direction (phase-3 locked CISD), stop at the protected
    swing, target fixed 2R, exit at 150 min (10 entry-TF bars). No management.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl, np, pd, cisd_raw, utc_ns, PHASE3_SRC  # noqa: E402

CID = "realistic-r-expectations"
HOLD = "150min"


def bias_4h(m1, times):
    b4 = cl.build_bars(m1, "4h", grid4h="forex")
    h, lo, c = b4["high"].to_numpy(), b4["low"].to_numpy(), b4["close"].to_numpy()
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, lo[:-1]]
    up, dn = h > ph, lo < pl
    bias = np.zeros(len(b4))
    bias[up & ~dn & (c > ph)] = 1           # continuation up
    bias[dn & ~up & (c < pl)] = -1          # continuation down
    bias[up & ~dn & (c <= ph)] = -1         # took the high, closed back inside -> reversal
    bias[dn & ~up & (c >= pl)] = 1          # took the low, closed back inside -> reversal
    b4 = b4.assign(bias=bias)
    a = cl.asof(b4[["bias", "close_time"]], times)
    return a["bias"].to_numpy(float), pd.DatetimeIndex(a["available_at"])


def detect(m1):
    b, ev = cisd_raw(m1, "15min")
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if ev is None:
        return pd.DataFrame(columns=cols)
    bias, bav = bias_4h(m1, pd.DatetimeIndex(ev["decision_time"]))
    keep = np.isfinite(bias) & (bias == ev["direction"].to_numpy())
    out = ev[keep].reset_index(drop=True).assign(rr=2.0)
    out["available_at"] = pd.to_datetime(np.maximum(
        utc_ns(pd.DatetimeIndex(out["available_at"])), utc_ns(bav[keep])), utc=True)
    return out[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("realr_cisd15_4hbias_2r", lambda: detect(cl.load_m1()))
    print("events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.trade_test(ev, max_hold=HOLD, claim="+", keep_trades=True)
    tr = res.pop("_trades", None)
    wr = float((tr["net_R"] > 0).mean()) if tr is not None else None
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde",
                                   "verdict", "verdict_detail", "ties", "exposure_bars",
                                   "ctrl_overlap")}, "raw win rate", wr)
    op = {"rules": [
        "4H bias = previous-candle engine on the last CLOSED forex-grid 4H candle vs its "
        "predecessor (continuation / reversal closure; both-sides or inside = no bias)",
        "entry: 15m CISD (series_open, 2/2 swings, max_wait 3) in the bias direction, "
        "decide at the confirming bar close, enter next M1 open",
        "stop at the protected swing, fixed 2R target, exit at 150min; no management"],
        "params": {"entry_tf": "15min", "bias_tf": "4h", "grid4h": "forex", "rr": 2.0,
                   "max_hold": HOLD}}
    src = {"entry_tf": "method_spec §1.2: 4-hour / 15-minute pair (the benchmark model)",
           "bias_tf": "method_spec §1.2 + corpus benchmark '4-hour / 15-minute model'",
           "grid4h": "phase3: forex 4H grid locked for gold (carried as a knob)",
           "rr": "corpus: benchmark 'taking a fixed 2R'",
           "max_hold": PHASE3_SRC + " (10 entry-TF bars)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes=f"Raw win rate of the real arm (not a verdict input, trap 3): "
                              f"{wr:.3f} vs the 63% benchmark / 34% break-even. The 4H bias "
                              f"is the §2.3 previous-candle engine only; the POI/profile/"
                              f"alignment gates of the full stack are not applied (phase 3 "
                              f"found none of them adds value).")
    print("wrote", p)
