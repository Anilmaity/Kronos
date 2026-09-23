"""risk_own_01b / stop-behind-already-swept-liquidity (specified) — gate_test.

Baseline: 15m rung-0 CISD book, stop at the protected swing (the CISD extreme).
Gate (kept): that protected extreme SWEPT resting liquidity before entry — the
extreme bar traded through at least one confirmed 2/2 swing low (bullish; swing
high for bearish) that was still intact at the end of the previous bar and was
confirmed before the extreme bar opened, looking back LIQ_LOOKBACK bars.
Complement: the protected swing is a fresh level that took no prior liquidity.
Claim +: "we already ran the liquidity, there's no real reason to run it again" —
stops behind already-swept liquidity survive better, so the kept book beats the
complement (control-adjusted). This is the concept's own measurable: 'stop-out rate
of stops placed behind swept vs unswept levels'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
from _common import *   # noqa
from detectors.primitives import swing_points  # noqa: E402

TF = "15min"
LIQ_LOOKBACK = 96          # 15m bars = one day


def detect(m1):
    ev, _, b = cisd_book(m1, TF)
    keep = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if ev.empty:
        return ev[keep].assign(swept_liq=pd.Series(dtype=bool))
    sw = swing_points(b[["open", "high", "low", "close"]], left=2, right=2)
    H, L = b["high"].to_numpy(float), b["low"].to_numpy(float)
    sl = np.flatnonzero(sw["swing_low"].to_numpy())
    sh = np.flatnonzero(sw["swing_high"].to_numpy())
    swept = np.zeros(len(ev), bool)
    for k, (p, d) in enumerate(zip(ev["ext_pos"].to_numpy(), ev["direction"].to_numpy())):
        piv = sl if d > 0 else sh
        lo_i = np.searchsorted(piv, p - LIQ_LOOKBACK)
        hi_i = np.searchsorted(piv, p - 2, side="left")      # q + 2 <= p - 1
        for q in piv[lo_i:hi_i][::-1]:
            if d > 0:
                lvl = L[q]
                if L[q + 1:p].min() > lvl and L[p] < lvl:     # intact until p-1, taken by p
                    swept[k] = True
                    break
            else:
                lvl = H[q]
                if H[q + 1:p].max() < lvl and H[p] > lvl:
                    swept[k] = True
                    break
    out = ev[keep].copy()
    out["swept_liq"] = swept
    return out


if __name__ == "__main__":
    ev = cl.cache_frame(f"swept_stop_{TF}_lb{LIQ_LOOKBACK}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["swept_liq"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "swept_liq", mask_available_at="decision_time", max_hold=HOLD[TF], claim="+")
    show(res)
    op = {"rules": ["baseline: 15m rung-0 CISD book (series_open, 2/2 swings, max_wait 3, stop at protected swing, 2R, hold 150min)",
                    f"kept: the protected extreme bar traded through a confirmed 2/2 swing low/high that was intact at the prior bar's close and confirmed before the extreme bar (lookback {LIQ_LOOKBACK} bars)",
                    "complement: protected swing took no prior intact swing",
                    "claim +: stops behind already-swept liquidity perform better (control-adjusted)"],
          "params": {"baseline_tf": TF, **BASE_PARAMS, "max_hold": HOLD[TF],
                     "liq_swing": "2/2 fractal, same TF", "liq_lookback_bars": LIQ_LOOKBACK, "grid4h": "n/a"}}
    src = {"baseline_tf": "phase3: primary stack entry TF; concept htf lists 15m",
           **{k: BASE_SRC for k in BASE_PARAMS}, "max_hold": HOLD_SRC,
           "liq_swing": "phase3: the locked 2/2 swing definition used by CISD",
           "liq_lookback_bars": "declared-before-run: one trading day of 15m bars",
           "grid4h": "declared-before-run: no 4h bars used"}
    p = cl.write_result("stop-behind-already-swept-liquidity", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="mask_available_at = decision: the sweep happens on the extreme bar, before the CISD confirmation.")
    print("wrote", p)
