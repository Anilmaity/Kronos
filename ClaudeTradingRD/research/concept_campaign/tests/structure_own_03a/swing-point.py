"""swing-point (TTrades own voice, contested) — batch structure_own_03a.

Premise: "price cannot reverse without forming a swing point"; a swing low = a low with
a higher low on each side (3 candles), usable only once the right-hand candle has
closed. The tradeable content of the premise: a freshly confirmed swing is a reversal
point to trade away from, with the swing extreme as the invalidation.

Book: 1h bars. At the close of bar i+1 confirming a strict 3-bar swing low at i, go
long at the next M1 open, stop at low[i], target 2R, exit after 10h (mirror: swing
highs -> short). trade_test vs matched random entries, claim '+'.
Reading a: every strict 3-bar swing (the stated arithmetic definition).
Reading b: only swings that SWEEP liquidity — the swing low trades below the most recent
  earlier confirmed swing low ("A genuine swing point is one whose sweep takes out a
  prior extreme"; interior swings that take nothing are failure swings, not structure).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a")
from _common import PHASE3, cl, np, pd, summary, swings3  # noqa: E402

CID = "swing-point"
TF, RR, HOLD = "1h", 2.0, "10h"


def detect(m1, sweep: bool):
    b = cl.build_bars(m1, TF)
    h = b["high"].to_numpy(float)
    l = b["low"].to_numpy(float)
    sh, sl = swings3(b)
    rows = []
    for bull in (True, False):
        x = l if bull else -h                 # "low space"
        pts = np.flatnonzero(sl if bull else sh)
        for k, p in enumerate(pts):
            conf = p + 1
            if conf >= len(b):
                continue
            if sweep:
                # the most recent earlier swing CONFIRMED before bar p (pivot <= p-2)
                prev = pts[:k][pts[:k] + 1 < p]
                if not len(prev) or not (x[p] < x[prev[-1]]):
                    continue
            rows.append((conf, 1 if bull else -1, x[p] if bull else -x[p]))
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if not rows:
        return pd.DataFrame(columns=cols)
    r = pd.DataFrame(rows, columns=["conf", "d", "stop"])
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[r["conf"].to_numpy()])
    ev = pd.DataFrame({"decision_time": ct, "available_at": ct,
                       "direction": r["d"].to_numpy().astype(int),
                       "stop_px": r["stop"].to_numpy(float), "rr": RR})
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    rules = [f"{TF} bars; swing low at i := low[i] < low[i-1] and low[i] < low[i+1] (mirror "
             "for highs), usable from the close of bar i+1",
             "decide at that close, enter next M1 open away from the swing (long off a swing "
             f"low, short off a swing high), stop = the swing extreme, {RR}R, exit after {HOLD}"]
    params = {"tf": TF, "swing": "strict 3-bar", "rr": RR, "max_hold": HOLD}
    src = {"tf": "corpus: swing-point.yaml timeframes htf includes 1H (phase-3 1h stack)",
           "swing": "corpus: swing-point.yaml 'swing_low(i) := low[i] < low[i-1] AND low[i] < low[i+1]'",
           "rr": PHASE3, "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    for reading, sweep, extra, xp, xs in (
            ("a", False, [], {}, {}),
            ("b", True, ["reading b: only swings whose extreme takes out the most recent "
                         "earlier confirmed same-side swing (a sweep of liquidity)"],
             {"sweep_ref": "last confirmed same-side swing"},
             {"sweep_ref": "corpus: swing-point.yaml 'A genuine swing point is one whose sweep "
                           "takes out a prior extreme (liquidity)'"})):
        ev = cl.cache_frame(f"sp_{TF}_sweep{int(sweep)}", lambda: detect(cl.load_m1(), sweep))
        print(reading, len(ev))
        probe = cl.probe_lookahead(lambda m: detect(m, sweep), ev, lookback="15D")
        res = cl.trade_test(ev, max_hold=HOLD)
        print(f"reading {reading}\n" + summary(res))
        p = cl.write_result(CID, reading, res,
                            operationalization={"rules": rules + extra,
                                                "params": {**params, **xp}},
                            params_source={**src, **xs}, script=__file__, probe=probe,
                            notes="The 'no reversal without a swing' premise is a tautology at "
                                  "the bar level; what is testable is whether a confirmed swing "
                                  "is a reversal point worth trading away from.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
