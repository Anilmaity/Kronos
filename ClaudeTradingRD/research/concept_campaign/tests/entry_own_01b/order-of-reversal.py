"""order-of-reversal — gate_test.

The ladder: rung 1 sweep, rung 2 inversion (a close beyond the FVG that supported the
prior move), rung 3 CISD; "steps 2 and 3 together are the stated minimum for more
confirmation that a reversal has formed".

Baseline book (stated): phase-3 rung-0 1h CISD (rung 3 entry), decided at the confirming
bar's close, stop protected swing, 2R, 10h.
Gate `inversion`: rung 2 printed before/at the CISD — an FVG opposing the reversal
(bearish FVG for a bullish reversal) whose third bar lies in [range_start, extreme], not
already closed through before the extreme, is closed THROUGH (close beyond the whole gap:
gap_high for bullish, gap_low for bearish) by a bar in (extreme, confirm]. range_start =
the phase-3 POI search-range start (detectors.poi.range_from_swing, lookback 40).
claim '+': CISDs with a prior inversion beat those without, control-adjusted.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b")
from _common import cl, np, pd, cisd_frame, PHASE3_SRC
from detectors.poi import range_from_swing

CID = "order-of-reversal"
TF = "1h"
HOLD = "10h"
RR = 2.0
LOOKBACK = 40


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "inversion"]
    b = cl.build_bars(m1, TF)
    ev = cisd_frame(b)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    h, l, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    ohlc = b[["open", "high", "low", "close"]]
    inv = np.zeros(len(ev), bool)
    for i, r in enumerate(ev.itertuples(index=False)):
        e, cf = r.ext_pos, r.conf_pos
        s = range_from_swing(ohlc, e, r.direction, lookback=LOOKBACK)
        for k in range(max(s, 2), e + 1):                      # FVG stamped on its 3rd bar k
            if r.sgn > 0:
                if h[k] < l[k - 2]:                            # bearish FVG (high[k] < low[k-2])
                    top = l[k - 2]
                    if (c[k + 1:e + 1] > top).any():           # already inverted before the low
                        continue
                    if (c[e + 1:cf + 1] > top).any():
                        inv[i] = True
                        break
            else:
                if l[k] > h[k - 2]:                            # bullish FVG
                    bot = h[k - 2]
                    if (c[k + 1:e + 1] < bot).any():
                        continue
                    if (c[e + 1:cf + 1] < bot).any():
                        inv[i] = True
                        break
    t = pd.DatetimeIndex(ev["conf_close_time"])
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": ev["sgn"].to_numpy(),
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": RR,
                        "inversion": inv})
    return out[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_1h_inv", lambda: detect(cl.load_m1()))
    print(len(ev), ev["inversion"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe["passed"], probe["events_compared"])
    res = cl.gate_test(ev, "inversion", mask_available_at="decision_time", max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "avg_R", "exposure_bars", "ctrl_overlap")})
    op = {"rules": [
        "baseline: 1h CISD (series_open, 2/2 swing, max_wait 3) = rung 3; decide at confirm close, "
        "enter next M1 open, stop protected swing, 2R, 10h",
        "gate inversion (rung 2): an FVG opposing the reversal (3-bar wick gap), stamped in "
        "[range_start, extreme bar], not closed through before the extreme, is closed through "
        "(close beyond the whole gap) by a bar after the extreme and no later than the CISD bar",
        "range_start = most recent opposing 2/2 swing before the extreme within 40 bars "
        "(detectors.poi.range_from_swing)"],
        "params": {"tf": TF, "level_rule": "series_open", "swing": "2/2", "max_wait": 3, "rr": RR,
                   "max_hold": HOLD, "range_lookback": LOOKBACK, "inversion_close": "beyond whole gap"}}
    src = {"tf": PHASE3_SRC, "level_rule": PHASE3_SRC, "swing": PHASE3_SRC, "max_wait": PHASE3_SRC,
           "rr": "phase3: §1.12 2R fixed", "max_hold": "phase3: §1.13 10 entry-TF periods",
           "range_lookback": "phase3: POI search range, detectors/poi.range_from_swing lookback=40 (§1.6)",
           "inversion_close": "method_spec: §3.9 inversion FVG — a close beyond the CE alone is not "
                              "sufficient, the close must be beyond the whole gap"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes=f"gate firing rate {ev['inversion'].mean():.3f}; "
                        "tests the ladder's 'rung 2 + rung 3' minimum-confirmation claim on the rung-3 book")
    print(p)
