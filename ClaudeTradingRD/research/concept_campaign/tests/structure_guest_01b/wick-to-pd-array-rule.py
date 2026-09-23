"""wick-to-pd-array-rule (guest: DexterLab, wWIHS_dxbEY) -> rate_test.

Claim: both extremes of any candle terminate inside a PD array of the same or a higher
timeframe.  Measurable: 'percentage of 4H wick extremes that land inside a 4H-or-higher PD
array'.  Reading (declared before the run):
  * Candle = 4H (forex grid).  At the close of 4H bar q the arrays are fixed; the outcome
    is the NEXT 4H candle's high and its low (two rows per candle, cluster = candle).
  * PD arrays (only the three the speaker shows: FVG, order block, breaker-less):
      - FVG: 3-bar gap on 4H and on 1D bars (bull [h[i-2], l[i]], bear [h[i], l[i-2]]);
      - order block: on a close beyond the most recent confirmed fractal 2/2 swing
        (structure break), the last opposing-close bar within the 10 bars before the
        breaking bar; zone = its full high-low range;
    formed at the close of the bar that completes them; active while formed within the
    last 60 4H bars (~10 days) / 20 1D bars and not invalidated by a CLOSE beyond the
    zone's far edge (bull zone: close below its low; bear: close above its high).
    Breakers are not modelled (a failed OB; the broken-OB zone overlaps the OB zone).
  * Hit = the extreme lies inside any active zone (lo <= X <= hi) - 'touch/enter'.
  * Null: the same extreme expressed as a % offset from its candle's open, re-applied to
    the open of the candle after a random OTHER 4H bar within +/-30 days, checked against
    THAT bar's active arrays.  Geometry (distance from open) is preserved; only the
    arrays change.  claim '+': real extremes land in arrays more often than the null.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_guest_01b")
from common01b import cl, bars_arr, structure_breaks, to_utc  # noqa: E402

SWING = (2, 2)
OB_BACK = 10
K4 = 60
KD = 20


def tf_zones(b: dict) -> pd.DataFrame:
    o, h, l, c = b["o"], b["h"], b["l"], b["c"]
    n = len(c)
    z = []
    for i in range(2, n):
        if l[i] > h[i - 2]:
            z.append((i, h[i - 2], l[i], 1))
        if h[i] < l[i - 2]:
            z.append((i, h[i], l[i - 2], -1))
    br = structure_breaks(b, *SWING)
    for i, d in zip(br["bar"].to_numpy(), br["dir"].to_numpy()):
        for k in range(i - 1, max(i - 1 - OB_BACK, -1), -1):
            if (d == 1 and c[k] < o[k]) or (d == -1 and c[k] > o[k]):
                z.append((i, l[k], h[k], int(d)))
                break
    f = pd.DataFrame(z, columns=["form", "lo", "hi", "dir"]).sort_values("form", kind="stable")
    inv = np.full(len(f), n, np.int64)
    fo, lo, hi, dd = (f[x].to_numpy() for x in ("form", "lo", "hi", "dir"))
    for r in range(len(f)):
        seg = c[fo[r] + 1:]
        bad = np.flatnonzero(seg < lo[r]) if dd[r] == 1 else np.flatnonzero(seg > hi[r])
        if len(bad):
            inv[r] = fo[r] + 1 + bad[0]
    f["inv"] = inv
    return f.reset_index(drop=True)


def _active(f: pd.DataFrame, p: int, K: int):
    fo = f["form"].to_numpy()
    a, zz = np.searchsorted(fo, p - K + 1, "left"), np.searchsorted(fo, p, "right")
    s = f.iloc[a:zz]
    s = s[s["inv"].to_numpy() > p]
    return list(zip(s["lo"].round(6).tolist(), s["hi"].round(6).tolist()))


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    H = cl.build_bars(m1, "4h")
    D = cl.build_bars(m1, "1D")
    bh, bd = bars_arr(H), bars_arr(D)
    zh, zd = tf_zones(bh), tf_zones(bd)
    rows = []
    for q in range(len(H)):
        tq = bh["close_t"][q]
        p = int(np.searchsorted(bd["close_t"], tq, "right")) - 1
        zones = _active(zh, q, K4) + (_active(zd, p, KD) if p >= 0 else [])
        rows.append((tq, json.dumps(sorted(zones))))
    f = pd.DataFrame(rows, columns=["t", "zones"])
    f["decision_time"] = to_utc(f["t"].to_numpy())
    f["available_at"] = f["decision_time"]
    f["qid"] = f["t"].astype("int64")
    f = pd.concat([f.assign(side="high"), f.assign(side="low")], ignore_index=True)
    f = f.sort_values(["decision_time", "side"], kind="stable").reset_index(drop=True)
    return f[["decision_time", "available_at", "side", "zones", "qid"]]


def _inside(x, zones):
    return any(lo <= x <= hi for lo, hi in zones)


if __name__ == "__main__":
    ev = cl.cache_frame(f"wick_pd_{SWING}_{OB_BACK}_{K4}_{KD}", lambda: detect(cl.load_m1()))
    print(len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="90D", n_cuts=100)
    print("probe", probe.get("passed"))
    H = cl.build_bars(cl.load_m1(), "4h")
    ct = cl.data.utc_ns(H["close_time"]).view("int64")
    ho, hh, hl = H["open"].to_numpy(), H["high"].to_numpy(), H["low"].to_numpy()
    q = np.searchsorted(ct, cl.data.utc_ns(ev["decision_time"]).view("int64"))
    assert (ct[q] == cl.data.utc_ns(ev["decision_time"]).view("int64")).all()
    has_next = q + 1 < len(H)
    nq = np.minimum(q + 1, len(H) - 1)
    is_hi = (ev["side"] == "high").to_numpy()
    X = np.where(is_hi, hh[nq], hl[nq])
    rel = X / ho[nq]
    Z = [json.loads(s) for s in ev["zones"]]
    obs = np.array([_inside(x, z) for x, z in zip(X, Z)], float)
    obs[~has_next] = np.nan
    print("zones/candle", np.mean([len(z) for z in Z]), "obs rate", np.nanmean(obs))
    # null: random other 4H bar close within +/-30d (grid = 4H closes)
    zmap = {}
    for qi, z in zip(q, Z):
        zmap[int(qi)] = z
    rt = cl.sample_times(ev["decision_time"], cl.rules.CTRL_REPS if hasattr(cl.rules, "CTRL_REPS") else 5,
                         30, seed=cl.rules.SEED, grid_times=H["close_time"].iloc[:-1])

    def null_fn(rng, k):
        tk = rt[:, k]
        out = np.full(len(ev), np.nan)
        ok = ~np.isnat(tk)
        qk = np.searchsorted(ct, tk[ok].astype("int64"))
        vals = []
        for qq, r in zip(qk, rel[ok]):
            nn = qq + 1
            if nn >= len(H) or qq not in zmap:
                vals.append(np.nan)
                continue
            vals.append(float(_inside(ho[nn] * r, zmap[qq])))
        out[ok] = vals
        out[~has_next] = np.nan
        return out

    res = cl.rate_test(obs, ev["decision_time"], available_at=ev["available_at"], null_fn=null_fn,
                       predictors=ev, cluster="qid")
    for k in ("n", "observed_rate", "null_rate", "lift", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail", "ci_method"):
        print(k, res.get(k))
    op = {"rules": [
        "4H candles (forex grid); outcome = the next candle's high and low (2 rows/candle, cluster = candle).",
        "PD arrays on 4H and 1D: 3-bar FVGs; order blocks = last opposing-close bar within 10 bars before a close beyond the most recent confirmed 2/2 swing; zone = bar range.",
        "Active: formed within the last 60 4H / 20 1D bars and not closed through the far edge; all fixed at the prior 4H close.",
        "Hit = extreme inside any active zone. Null = same %-offset from open applied at a random other 4H candle within +/-30d against its own arrays."],
        "params": {"swing_left_right": SWING, "ob_lookback_bars": OB_BACK, "active_4h_bars": K4,
                   "active_1d_bars": KD, "tolerance": "inside [lo, hi]", "grid4h": "forex",
                   "null": "4H-close grid, +/-30d, 5 reps"}}
    ps = {"swing_left_right": "declared-before-run: fractal 2/2",
          "ob_lookback_bars": "declared-before-run: 10 bars",
          "active_4h_bars": "declared-before-run: 60 4H bars (~10 trading days)",
          "active_1d_bars": "declared-before-run: 20 daily bars (~1 month)",
          "tolerance": "declared-before-run: the extreme must lie inside the zone (corpus leaves tolerance open)",
          "grid4h": "session_window_fit: forex grid (carried as a knob)",
          "null": "declared-before-run: locked reps/window of the harness"}
    notes = ("Breakers and 1W/1M arrays not modelled (1D is the highest array TF used). The null keeps each "
             "extreme's distance from its candle open and swaps only the arrays, so zone density near price cancels.")
    print(cl.write_result("wick-to-pd-array-rule", None, res, operationalization=op, params_source=ps,
                          script=__file__, probe=probe, notes=notes))
