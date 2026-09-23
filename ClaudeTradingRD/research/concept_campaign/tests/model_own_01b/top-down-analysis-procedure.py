"""top-down-analysis-procedure (TTrades own voice, contested) — batch model_own_01b.

The later-canon ladder: Daily bias -> Hourly point of interest aligned with the bias
-> 5-minute entry. Tested as gates on the phase-3 bare 5m CISD book (the Layer-3
entry: series_open, swing 2/2, max_wait 3, stop at the protected swing, 2R, 10 bars).

Daily bias (Layer 1): the previous-candle engine (method_spec §2.3) on the last
COMPLETED 18:00-NY daily candle vs the one before it: took one side and closed
outside -> continuation (same direction), closed back inside -> reversal (opposite).
Inside day / both sides -> no bias (the playbook's hard stop: no bias, no trade).

Reading a: gate = the 5m entry direction agrees with the daily bias.
Reading b: the full ladder — gate a AND the 5m setup's swept extreme took out the
           previous COMPLETED hourly candle's low (longs) / high (shorts) — the
           hourly point of interest 'a low being taken out' in the bias direction.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
from _common import PHASE3, cisd_book, cl, np, pd, prev_candle_state, summary  # noqa: E402

CID = "top-down-analysis-procedure"


def _asof_pos(close_times, t):
    ct = cl.data.utc_ns(pd.DatetimeIndex(close_times))
    return np.searchsorted(ct, cl.data.utc_ns(pd.DatetimeIndex(t)), side="right") - 1


def detect(m1):
    ev = cisd_book(m1, "5min")
    t = pd.DatetimeIndex(ev["decision_time"])
    d = cl.build_bars(m1, "1D")
    st = prev_candle_state(d)
    pos = _asof_pos(d["close_time"], t)
    bias = np.where(pos >= 0, st["implied"].to_numpy()[np.clip(pos, 0, None)], 0)
    bias_at = pd.DatetimeIndex(d["close_time"]).tz_convert("UTC")[np.clip(pos, 0, None)]
    dirn = ev["direction"].to_numpy()
    gate_a = (bias != 0) & (bias == dirn)
    # hourly POI: previous completed 1H candle as of the swept extreme's bar START
    h = cl.build_bars(m1, "1h")
    te = pd.DatetimeIndex(ev["extreme_time"])
    hp = _asof_pos(h["close_time"], te)
    okh = hp >= 0
    hp_ = np.clip(hp, 0, None)
    hlow, hhigh = h["low"].to_numpy()[hp_], h["high"].to_numpy()[hp_]
    pe = ev["extreme_price"].to_numpy()
    took = np.where(dirn > 0, pe < hlow, pe > hhigh) & okh
    out = ev.drop(columns=["extreme_time", "extreme_price"]).copy()
    out["daily_bias"] = bias
    # the gate is knowable at max(bias day close, the extreme bar close) <= decision
    ext_close = te + pd.Timedelta(minutes=5)
    bias_ns = np.where(pos >= 0, cl.data.utc_ns(bias_at), cl.data.utc_ns(ext_close))
    out["gate_at"] = np.maximum(bias_ns, cl.data.utc_ns(ext_close))
    out["gate_at"] = pd.to_datetime(out["gate_at"], utc=True)
    out["gate_a"] = gate_a
    out["gate_b"] = gate_a & took
    return out


def main():
    ev = cl.cache_frame("topdown_cisd5_v1", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="15D")
    base_rules = ["baseline: 5m bare CISD (series_open, swing 2/2, max_wait 3), decide at "
                  "the confirming bar close, enter next M1 open, stop protected swing, 2R, 50 min",
                  "daily bias: previous-candle engine on the last completed 18:00-NY day vs "
                  "the day before (continuation -> same, reversal -> opposite; inside/both -> none)"]
    base_params = {"entry_tf": "5min", "level_rule": "series_open", "swing": "2/2",
                   "max_wait": 3, "rr": 2.0, "max_hold": "50min", "day_open_hour": 18}
    base_src = {"entry_tf": "corpus: top-down-analysis-procedure.yaml 'Layer 3 (5-minute): take the entry'",
                "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
                "max_hold": "phase3: 10 entry-TF bars (§1.13)",
                "day_open_hour": "method_spec: §1.4 daily open 18:00 canon"}
    for reading, col, extra, xp, xs in (
            ("a", "gate_a", ["gate: entry direction == daily bias (no bias -> not gated)"], {}, {}),
            ("b", "gate_b", ["gate: gate a AND the setup's swept extreme took out the previous "
                             "completed 1H candle's low (long) / high (short) = hourly POI tagged",
                             "hourly FVG branch of the POI not implemented (declared)"],
             {"poi_tf": "1h", "poi_kind": "prior 1H candle extreme taken"},
             {"poi_tf": "corpus: top-down-analysis-procedure.yaml 'Layer 2 (hourly): find a point of interest that ALIGNS with that bias'",
              "poi_kind": "method_spec: §4.1 POI enumeration 'a high being taken out, or a low being taken out'"})):
        res = cl.gate_test(ev, col, mask_available_at="gate_at", max_hold="50min")
        print(f"reading {reading}\n" + summary(res))
        op = {"rules": base_rules + extra, "params": {**base_params, **xp}}
        p = cl.write_result(CID, reading, res, operationalization=op,
                            params_source={**base_src, **xs}, script=__file__, probe=probe,
                            notes="Phase 3 already refuted the full conjunction (bias+POI+CISD+timing); "
                                  "this tests the top-down ladder as stated in this concept.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
