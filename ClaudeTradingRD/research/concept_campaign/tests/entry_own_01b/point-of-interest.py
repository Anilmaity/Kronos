"""point-of-interest — gate_test, two readings (contested).

Baseline book (stated): phase-3 rung-0 1h CISD, decided at the confirming bar's close,
stop protected swing, 2R, 10h. POI evaluated per EVENT on the entry timeframe (phase-3 §1.6).

Reading a — method_spec §4.1 / the dedicated 'only three POIs' lesson (NqSbvqDKML0):
  search range = reversal point -> extreme; FVG first; else swing high/low taken; only if
  neither, the CISD level with 50% of the series bodies holding; if BOTH an FVG and a swing
  exist, both must be tagged. (detectors.poi.poi_gate, defaults). The body-hold look-forward
  is capped at the CISD confirm bar so the verdict is known at the decision
  (fixes the phase-3 §11 availability bug).
Reading b — the live-stream closed enumeration "fair value gaps, highs and lows — that's it"
  (i2HhHhWdaPQ, tyoxl1l-6iI): pass iff the extreme tagged ANY FVG in the range OR took out ANY
  prior swing in the range; no CISD-level fallback, no both-required clause.
claim '+': POI-gated CISDs beat un-gated ones, control-adjusted.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b")
from _common import cl, np, pd, cisd_frame, OHLC, PHASE3_SRC
from detectors.poi import poi_gate, range_from_swing, fvg_pois, swing_pois

CID = "point-of-interest"
TF = "1h"
HOLD = "10h"
RR = 2.0
LOOKBACK = 40


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "poi_a", "poi_b"]
    b = cl.build_bars(m1, TF)
    ev = cisd_frame(b)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    df = b[OHLC]
    pa = np.zeros(len(ev), bool)
    pb = np.zeros(len(ev), bool)
    for i, r in enumerate(ev.itertuples(index=False)):
        e = int(r.ext_pos)
        hold = max(0, int(r.conf_pos) - int(r.e_pos))     # body-hold window ends at the confirm bar
        res = poi_gate(df, e, r.direction, lookback=LOOKBACK, timeframe="1h",
                       setup_type="reversal", require_body_half_hold=True,
                       body_hold_bars=hold)
        pa[i] = bool(res.passed)
        s = range_from_swing(df, e, r.direction, lookback=LOOKBACK)
        pb[i] = any(p["tagged"] for p in fvg_pois(df, s, e, r.direction)) or \
            any(p["tagged"] for p in swing_pois(df, s, e, r.direction))
    t = pd.DatetimeIndex(ev["conf_close_time"])
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": ev["sgn"].to_numpy(),
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": RR,
                        "poi_a": pa, "poi_b": pb})
    return out[cols]


if __name__ == "__main__":
    which = sys.argv[1]
    ev = cl.cache_frame(f"{CID}_1h_poi", lambda: detect(cl.load_m1()))
    print(len(ev), ev["poi_a"].mean(), ev["poi_b"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe["passed"], probe["events_compared"])
    col = f"poi_{which}"
    res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "avg_R", "exposure_bars", "ctrl_overlap")})
    base = ["baseline: 1h CISD (series_open, 2/2 swing, max_wait 3); decide at confirm close, enter "
            "next M1 open, stop protected swing, 2R, 10h",
            "search range = most recent opposing 2/2 swing before the extreme (<=40 bars) -> extreme bar; "
            "'tagged' = the extreme bar's excursion reached the FVG / took the swing (detectors.poi)"]
    if which == "a":
        rules = base + ["gate poi_a: spec §4.1 order — FVG tagged; else swing taken; else CISD level "
                        "with 50% of series bodies reclaimed by a close no later than the CISD bar; "
                        "FVG AND swing both tagged when both exist; FVG polarity any"]
    else:
        rules = base + ["gate poi_b: any FVG in range tagged OR any prior swing in range taken out "
                        "(closed enumeration 'fair value gaps, highs and lows'), no fallback"]
    op = {"rules": rules,
          "params": {"tf": TF, "level_rule": "series_open", "swing": "2/2", "max_wait": 3, "rr": RR,
                     "max_hold": HOLD, "range_lookback": LOOKBACK, "fvg_polarity": "any"}}
    src = {"tf": PHASE3_SRC, "level_rule": PHASE3_SRC, "swing": PHASE3_SRC, "max_wait": PHASE3_SRC,
           "rr": "phase3: §1.12 2R fixed", "max_hold": "phase3: §1.13 10 entry-TF periods",
           "range_lookback": "phase3: §1.6 POI gate, detectors/poi range_from_swing lookback=40",
           "fvg_polarity": "method_spec: §4.1 [GAP] FVG polarity never stated; literal 'any' default (detectors/poi)"}
    p = cl.write_result(CID, which, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes=f"gate firing rate {ev[col].mean():.3f}")
    print(p)
