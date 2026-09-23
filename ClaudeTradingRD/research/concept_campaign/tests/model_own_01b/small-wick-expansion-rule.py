"""small-wick-expansion-rule (TTrades own voice, contested) — batch model_own_01b.

Claim: a candle with a small wick (small opposing run) and a large body supports
expansion away from the wick; a large-wick candle does not (it is a reversal
candle — expect a return toward its open, wait for the next candle).

Baseline book: every closed 4H candle (forex grid) with a direction (close != open).
Trade the continuation: decide at the candle's close, enter next M1 open in the
candle's direction, stop beyond the candle's opposite extreme (its low for a bullish
candle), no fixed target, exit after one more 4H candle (240 M1 bars, trading time).
Gate = the candle is a small-wick (expansion) candle:
  reading a: opposing_run / |close-open| <= 1.0   (threshold_fits grade A — the one
             corpus-attested cut: 'a wick larger than the body' = reversal candle)
  reading b: opposing_run / (high-low)   <= 0.30  (threshold_fits range form, grade C)
opposing_run = open -> extreme AGAINST the candle's direction (SlWxhzhLo3A, one-sided).
4H chosen because threshold_fits located the only wick separation on 4h/1D; 1D would
leave ~2,600 candles and a far wider CI.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
from _common import cl, np, pd, summary  # noqa: E402

CID = "small-wick-expansion-rule"
CUT_BODY, CUT_RANGE = 1.0, 0.30


def detect(m1):
    H = cl.build_bars(m1, "4h", grid4h="forex")
    o, h, l, c = (H[k].to_numpy() for k in ("open", "high", "low", "close"))
    d = np.sign(c - o)
    keep = d != 0
    o, h, l, c, d = o[keep], h[keep], l[keep], c[keep], d[keep].astype(int)
    opp = np.where(d > 0, o - l, h - o)
    body = np.abs(c - o)
    rng = h - l
    ct = pd.DatetimeIndex(H["close_time"].to_numpy()[keep])
    return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": d,
                         "stop_px": np.where(d > 0, l, h), "rr": np.nan,
                         "small_body": (opp / body) <= CUT_BODY,
                         "small_range": np.where(rng > 0, opp / np.where(rng > 0, rng, 1), np.inf) <= CUT_RANGE,
                         }).reset_index(drop=True)


def main():
    ev = cl.cache_frame("swer_4h_v1", lambda: detect(cl.load_m1()))
    # entry at the close of a stop-at-the-low candle can leave the stop ON the entry
    # side only if the next open gaps through it; the harness handles gap fills.
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    base_rules = ["every closed 4H candle (forex grid 17/21/01/05/09/13 NY) with close != open",
                  "trade the continuation: decide at its close, enter next M1 open in its "
                  "direction, stop at its opposite extreme, no target, exit after 240 M1 bars",
                  "opposing run = open -> extreme against the candle's direction"]
    base_params = {"tf": "4h", "grid4h": "forex", "max_hold": "240min", "hold_basis": "bars",
                   "target": "none (time exit)"}
    base_src = {"tf": "threshold_fits: §1 wick separation is a 4h/1D phenomenon; yaml timeframes htf 4H",
                "grid4h": "session_window_fit: forex grid for gold (weak; recorded)",
                "max_hold": "declared-before-run: expansion is expected in the NEXT candle (one 4H candle)",
                "hold_basis": "declared-before-run: trading time (the 17:00 grid candle spans the halt)",
                "target": "declared-before-run: the EQ target is undefined ('EQ of what' ambiguity); "
                          "time exit measures expansion directly"}
    for reading, col, rule, xp, xs in (
            ("a", "small_body", "gate: opposing_run / |close-open| <= 1.0",
             {"wick_cut_body": CUT_BODY},
             {"wick_cut_body": "threshold_fits: small wick opposing_run/body <= 1.0 (grade A)"}),
            ("b", "small_range", "gate: opposing_run / (high-low) <= 0.30",
             {"wick_cut_range": CUT_RANGE},
             {"wick_cut_range": "threshold_fits: range parameterisation default 0.30 (grade C)"})):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold="240min",
                           hold_basis="bars")
        print(f"reading {reading}\n" + summary(res))
        op = {"rules": base_rules + [rule], "params": {**base_params, **xp}}
        p = cl.write_result(CID, reading, res, operationalization=op,
                            params_source={**base_src, **xs}, script=__file__, probe=probe,
                            notes="control-adjusted R per trade (same stop distance, same "
                                  "hold), so the body/stop geometry of small- vs large-wick "
                                  "candles is matched rather than read as prediction.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
