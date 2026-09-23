"""t-spot — rate_test, two readings (contested; the indicator's derivation is withheld).

Setting: a 4h (forex grid) C2 closure carrying a same-direction 15m CISD inside it (the
"printed model" the T-spot is drawn after). The T-spot is where the NEXT candle's (C3's) wick
is expected to form; price must not trade through and beyond it.
Prediction tested: C3 does not trade beyond the T-spot's far edge.
  hit = any M1 low <= level (bullish) / high >= level (bearish) during the C3 candle
  (horizon = C3's own M1-bar count). claim '-': the hit rate is LOWER than a matched null
  (same distance from the first price, same side, same bar count, at matched random moments
  +/-30d).
Reading a — "in this case is just the equilibrium" (-KKuZb5Z5aU): level = EQ of C2 = 50% of its
  wick-high-to-wick-low range (equilibrium-eq: fib wick to wick, not bodies).
Reading b — overlap of two half levels (ES walkthrough): 0.5 of C2's sweeping wick (body edge to
  extreme) and 0.5 of the CISD's opposing-series bodies; far edge of the band = the deeper of the two.
Rows kept only when the C2 close is on the holding side of the level.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b")
from _common import cl, np, pd, c2_book, PHASE3_SRC

CID = "t-spot"


def _detect(m1, which):
    cols = ["decision_time", "available_at", "direction", "level"]
    bk = c2_book(m1)
    if bk.empty:
        return pd.DataFrame(columns=cols)
    s = bk["sgn"].to_numpy()
    o, h, l, c = (bk[k].to_numpy(float) for k in ("o", "h", "l", "c"))
    if which == "a":
        lvl = (h + l) / 2.0
    else:
        hw = np.where(s > 0, (np.minimum(o, c) + l) / 2.0, (np.maximum(o, c) + h) / 2.0)
        mt = bk["cisd_mt"].to_numpy(float)
        lvl = np.where(s > 0, np.minimum(hw, mt), np.maximum(hw, mt))
    keep = np.where(s > 0, c > lvl, c < lvl)
    t = pd.DatetimeIndex(bk["c2_close"])
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": s, "level": lvl})
    return out[keep].reset_index(drop=True)[cols]


def detect_a(m1):
    return _detect(m1, "a")


def detect_b(m1):
    return _detect(m1, "b")


def run(which):
    det = detect_a if which == "a" else detect_b
    ev = cl.cache_frame(f"{CID}_{which}_4h15m", lambda: det(cl.load_m1()))
    probe = cl.probe_lookahead(det, ev, lookback="10D")
    print(which, len(ev), "probe", probe["passed"], probe["events_compared"])
    mkt = cl.get_market()
    b4 = cl.bars("4h")
    t = pd.DatetimeIndex(ev["decision_time"])
    starts = b4.index.tz_convert("UTC").as_unit("ns").asi8
    pos = np.searchsorted(starts, t.as_unit("ns").asi8, side="left")
    ok = pos < len(b4)
    nxt = np.where(ok, b4["n_m1"].to_numpy()[np.minimum(pos, len(b4) - 1)], 0).astype(np.int64)
    s = ev["direction"].to_numpy()
    lvl = ev["level"].to_numpy(float)
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = (first_px - lvl) * s                                  # >0: level on the holding side
    obs = np.full(len(ev), np.nan)
    for sg, side in ((1, "below"), (-1, "above")):
        m = (s == sg) & ok & (nxt > 0)
        obs[m] = cl.touch(t[m], lvl[m], side, horizon_bars=nxt[m])["hit"].to_numpy()
    rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(t), np.nan)
        for sg, side in ((1, "below"), (-1, "above")):
            m = (~tk.isna()) & (s == sg) & ok & (nxt > 0)
            px = mkt.o[mkt.pos_at_or_after(tk[m])]
            out[m] = cl.touch(tk[m], px - sg * dist[m], side, horizon_bars=nxt[m])["hit"].to_numpy()
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]), null_fn=null_fn,
                       claim="-", predictors=ev)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p")})
    lv = ("C2 EQ = (high+low)/2" if which == "a" else
          "deeper of 0.5 of C2's sweeping wick (body edge to extreme) and the 15m CISD opposing-series "
          "body midpoint")
    op = {"rules": [
        "4h forex-grid C2 (sweep prior extreme, close back inside) carrying a same-direction 15m CISD "
        "(series_open, 2/2, max_wait 3) with extreme and confirm inside C2 (the printed model)",
        f"T-spot level: {lv}; row kept only if the C2 close is on the holding side",
        "hit = C3 (next 4h candle, its M1-bar count) trades beyond the level (bullish: low<=level)",
        "null: same signed distance from the first M1 open, same side and bar count, at 5 matched "
        "random moments within +/-30 days"],
        "params": {"htf": "4h", "grid4h": "forex", "ltf": "15min", "level_rule": "series_open",
                   "swing": "2/2", "max_wait": 3, "tspot": ("EQ of C2" if which == "a" else
                                                           "overlap of 0.5 wick and 0.5 CISD bodies"),
                   "horizon": "C3 candle, M1 bars"}}
    src = {"htf": "corpus: t-spot.yaml timeframes htf 1D/4H/1H ltf 15m/5m; method_spec §1.3 4H/15m",
           "grid4h": PHASE3_SRC, "ltf": "corpus: t-spot.yaml ltf 15m", "level_rule": PHASE3_SRC,
           "swing": PHASE3_SRC, "max_wait": PHASE3_SRC,
           "tspot": ("corpus: -KKuZb5Z5aU 'we have the T-spot marked up, which in this case is just the "
                     "equilibrium'; method_spec §3.7 EQ wick-high to wick-low" if which == "a" else
                     "corpus: t-spot.yaml variant 2 (ES walkthrough) overlap of 0.5 of the HTF wick with 0.5 "
                     "of the change in the state of delivery; method_spec §3.6 half-wick body-to-extreme"),
           "horizon": "corpus: Hi8faa5u2uw T-spot is where the higher-timeframe (next candle's) wick is anticipated"}
    p = cl.write_result(CID, which, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes="T-spot derivation is withheld (paywalled indicator); this tests "
                        "the two attested public constructions only")
    print(p)


if __name__ == "__main__":
    run(sys.argv[1])
