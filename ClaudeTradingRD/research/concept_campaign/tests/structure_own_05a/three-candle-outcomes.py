"""three-candle-outcomes (TTrades own voice) — batch structure_own_05a.

The concept is an exhaustive taxonomy (consolidate / take one side / take both) and is
used as the JUSTIFICATION for marking the previous candle's high and low as the candidate
draws: "unless the period consolidates, it must reach for one or both sides, so those two
levels are the candidate draws" (YESqIoA7Wyg). The taxonomy itself is true by
construction; the testable content is that the previous candle's two extremes are drawn
to MORE than equally distant arbitrary levels.

rate_test (daily, the corpus's first listed use):
  predictor : at each trading-day close (18:00 NY roll), the day's high (PDH) and low (PDL)
  hit       : the next session trades to PDH OR PDL (any M1 high >= PDH or low <= PDL)
              within that session's M1-bar count (i.e. it does not consolidate = inside day)
  null      : at matched random moments (+/-30d, locked reps/seed) the same two distances
              above and below the first price, the same bar count; hit if either is touched.
claim '+': previous-candle levels are reached more often than geometry alone implies.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05a")
from _common import cl, np, pd, summary  # noqa: E402

CID = "three-candle-outcomes"
MIN_BARS = 600          # declared-before-run: skip stub / holiday sessions (example_rate)


def main():
    mkt = cl.get_market()
    d = cl.bars("1D")
    d = d[d["n_m1"] > MIN_BARS]
    t = pd.DatetimeIndex(d["close_time"].iloc[:-1])
    pdh = d["high"].iloc[:-1].to_numpy()
    pdl = d["low"].iloc[:-1].to_numpy()
    nxt = d["n_m1"].iloc[1:].to_numpy()
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    up = cl.touch(t, pdh, "above", horizon_bars=nxt)["hit"].to_numpy()
    dn = cl.touch(t, pdl, "below", horizon_bars=nxt)["hit"].to_numpy()
    obs = (up | dn).astype(float)
    dh, dl = pdh - first_px, first_px - pdl
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        px = mkt.o[mkt.pos_at_or_after(tk[ok])]
        a = cl.touch(tk[ok], px + dh[ok], "above", horizon_bars=nxt[ok])["hit"].to_numpy()
        b = cl.touch(tk[ok], px - dl[ok], "below", horizon_bars=nxt[ok])["hit"].to_numpy()
        out[ok] = (a | b)
        return out

    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, claim="+")
    print(summary(res))
    print("  share one-sided up/down/both/inside:",
          round(float((up & ~dn).mean()), 3), round(float((dn & ~up).mean()), 3),
          round(float((up & dn).mean()), 3), round(float((~up & ~dn).mean()), 3))
    op = {"rules": [
        "at each NY trading-day close (18:00 NY roll) take that day's high (PDH) and low (PDL)",
        "hit = the next session trades to PDH or PDL (M1 high >= PDH or M1 low <= PDL) within "
        "the next session's M1-bar count (= the next candle is NOT an inside/consolidation candle)",
        "null = the same two distances above/below the first price at matched random moments "
        "(+/-30d), same bar count; hit if either is touched"],
        "params": {"tf": "1D", "day_open_hour": 18, "min_session_bars": MIN_BARS,
                   "take_out": "wick (any trade through)", "horizon": "next session, M1 bars"}}
    src = {"tf": "corpus: YESqIoA7Wyg 'there are three ways a Candlestick can form' (daily/weekly/monthly; daily is the first listed)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "min_session_bars": "declared-before-run: stub-session filter as in concept_lab example_rate",
           "take_out": "declared-before-run: yaml ambiguity (wick vs close) - the classification's own rules use high>PH / low<PL, i.e. a wick",
           "horizon": "declared-before-run: one candle of the same timeframe"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__,
                        no_detector="pure level rule: the prior trading day's high and low from "
                                    "bars('1D') at that bar's close_time; no detector",
                        notes="The three-way classification is exhaustive by construction and "
                              "carries no probability; what is tested is the use it is put to - "
                              "previous-candle extremes as the candidate draws - against an "
                              "equal-distance null (either side).")
    print("wrote", p)


if __name__ == "__main__":
    main()
