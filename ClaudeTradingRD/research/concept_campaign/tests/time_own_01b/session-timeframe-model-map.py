"""session-timeframe-model-map — which timeframe pair for which session (W7Fu3Rx5iMs).

"Asia usually will do like a just daily H1 model [or H4 M15]"; "London, you can do all
of the above, or H1 M5"; "New York AM, you can use H4 M15, or H1 M5 [or 30m/3m]".
Volatility rises Asia -> London -> NY AM and the permitted EXECUTION timeframe drops
with it. Measurable: expectancy by (session, timeframe pair) cell.

The table's testable content is that a given low execution timeframe works where it is
permitted and not where it is not. Two readings (gate_test, claim '+'), declared before
the first run; sessions from SESSION_WINDOWS: Asia 20:00-00:00, London 02:00-05:00,
NY a.m. 08:30-12:00 (NY, DST-aware). Baseline books are phase-3 rung-0 CISD (series_open,
2/2, max_wait 3, min_series 1; decide at the confirming close; enter next M1 open; stop
protected swing; 2R; hold 10 entry bars), restricted to decisions inside the three
sessions.

  a: the 5m (H1/M5) book: gated = London or NY a.m. (M5 permitted) vs Asia (not).
  b: the 3m (30m/3m) book: gated = NY a.m. (M3 permitted) vs Asia or London (not).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, cisd_book, PHASE3_SRC  # noqa: E402

CID = "session-timeframe-model-map"
SESS = {k: cl.SESSION_WINDOWS[k] for k in ("asia", "london", "ny_am")}
READ = {"a": {"tf": "5min", "hold": "50min", "permitted": ("london", "ny_am")},
        "b": {"tf": "3min", "hold": "30min", "permitted": ("ny_am",)}}


def make_detect(reading):
    cfg = READ[reading]

    def detect(m1):
        ev = cisd_book(m1, cfg["tf"])
        if len(ev) == 0:
            ev["permitted"] = pd.Series(dtype=bool)
            return ev
        ins = {k: cl.in_window(ev["decision_time"], *w) for k, w in SESS.items()}
        anyw = np.zeros(len(ev), bool)
        perm = np.zeros(len(ev), bool)
        for k, m in ins.items():
            anyw |= m
            if k in cfg["permitted"]:
                perm |= m
        ev = ev[anyw].reset_index(drop=True)
        ev["permitted"] = perm[anyw]
        return ev
    return detect


def run(reading):
    cfg = READ[reading]
    detect = make_detect(reading)
    ev = cl.cache_frame(f"cisd_{cfg['tf']}_sessions_{reading}", lambda: detect(cl.load_m1()))
    print(reading, "events", len(ev), "gated", int(ev["permitted"].sum()))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "permitted", mask_available_at="decision_time",
                       max_hold=cfg["hold"], claim="+")
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde",
                                   "verdict", "verdict_detail", "ties", "ctrl_overlap",
                                   "halves", "exposure_bars")})
    perm = " or ".join(cfg["permitted"])
    op = {"rules": [
        f"baseline: phase-3 rung-0 {cfg['tf']} CISD, decisions inside Asia 20:00-00:00, "
        "London 02:00-05:00 or NY a.m. 08:30-12:00 NY; enter next M1 open; stop protected "
        f"swing; 2R; hold {cfg['hold']} (10 bars)",
        f"gate: decision inside a session where the map permits {cfg['tf']} execution "
        f"({perm}) vs the sessions where it does not"],
        "params": {"tf": cfg["tf"], "max_hold": cfg["hold"], "rr": 2.0,
                   "sessions": SESS, "permitted": list(cfg["permitted"])}}
    src = {"tf": ("corpus: W7Fu3Rx5iMs 'London, you can do all of the above, or H1 M5'"
                  if reading == "a" else
                  "corpus: session-timeframe-model-map 'New York a.m.: ... or 30-minute + "
                  "3-minute'") + "; " + PHASE3_SRC,
           "max_hold": PHASE3_SRC + " (10 entry-TF bars)",
           "rr": PHASE3_SRC,
           "sessions": "session_window_fit: SESSION_WINDOWS (method spec §2.5; Asia from "
                       "killzones.yaml)",
           "permitted": "corpus: W7Fu3Rx5iMs map - Asia D/H1 or H4/M15; London those or "
                        "H1/M5; NY AM H4/M15, H1/M5 or 30m/3m"}
    return res, op, src, probe


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    for r in "ab":
        if r in which:
            res, op, src, probe = run(r)
            print(cl.write_result(CID, r, res, operationalization=op, params_source=src,
                                  script=__file__, probe=probe,
                                  notes=f"Reading {r}: does the {READ[r]['tf']} CISD book do "
                                        "better in the sessions the map permits it than in "
                                        "those it does not? Control-adjusted R, so session "
                                        "volatility (geometry) cancels."))
