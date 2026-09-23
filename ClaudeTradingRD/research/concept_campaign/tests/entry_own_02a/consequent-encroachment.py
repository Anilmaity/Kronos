"""consequent-encroachment -- the 50% (CE) of a fair value gap decides the gap's fate.

Rate tests (a level-behaviour prediction), 1H FVGs (YAML htf includes 1H).
FVG (method_spec 3.9, wicks): bullish low[i] > high[i-2], gap = (high[i-2], low[i]);
bearish mirror. CE = (gap_high + gap_low)/2. Known at bar i's close.
Event = the FIRST later 1H bar (within 48 bars) whose wick reaches the CE, provided
no earlier bar closed beyond the far edge. That bar's close splits the two uses:
  a  Reading A (ZVUDpCyvxfQ, invalidation): the bar CLOSES beyond the CE but not beyond
     the far edge -> "anticipate price working through the rest of the gap".
     hit = price trades beyond the far edge within 10 1H bars (600 trading minutes).
  b  RESPECT (both readings agree; YAML detection rule 2): the bar trades to the CE and
     closes back on the respecting side -> "continuation expected".
     hit = price reaches the extreme of the displacement leg (highest high / lowest
     low from the gap's first candle up to the event) within 600 trading minutes.
Null (both): the same signed distance from the next M1 open, same horizon in M1
bars, at matched random moments (reps 5, +/-30 d, locked seed). claim '+'.
Reading B's own claim (a CE close is only a 'hint') predicts a weaker/zero effect
in (a); (a) therefore decides between A and B.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "consequent-encroachment"
TF = "1h"
LIFE = 48
HORIZON_BARS = 600


def detect(m1):
    b = cl.build_bars(m1, TF)
    o, h, l, c = (b[k].to_numpy() for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    n = len(b)
    rows = []
    for i in range(2, n):
        for bull in (True, False):
            if bull and l[i] > h[i - 2]:
                glo, ghi = h[i - 2], l[i]
            elif (not bull) and h[i] < l[i - 2]:
                glo, ghi = h[i], l[i - 2]
            else:
                continue
            ce = (glo + ghi) / 2.0
            for m in range(i + 1, min(n, i + 1 + LIFE)):
                if bull:
                    if l[m] <= ce:
                        if c[m] < glo:
                            break                       # closed through the whole gap
                        if c[m] < ce:
                            rows.append(("a", ct[m], -1, glo, "below", ct[i]))
                        else:
                            rows.append(("b", ct[m], 1, h[i - 2:m + 1].max(), "above", ct[i]))
                        break
                    if c[m] < glo:
                        break
                else:
                    if h[m] >= ce:
                        if c[m] > ghi:
                            break
                        if c[m] > ce:
                            rows.append(("a", ct[m], 1, ghi, "above", ct[i]))
                        else:
                            rows.append(("b", ct[m], -1, l[i - 2:m + 1].min(), "below", ct[i]))
                        break
                    if c[m] > ghi:
                        break
    cols = ["decision_time", "available_at", "reading", "direction", "level", "side",
            "fvg_time"]
    if not rows:
        return pd.DataFrame(columns=cols)
    r = pd.DataFrame(rows, columns=["reading", "decision_time", "direction", "level",
                                    "side", "fvg_time"])
    r["available_at"] = r["decision_time"]
    return (r.sort_values(["reading", "decision_time", "fvg_time"])
             .reset_index(drop=True)[cols])


def book(m1, reading):
    e = detect(m1)
    return e[e["reading"] == reading].reset_index(drop=True)


if __name__ == "__main__":
    full = cl.cache_frame(f"{CID}_1h_v1", lambda: detect(cl.load_m1()))
    mkt = cl.get_market()
    for reading, desc in (
            ("a", "event: first CE touch closes beyond the CE but inside the gap; hit = the "
                  "far edge is traded through within 600 trading minutes"),
            ("b", "event: first CE touch closes back on the respecting side; hit = the "
                  "displacement leg's extreme is reached within 600 trading minutes")):
        ev = full[full["reading"] == reading].reset_index(drop=True)
        probe = cl.probe_lookahead(lambda m, r=reading: book(m, r), ev, lookback="10D")
        t = pd.DatetimeIndex(ev["decision_time"])
        lvl = ev["level"].to_numpy(float)
        side = ev["side"].to_numpy()
        up = side == "above"
        i0 = np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)
        dist = lvl - mkt.o[i0]
        obs = np.zeros(len(t))
        for sd, msk in (("above", up), ("below", ~up)):
            obs[msk] = cl.touch(t[msk], lvl[msk], sd,
                                horizon_bars=HORIZON_BARS)["hit"].to_numpy()
        rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

        def null_fn(rng, k, rt=rt, dist=dist, up=up):
            tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC") \
                if pd.DatetimeIndex(rt[:, k]).tz is None else pd.DatetimeIndex(rt[:, k])
            out = np.full(len(tk), np.nan)
            ok = ~tk.isna()
            for sd, msk in (("above", up), ("below", ~up)):
                sel = ok & msk
                if sel.any():
                    px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[sel]), len(mkt.o) - 1)]
                    out[sel] = cl.touch(tk[sel], px + dist[sel], sd,
                                        horizon_bars=HORIZON_BARS)["hit"].to_numpy()
            return out

        res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                           null_fn=null_fn, predictors=ev, cluster="fvg_time")
        print(reading, {k: res.get(k) for k in ("n", "observed_rate", "null_rate", "diff",
                                                  "ci_lo", "ci_hi", "p", "verdict",
                                                  "verdict_detail")})
        p = cl.write_result(CID, reading, res, operationalization={"rules": [
            "1H wick-defined FVGs (method_spec 3.9); CE = gap midpoint",
            "first 1H bar within 48 bars whose wick reaches the CE (no earlier close "
            "beyond the far edge)", desc,
            "null: same signed distance from the next M1 open, same M1-bar horizon, "
            "matched random moments; claim '+'"],
            "params": {"tf": TF, "fvg_life_bars": LIFE, "horizon_m1_bars": HORIZON_BARS,
                       "ce": "midpoint of gap boundary prices"}},
            params_source={"tf": "corpus: YAML htf 1H (fractal); phase3 1H HTF",
                           "fvg_life_bars": "declared-before-run: a gap is watched for 48 "
                                            "1H bars (2 days)",
                           "horizon_m1_bars": "phase3: 10 entry-TF bars (10 x 1H = 600 "
                                              "trading minutes)",
                           "ce": "corpus: YAML 'ce := (gap_high + gap_low) / 2'"},
            script=__file__, probe=probe,
            notes="Reading a tests Reading A (CE close = invalidation, predicts the far edge "
                  "is taken); Reading B (a CE close is only a hint) is the alternative this "
                  "same statistic arbitrates. Reading b tests the respect->continuation use "
                  "both readings share. Clustered by FVG.")
        print("wrote", p)
