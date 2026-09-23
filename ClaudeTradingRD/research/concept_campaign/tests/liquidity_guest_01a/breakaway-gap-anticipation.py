"""breakaway-gap-anticipation (DayTradingRauf, guest) — rate_test on 1H gold FVGs.

Claim: a fair value gap that OVERLAPS a mitigation block is a breakaway gap and is
expected to stay OPEN (not be filled). Measurable named in the concept: fill rate of
FVGs overlapping a mitigation block versus those that do not.

Operationalisation (declared before the first run):
  * 1H gold bars; three-bar FVG stamped on the third bar i (detectors.primitives
    definition), only when bars i-2, i-1, i are consecutive hours (no halt inside).
  * Mitigation block, bullish case (Rauf's variant of mitigation-block): an
    UP-close candle u in the 40 bars before the FVG's first candle (u <= i-3) whose
    LOW was later broken by a bar before i-2 (it sits on the sell side of the leg),
    and which itself traded into fair value: its high reached the bottom of a
    bearish FVG formed in the 10 bars before u. Bearish case mirrors (down-close
    candle, high broken, low reached into a prior bullish FVG). Consecutive candles
    are covered because overlap with any member = overlap with the merged block.
  * overlap = the block's [low, high] and the gap intersect with positive length,
    block on the same side (bullish block for a bullish gap).
  * outcome 'filled' = price trades through the gap's far edge (bullish: low <= gap
    bottom) within 120 1H bars' worth of M1 trading minutes (7,200) after the gap's
    third bar closes.
  * matched null = the fill outcome of NON-overlap same-direction FVGs within +/-30
    days whose distance from the decision close to the far edge (in % of price) is
    closest to the overlap gap's: rep k takes the k-th nearest (k = 0..4). So the
    null asks the same-distance question of ordinary gaps in the same regime.
claim '-': overlap gaps fill LESS than matched ordinary gaps.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

L_MB, L_FV, H_M1, WIN_D = 40, 10, 7200, 30


def detect_all(m1):
    b = cl.build_bars(m1, "1h")
    o, h, l, c = (b[x].to_numpy() for x in ("open", "high", "low", "close"))
    t = b.index
    ct = pd.DatetimeIndex(b.close_time)
    n = len(b)
    consec = np.zeros(n, bool)
    dt = np.diff(t.as_unit("ns").asi8)
    one = pd.Timedelta(hours=1).value
    consec[2:] = (dt[1:] == one) & (dt[:-1] == one)
    bull = np.zeros(n, bool); bear = np.zeros(n, bool)
    bull[2:] = l[2:] > h[:-2]
    bear[2:] = h[2:] < l[:-2]
    bull &= consec; bear &= consec
    # blocks: bullish-context mitigation block candidates (up-close, low later broken,
    # high reached a prior bearish FVG bottom), and the bearish mirror.
    up = c > o
    dn = c < o
    rows = []
    for i in np.flatnonzero(bull | bear):
        isb = bool(bull[i])
        glo, ghi = (h[i - 2], l[i]) if isb else (h[i], l[i - 2])
        ov = False
        for u in range(max(L_FV + 2, i - 2 - L_MB), i - 2):
            if isb:
                if not up[u]:
                    continue
                if not (l[u + 1:i - 2] < l[u]).any():
                    continue
                ks = np.arange(max(2, u - L_FV), u)
                fv = ks[h[ks] < l[ks - 2]]              # bearish FVGs before u, bottom = h[k]
                if not (len(fv) and (h[u] >= h[fv]).any()):
                    continue
            else:
                if not dn[u]:
                    continue
                if not (h[u + 1:i - 2] > h[u]).any():
                    continue
                ks = np.arange(max(2, u - L_FV), u)
                fv = ks[l[ks] > h[ks - 2]]              # bullish FVGs before u, top = l[k]
                if not (len(fv) and (l[u] <= l[fv]).any()):
                    continue
            if min(h[u], ghi) - max(l[u], glo) > 0:
                ov = True
                break
        far = glo if isb else ghi
        rows.append({"decision_time": ct[i], "available_at": ct[i],
                     "direction": 1 if isb else -1, "gap_low": float(glo),
                     "gap_high": float(ghi), "far_edge": float(far),
                     "dist_pct": float(abs(c[i] - far) / c[i]), "overlap": ov})
    return pd.DataFrame(rows, columns=["decision_time", "available_at", "direction",
                                       "gap_low", "gap_high", "far_edge", "dist_pct",
                                       "overlap"])


def detect(m1):
    a = detect_all(m1)
    return a[a["overlap"]].reset_index(drop=True)


def fill(times, far, direction):
    t = pd.DatetimeIndex(times)
    hit = np.zeros(len(t), bool)
    for d, side in ((1, "below"), (-1, "above")):
        s = np.asarray(direction) == d
        if s.any():
            hit[s] = cl.touch(t[s], np.asarray(far)[s], side, horizon_bars=H_M1)["hit"].to_numpy()
    return hit


if __name__ == "__main__":
    allf = cl.cache_frame("breakaway_fvg_all_1h", lambda: detect_all(cl.load_m1()))
    ev = cl.cache_frame("breakaway_fvg_overlap_1h", lambda: detect(cl.load_m1()))
    print(len(allf), allf.overlap.mean(), len(ev))
    probe_all = cl.probe_lookahead(detect_all, allf, lookback="10D")
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probes", probe_all["passed"], probe["passed"])
    obs = fill(ev.decision_time, ev.far_edge, ev.direction).astype(float)
    base = allf[~allf.overlap].reset_index(drop=True)
    base_hit = fill(base.decision_time, base.far_edge, base.direction).astype(float)
    bt = pd.DatetimeIndex(base.decision_time).as_unit("ns").asi8
    bdir = base.direction.to_numpy(); bdist = np.log(base.dist_pct.clip(lower=1e-6).to_numpy())
    # precompute the 5 nearest matches per overlap event
    et = pd.DatetimeIndex(ev.decision_time).as_unit("ns").asi8; edir = ev.direction.to_numpy()
    edist = np.log(ev.dist_pct.clip(lower=1e-6).to_numpy())
    win = pd.Timedelta(days=WIN_D).value
    match = np.full((len(ev), 5), -1)
    lo_i = np.searchsorted(bt, et - win); hi_i = np.searchsorted(bt, et + win)
    for q in range(len(ev)):
        cand = np.arange(lo_i[q], hi_i[q])
        cand = cand[bdir[cand] == edir[q]]
        if len(cand) < 5:
            continue
        order = cand[np.argsort(np.abs(bdist[cand] - edist[q]), kind="stable")[:5]]
        match[q] = order
    ok = (match >= 0).all(1)
    print("matched", ok.mean())
    obs[~ok] = np.nan

    def null_fn(rng, k):
        out = np.full(len(ev), np.nan)
        out[ok] = base_hit[match[ok, k]]
        return out

    res = cl.rate_test(obs, ev.decision_time, available_at=ev.available_at, null_fn=null_fn,
                       claim="-", predictors=ev, outcome_horizon="5D")
    print({k: res.get(k) for k in ("n", "rate", "null_rate", "diff", "ci_lo", "ci_hi", "p",
                                   "verdict", "verdict_detail")})
    p = cl.write_result(
        "breakaway-gap-anticipation", None, res,
        operationalization={"rules": [
            "1H gold bars; 3-bar FVG on consecutive hours, stamped at the third bar's close",
            "mitigation block (bullish): up-close candle within 40 bars before the FVG, low later broken before the FVG, high reached into a bearish FVG formed in the 10 bars before it; bearish mirrors",
            "overlap: block [low, high] intersects the gap with positive length",
            "observed: overlap gap filled through its far edge within 7,200 M1 trading minutes (~120 1H bars)",
            "null: the same fill outcome for the k-th nearest-distance (far edge, % of price) non-overlap same-direction FVG within +/-30 days, k=0..4",
            "claim '-': overlap (breakaway) gaps fill less often"],
            "params": {"tf": "1h", "mb_lookback_bars": L_MB, "mb_fair_value_lookback_bars": L_FV,
                       "fill_horizon_m1_bars": H_M1, "null_window_days": WIN_D,
                       "three_gap_rule": "not tested (stated once, no example)"}},
        params_source={
            "tf": "corpus: wB-fQiT_UDo timeframes ltf 1H (htf 1W/1D too thin)",
            "mb_lookback_bars": "declared-before-run: the leg preceding the gap, 40 1H bars",
            "mb_fair_value_lookback_bars": "declared-before-run: 'traded into fair value' = into an FVG from the prior 10 bars",
            "fill_horizon_m1_bars": "declared-before-run: about one trading week",
            "null_window_days": "phase3: control window +/-30 days",
            "three_gap_rule": "declared-before-run: excluded"},
        script=__file__, probe=probe,
        notes=f"{len(allf)} FVGs, overlap share {allf.overlap.mean():.3f}; {int(ok.sum())} overlap gaps had 5 matches. "
              f"The non-overlap null pool comes from detect_all, probed separately (passed={probe_all['passed']}).")
    print(p)
