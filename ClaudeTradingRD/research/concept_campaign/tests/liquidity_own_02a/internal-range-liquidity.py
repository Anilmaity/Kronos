"""internal-range-liquidity — after external liquidity is taken, is the nearest unfilled
FVG (internal range liquidity) the draw?

Corpus (3OivsP1j_UE / TfHlNgAZ_II, "internal range liquidity is just a fair value Gap"):
IRL = an unfilled FVG inside the current range; "After external range liquidity has been
purged, the nearest unfilled fair value gap becomes the draw". Measurable: "hit rate of
the FVG being reached after external liquidity is purged". Target "commonly its
consequent encroachment (50%)"; 'reaching' is ambiguous (near edge vs CE), so two readings:
  a  reached = touches the gap's near edge
  b  reached = touches the gap's consequent encroachment (midpoint)

rate_test on gold 1h (the concept's htf list includes 1H):
  * ERL taken at bar j: its high trades above a confirmed (2/2) swing high formed within the
    last 50 bars and not yet taken (buy-side purge) -> draw is DOWN to the nearest untouched
    bullish FVG below the close; the sell-side mirror draws UP to the nearest untouched
    bearish FVG above. Bars that purge both sides are skipped; no FVG -> no event ("wait").
  * untouched = no bar after the gap (through bar j) has traded into it; gaps older than 50
    bars are out of the range.
  * outcome: gold reaches the level within 600 M1 bars after bar j's close.
  * null: the same distance from the first M1 open at matched random moments (+/-30d,
    locked 5 reps), same side, same horizon. claim '+'.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                   # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

CID = "internal-range-liquidity"
RANGE_BARS = 50        # declared-before-run: the 'current range' = last 50 1h bars
HORIZON_BARS = 600     # phase3: 10 x 1h hold, in trading minutes
SWING = 2              # phase3: 2/2 swings


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "near_edge", "ce"]
    b = cl.build_bars(m1, "1h")
    if len(b) < 20:
        return pd.DataFrame(columns=cols)
    h, l, cl_ = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    sw = swing_points(b, left=SWING, right=SWING)
    is_sh, is_sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    n = len(b)
    sh, sl = [], []            # untaken confirmed swings: (pos, level)
    bull, bear = [], []        # untouched gaps: (pos, near_edge, far_edge)
    rows = []
    for j in range(n):
        # swings confirmed by the close of bar j-1 become usable at bar j
        p = j - 1 - SWING
        if p >= SWING:
            if is_sh[p]:
                sh.append((p, h[p]))
            if is_sl[p]:
                sl.append((p, l[p]))
        sh = [s for s in sh if j - s[0] <= RANGE_BARS]
        sl = [s for s in sl if j - s[0] <= RANGE_BARS]
        buy = any(h[j] > s[1] for s in sh)
        sell = any(l[j] < s[1] for s in sl)
        sh = [s for s in sh if not h[j] > s[1]]
        sl = [s for s in sl if not l[j] < s[1]]
        # gaps: bar j touching them consumes them; then add the gap bar j completes
        bull = [g for g in bull if j - g[0] <= RANGE_BARS and l[j] > g[1]]
        bear = [g for g in bear if j - g[0] <= RANGE_BARS and h[j] < g[1]]
        if j >= 2:
            if l[j] > h[j - 2]:
                bull.append((j, l[j], h[j - 2]))
            if h[j] < l[j - 2]:
                bear.append((j, h[j], l[j - 2]))
        if buy == sell:
            continue
        if buy:     # buy-side purged -> draw down to the nearest bullish gap below
            cand = [g for g in bull if g[1] < cl_[j]]
            if cand:
                g = max(cand, key=lambda z: z[1])
                rows.append((j, -1, g[1], 0.5 * (g[1] + g[2])))
        else:       # sell-side purged -> draw up to the nearest bearish gap above
            cand = [g for g in bear if g[1] > cl_[j]]
            if cand:
                g = min(cand, key=lambda z: z[1])
                rows.append((j, 1, g[1], 0.5 * (g[1] + g[2])))
    if not rows:
        return pd.DataFrame(columns=cols)
    r = np.array(rows, dtype=float)
    pos = r[:, 0].astype(int)
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[pos])
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": r[:, 1].astype(int),
                         "near_edge": r[:, 2], "ce": r[:, 3]})


def main():
    ev = cl.cache_frame(f"{CID}_1h_r50", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    d = ev["direction"].to_numpy(int)
    px0 = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def hit(times, level, dirs):
        out = np.zeros(len(times), bool)
        for s, side in ((1, "above"), (-1, "below")):
            m = dirs == s
            if m.any():
                out[m] = cl.touch(times[m], level[m], side,
                                  horizon_bars=HORIZON_BARS)["hit"].to_numpy()
        return out

    for reading, col in (("a", "near_edge"), ("b", "ce")):
        lvl = ev[col].to_numpy(float)
        dist = lvl - px0                       # signed; preserved in the null
        obs = hit(t, lvl, d)

        def null_fn(rng, k, dist=dist):
            tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
            ok = ~tk.isna()
            out = np.full(len(t), np.nan)
            p = mkt.o[mkt.pos_at_or_after(tk[ok])]
            out[ok] = hit(tk[ok], p + dist[ok], d[ok])
            return out

        res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, claim="+", predictors=ev)
        print(reading, res["n"], res["observed_rate"], res["null_rate"], res["diff"],
              res["ci_lo"], res["ci_hi"], res["verdict"], res["verdict_detail"])
        op = {"rules": ["gold 1h bars; ERL purge at bar j = high above an untaken confirmed "
                        "2/2 swing high from the last 50 bars (sell-side mirror); bars "
                        "purging both sides skipped",
                        "IRL = nearest untouched 3-bar FVG on the opposite side of the close "
                        "(bullish gap below after a buy-side purge, bearish gap above after a "
                        "sell-side purge), formed within the last 50 bars; none -> no event",
                        f"hit = gold reaches the gap's {'near edge' if reading == 'a' else 'consequent encroachment (midpoint)'} "
                        "within 600 M1 bars after bar j's close",
                        "null = same signed distance from the first M1 open at matched random "
                        "moments (+/-30d, 5 reps), same side, same horizon"],
              "params": {"tf": "1h", "swing": "2/2", "range_bars": RANGE_BARS,
                         "reach": col, "horizon_bars": HORIZON_BARS}}
        src = {"tf": "corpus: concept timeframes htf includes 1H (3OivsP1j_UE examples use "
                     "4H/hourly/daily gaps)",
               "swing": "phase3: 2/2 swings (§1.8)",
               "range_bars": "declared-before-run: the corpus bounds 'the current range' by "
                             "no number",
               "reach": ("corpus: 'Reaching' is ambiguous (near edge / CE / fill); reading a "
                         "near edge" if reading == "a" else
                         "corpus: targets 'the fair value gap, commonly its consequent "
                         "encroachment (50%)'"),
               "horizon_bars": "phase3: 10 entry-TF bars (§1.13), as trading minutes"}
        notes = ("The 'fails to displace' qualifier of the rotation (method spec §2.2) is "
                 "not applied; the concept's own rule is 'immediately after external range "
                 "liquidity has been taken'.")
        print("wrote", cl.write_result(CID, reading, res, operationalization=op,
                                       params_source=src, script=__file__, probe=probe,
                                       notes=notes))


if __name__ == "__main__":
    main()
