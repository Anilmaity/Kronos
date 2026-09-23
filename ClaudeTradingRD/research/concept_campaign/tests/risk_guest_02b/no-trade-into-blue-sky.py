"""no-trade-into-blue-sky (Alex's Options, guest): deprioritise setups whose objective is
virgin price (all-time highs, no previous range overhead); prefer objectives inside or
through a previously traded range.

Baseline = bare 1h CISD book, LONGS ONLY (gold's all-time low is never in play in the
certified 2016-2026 span, so a short can never target virgin price; including shorts would
put every short in one arm and confound the gate with direction).
ATH at decision = max(pre-sample ATH 1921.17 [XAUUSD spot, 2011-09-06], every M1 high closed
by the decision). Objective = the book's 2R target (entry_ref + 2 * (entry_ref - stop)).
allowed = objective <= ATH (inside previously traded range); blocked = objective in blue sky.
claim '+'.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, BASE_PARAMS, BASE_SRC, BASE_RULE

PRE_SAMPLE_ATH = 1921.17


def detect(m1):
    ev = cisd_book(m1)
    ev = ev[ev["direction"] == 1].reset_index(drop=True)
    hi = np.maximum.accumulate(m1["high"].to_numpy(float))
    closes = (m1.index + pd.Timedelta(minutes=1)).asi8
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    pos = np.searchsorted(closes, t.as_unit(m1.index.unit).asi8, side="right") - 1
    ath = np.maximum(PRE_SAMPLE_ATH, np.where(pos >= 0, hi[np.clip(pos, 0, None)], -np.inf))
    tgt = ev["entry_ref"].to_numpy(float) + 2.0 * (ev["entry_ref"].to_numpy(float) - ev["stop_px"].to_numpy(float))
    ev["ath"] = ath
    ev["allowed"] = tgt <= ath
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("rg02b_bluesky_1hcisd_long", lambda: detect(cl.load_m1()))
    print(len(ev), "long events; allowed share", ev["allowed"].mean(), "blocked n", (~ev["allowed"]).sum())
    probe = cl.probe_lookahead(detect, ev, lookback="2000D", n_cuts=120)
    res = cl.gate_test(ev, "allowed", mask_available_at="decision_time", max_hold="10h", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [BASE_RULE + " -- long events only",
                    "ATH at decision = max(pre-sample ATH 1921.17, max M1 high closed by the decision)",
                    "objective = 2R target computed from the confirming close and protected-swing stop",
                    "blocked = objective above the ATH (virgin price / clear blue skies); allowed = objective inside previously traded range"],
          "params": {**BASE_PARAMS, "direction": "long only", "pre_sample_ath": PRE_SAMPLE_ATH,
                     "objective": "book 2R target"}}
    src = {**BASE_SRC,
           "direction": "declared-before-run: ATL never in play 2016-2026, so only longs can target virgin price",
           "pre_sample_ath": "declared-before-run: XAUUSD spot all-time high 2011-09-06 (~1921), precedes the certified span",
           "objective": "declared-before-run: the baseline book's own target is the setup's objective"}
    p = cl.write_result("no-trade-into-blue-sky", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="probe lookback 2000D: long enough that every probed slice contains the running ATH bar (ATHs only exceed the pre-sample constant from 2020-07); first attempt with 4000D left no room for random cuts and was refused by write_result, identical test re-run once with the valid probe.")
    print(p)
