"""advanced-market-structure-labeling (TTrades own voice, contested) — batch structure_own_03a.

Concept: short-term high (STH) = 3-bar swing high; intermediate-term high (ITH) = a STH
with a LOWER STH on both sides. Used operationally: once the ITH is confirmed (a STH
has formed on its right), enter short off that right-hand STH, stop on the ITH (it
"should not be violated while the idea holds"), target the sellside (2R, the risk
convention he states for these trades). Mirror for lows / longs.

Execution TF: 5m (yaml ltf 1H/5m/1m; the narrated live example is a 5-minute
execution). The claim ('+') is that this entry beats a matched random entry with the
same stop and target distances.

Reading a (the PDF arithmetic definition): ITH = STH whose neighbouring STHs on both
  sides are lower. Decide at the close of the bar that confirms the right-hand STH.
Reading b (the narrated chart procedure, which "adds a sweep"): the ITH bar must SWEEP
  the prior STH — trade above it and close back below it — "He explicitly declines an
  earlier entry because the highs there were failure swings rather than sweeps".
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a")
from _common import PHASE3, cl, np, pd, summary, swings3  # noqa: E402

CID = "advanced-market-structure-labeling"
TF, RR, HOLD = "5min", 2.0, "50min"


def _side(b, bull: bool, sweep: bool):
    h = b["high"].to_numpy(float)
    l = b["low"].to_numpy(float)
    c = b["close"].to_numpy(float)
    sh, sl = swings3(b)
    # work in "high" space; bullish = negated lows
    x = -l if bull else h
    cc = -c if bull else c
    pts = np.flatnonzero(sl if bull else sh)
    rows = []
    for k in range(1, len(pts) - 1):
        p0, p1, p2 = pts[k - 1], pts[k], pts[k + 1]
        if not (x[p0] < x[p1] > x[p2]):
            continue
        conf = p2 + 1                       # bar whose close confirms the right STH
        if conf >= len(b):
            continue
        # the ITH must not have been traded through before the decision
        if x[p1 + 1:conf + 1].max() >= x[p1]:
            continue
        if sweep and not (cc[p1] < x[p0]):  # closed back below the swept STH
            continue
        rows.append((conf, p1, -1 if not bull else 1, (-x[p1]) if bull else x[p1]))
    return rows


def detect(m1, sweep: bool = False):
    b = cl.build_bars(m1, TF)
    rows = _side(b, False, sweep) + _side(b, True, sweep)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if not rows:
        return pd.DataFrame(columns=cols)
    r = pd.DataFrame(rows, columns=["conf", "p1", "dir", "stop"])
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[r["conf"].to_numpy()])
    ev = pd.DataFrame({"decision_time": ct, "available_at": ct,
                       "direction": r["dir"].to_numpy().astype(int),
                       "stop_px": r["stop"].to_numpy(float), "rr": RR})
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    rules = [f"{TF} bars; STH/STL = strict 3-bar swing (high[i] > both neighbours; mirror)",
             "ITH = STH whose previous and next STH are both lower (ITL mirror: both higher)",
             "confirmed at the close of the bar after the right-hand STH (that STH is "
             "itself confirmed only then); ITH not traded through before the decision",
             "decide at that close, enter next M1 open AWAY from the ITH/ITL (short off an "
             "ITH, long off an ITL), stop = the ITH/ITL extreme, target 2R, exit after "
             f"{HOLD}"]
    params = {"tf": TF, "swing": "3-bar strict (1/1)", "rr": RR, "max_hold": HOLD}
    src = {"tf": "corpus: advanced-market-structure-labeling.yaml timeframes ltf 5m; "
                 "'Asia highs swept, London up-close candle order block, 5-minute execution'",
           "swing": "corpus: yaml detection_rules 'Short-term low = a low with a higher low "
                    "immediately either side'",
           "rr": "corpus: propulsion/structure trades target 2R; " + PHASE3,
           "max_hold": "phase3: 10 entry-TF bars (§1.13) -> 50 min on 5m"}
    for reading, sweep, extra, xp, xs in (
            ("a", False, [], {}, {}),
            ("b", True, ["reading b: the ITH bar must SWEEP the previous STH (high above it, "
                         "close back below it; mirror for lows)"],
             {"sweep": "close back inside the swept STH"},
             {"sweep": "corpus: yaml definition 'He explicitly declines an earlier entry "
                       "because the highs there were failure swings rather than sweeps'"})):
        ev = cl.cache_frame(f"amsl_ith_{TF}_sweep{int(sweep)}",
                            lambda: detect(cl.load_m1(), sweep))
        print(reading, len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(lambda m: detect(m, sweep), ev, lookback="5D")
        res = cl.trade_test(ev, max_hold=HOLD)
        print(f"reading {reading}\n" + summary(res))
        p = cl.write_result(CID, reading, res,
                            operationalization={"rules": rules + extra,
                                                "params": {**params, **xp}},
                            params_source={**src, **xs}, script=__file__, probe=probe,
                            notes="Long-term (HTF-reaction) points and the 'rebalanced' "
                                  "intermediate-term variant are not tested; the ITH-stop "
                                  "trade is the operational use the corpus narrates.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
