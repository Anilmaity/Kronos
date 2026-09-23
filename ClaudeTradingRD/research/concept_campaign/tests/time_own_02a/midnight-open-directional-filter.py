"""midnight-open-directional-filter (contested, voice mixed).  A location filter on entries
-> gate_test on a baseline book.  Two readings:

(a) TTrades' Twitter-model / 'Price targets FVG after PDH' gate (WwmS47Gb3M0, MewB_Ero8vo):
    shorts only ABOVE the midnight (00:00 NY) open, longs only BELOW it.
    Baseline = 15m CISD events decided on a trading day AFTER its midnight open printed
    (the level exists), through the 17:00 halt.
(b) the two-level deep premium/discount reading (b6yvRKf8haE levels; $niper UmLWRlXd_V8
    'I'm not looking for sells underneath the 830 open and the midnight open'): longs only
    when price is below BOTH the midnight and the 08:30 opens, shorts only when above BOTH.
    Baseline = 15m CISD events decided after that day's 08:30 open printed.
Entry price tested = the confirming 15m close (entry_ref), known at the decision; the fill is
the next M1 open.  claim '+': permitted-side trades beat the rest (control-adjusted).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np  # noqa: E402
from _common import cl, cisd_book, base_params, base_src, base_rule, HOLD, show  # noqa: E402

TF = "15min"


def _open_before(ev, hhmm, m1):
    """The level must have printed strictly BEFORE the decision (an open stamped at the
    decision minute is the entry bar itself, not a prior level)."""
    o = cl.open_at(ev["decision_time"], hhmm, m1=m1)
    ok = o["time"].notna().to_numpy() & (o["time"].to_numpy() < ev["decision_time"].to_numpy())
    return np.where(ok, o["price"].to_numpy(float), np.nan)


def detect_a(m1):
    ev = cisd_book(m1, TF)
    mo = _open_before(ev, "00:00", m1)
    keep = np.isfinite(mo)
    ev = ev[keep].reset_index(drop=True)
    mo = mo[keep]
    ev["midnight_open"] = mo
    d, px = ev["direction"].to_numpy(), ev["entry_ref"].to_numpy(float)
    ev["permitted"] = ((d == -1) & (px > mo)) | ((d == 1) & (px < mo))
    return ev


def detect_b(m1):
    ev = cisd_book(m1, TF)
    mo = _open_before(ev, "00:00", m1)
    eo = _open_before(ev, "08:30", m1)
    keep = np.isfinite(mo) & np.isfinite(eo)
    ev = ev[keep].reset_index(drop=True)
    mo, eo = mo[keep], eo[keep]
    ev["midnight_open"], ev["open_0830"] = mo, eo
    d, px = ev["direction"].to_numpy(), ev["entry_ref"].to_numpy(float)
    ev["permitted"] = ((d == -1) & (px > mo) & (px > eo)) | ((d == 1) & (px < mo) & (px < eo))
    return ev


NOTES = {"a": "Re-run once after a bug fix: the first run (NULL, diff -0.022) admitted events decided exactly AT 00:00 NY, whose 'midnight open' is the entry bar itself; the probe caught the same defect in reading b. Levels now must print strictly before the decision. Result below is the fixed run.",
         "b": "Levels must print strictly before the decision (the first attempt failed the probe on an event decided exactly at 08:30 and was never scored)."}


if __name__ == "__main__":
    common_src = {**base_src(TF, "corpus: MewB_Ero8vo '15-minute: look to SHORT ABOVE THE MIDNIGHT OPEN'"),
                  "tz": "method_spec: §1.4 DST settled, America/New_York",
                  "open_max_delay_min": "declared-before-run: open = first M1 bar in [hh:mm, hh:mm+5) of the trading day (concept_lab.open_at default)"}
    for reading, det, key, rules, extra, extra_src in (
        ("a", detect_a, "to02a_midnight_a_15m_v2",
         ["level: midnight open = open of the first M1 bar in [00:00, 00:05) NY of the event's trading day",
          "baseline restricted to events decided after that open printed (00:15..17:00 NY)",
          "gate permitted: short with confirming close > midnight open, or long with confirming close < midnight open"],
         {"levels": "midnight open"},
         {"levels": "corpus: WwmS47Gb3M0 'looking to only short above midnight open and then vice versa for Longs'"}),
        ("b", detect_b, "to02a_midnight_b_15m_v2",
         ["levels: midnight open and 08:30 open (first M1 bar in [hh:mm, hh:mm+5) NY of the trading day)",
          "baseline restricted to events decided after the 08:30 open printed (08:45..17:00 NY)",
          "gate permitted: long with confirming close below BOTH opens, or short above BOTH; mixed/other = complement"],
         {"levels": "midnight open AND 08:30 open (both must agree)"},
         {"levels": "corpus: UmLWRlXd_V8 'I'm not looking for cells underneath the 830 open and the midnight open'; b6yvRKf8haE 'if you're looking for Longs you want below the a30 or midnight open'"}),
    ):
        ev = cl.cache_frame(key, lambda: det(cl.load_m1()))
        print(reading, len(ev), "events; permitted rate", ev["permitted"].mean())
        probe = cl.probe_lookahead(det, ev, lookback="10D")
        res = cl.gate_test(ev, "permitted", mask_available_at="decision_time", max_hold=HOLD[TF])
        show(res)
        op = {"rules": [base_rule(TF)] + rules,
              "params": {**base_params(TF), **extra, "tz": "America/New_York", "open_max_delay_min": 5}}
        print(cl.write_result("midnight-open-directional-filter", reading, res, operationalization=op,
                              params_source={**common_src, **extra_src}, script=__file__, probe=probe,
                                    notes=NOTES[reading]))
