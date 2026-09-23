"""secondary-consolidation-breakout (guest: Alex's Options, V8P6lNIisvc).

"big initial consolidation, breaks above and closing above those highs", then a
"really small secondary consolidation", and the run comes out of the second one.
Trade test on 5m bars (the concept's ltf; its htf is 1h, so the first box spans
a few hours). Every size knob is unstated in the corpus and declared here before
the first run:

  box1   the W1=36 5m bars (3h) before the break bar; a consolidation when its
         range <= 4.0 x the mean bar range (high-low) of those 36 bars
  break  bar b CLOSES beyond box1's extreme
  box2   the next W2=6 bars (30 min): range <= 0.5 x box1 range and every close
         stays beyond box1's extreme (a close back inside = invalidation)
  entry  the first bar within the next 12 bars that closes beyond box2's extreme
         in the break direction, with no close back inside box1 before it;
         decide at that bar's close, enter next M1 open
  stop   box2's opposite extreme; target 2R; max hold 10 5m bars
One event per entry bar and direction.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

W1, W2, WE = 36, 6, 12
TIGHT = 4.0
SMALL = 0.5
RR = 2.0
MAX_HOLD = "50min"


def detect(m1):
    B = cl.build_bars(m1, "5min")
    B = B[B["n_m1"] > 0]
    h, l, c = (B[k].to_numpy() for k in ("high", "low", "close"))
    n = len(B)
    ct = pd.DatetimeIndex(B["close_time"])
    hs, ls = pd.Series(h), pd.Series(l)
    b1h = hs.rolling(W1).max().shift(1).to_numpy()       # box1 = [b-W1, b-1]
    b1l = ls.rolling(W1).min().shift(1).to_numpy()
    mr = (hs - ls).rolling(W1).mean().shift(1).to_numpy()
    r1 = b1h - b1l
    tight = r1 <= TIGHT * mr
    # box2 = [b+1, b+W2] -> rolling over W2 ending at b+W2, shifted back by W2
    b2h = hs.rolling(W2).max().shift(-W2).to_numpy()
    b2l = ls.rolling(W2).min().shift(-W2).to_numpy()
    cs = pd.Series(c)
    b2cmin = cs.rolling(W2).min().shift(-W2).to_numpy()
    b2cmax = cs.rolling(W2).max().shift(-W2).to_numpy()
    rows = []
    idx = np.arange(n)
    for bull in (True, False):
        brk = (c > b1h) if bull else (c < b1l)
        hold = (b2cmin > b1h) if bull else (b2cmax < b1l)
        small = (b2h - b2l) <= SMALL * r1
        base = tight & brk & hold & small
        bs = np.where(base)[0]
        e = np.full(len(bs), -1)
        dead = np.zeros(len(bs), bool)
        for k in range(1, WE + 1):
            p = bs + W2 + k
            valid = p < n
            p = np.minimum(p, n - 1)
            ce = c[p]
            if bull:
                back = ce <= b1h[bs]
                go = ce > b2h[bs]
            else:
                back = ce >= b1l[bs]
                go = ce < b2l[bs]
            newe = valid & (e < 0) & ~dead & go & ~back
            e = np.where(newe, p, e)
            dead |= valid & (e < 0) & back
        ok = e >= 0
        bs, e = bs[ok], e[ok]
        rows.append(pd.DataFrame({
            "decision_time": ct[e], "direction": 1 if bull else -1,
            "stop_px": (b2l if bull else b2h)[bs]}))
    ev = pd.concat(rows, ignore_index=True)
    ev = ev.drop_duplicates(["decision_time", "direction"], keep="first")
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = RR
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"scb_{W1}_{W2}_{WE}_{TIGHT}_{SMALL}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "5m bars; box1 = 36 bars before break bar b, consolidation if range <= 4.0 x mean bar range",
        "break: bar b closes beyond box1's extreme",
        "box2 = bars b+1..b+6: range <= 0.5 x box1 range; all closes beyond box1's extreme",
        "entry: first of the next 12 bars closing beyond box2's extreme (break direction), with "
        "no close back inside box1 first; decide at its close, enter next M1 open",
        "stop = box2 opposite extreme; target 2R; max hold 50 min; one event per entry bar"],
        "params": {"tf": "5min", "w1": W1, "w2": W2, "entry_window": WE, "tight_mult": TIGHT,
                   "small_ratio": SMALL, "rr": RR, "max_hold": MAX_HOLD}}
    src = {"tf": "corpus: V8P6lNIisvc (concept ltf 5m/1m, htf 1h)",
           "w1": "declared-before-run: first box 3h of 5m bars (a few 1h candles)",
           "w2": "declared-before-run: secondary box 30 min",
           "entry_window": "declared-before-run: breakout from box2 within 1h",
           "tight_mult": "declared-before-run: consolidation = range <= 4x mean bar range",
           "small_ratio": "declared-before-run: 'materially smaller' = <= half of box1 "
                          "(threshold_fits 'shallow' cut 0.50 used as the analogous half rule)",
           "rr": "method_spec §5.3: 2R floor",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    print(cl.write_result("secondary-consolidation-breakout", None, res, operationalization=op,
                          params_source=src, script=__file__, probe=probe,
                          notes="Guest rates his own capture at fifty-fifty and takes it only "
                                "with a strong bias; tested as the bare pattern (no bias gate)."))
