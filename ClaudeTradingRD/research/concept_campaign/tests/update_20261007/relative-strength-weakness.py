"""relative-strength-weakness -- update_20261007 (edu_01 draft, yH4eYwUgdTY). New claims only.

Prior readings a/b (structure_own_03b, gold vs SILVER, NULL/NULL) tested separation alone and
swing-taken alone. This draft adds (1) INPUT PRIORITY -- "this is what I use when SMT is not
present": rank by SMT first, separation only without SMT; (2) the C2-CLOSURE test -- "we sweep
out the low, but we can't close bullish or back above candle one's low"; (3) the CISD-closure
test; (4) generalisation to gold vs gold-GBP / gold-euro.
(3) is NOT re-run: gold vs XAUGBP on the CISD-validating candle is already written as
relative-strength-asset-selection__u1007a (NULL). Both readings here use gold vs XAU_EUR, the
pair on which the transcript demonstrates both separation ("gold euro is stronger") and the
C2-style closure ("sweeping out the high, closing below, while this one is closing over").
Gold is the only traded asset, so "long the stronger / short the weaker" becomes a gate:
gold trades where gold IS the right asset vs gold trades where it is not. claim '+'.

Fixed BEFORE the first run:
  u1007a  baseline = phase-3 gold 1h rung-0 CISD book (series_open, 2/2, max_wait 3), stop
          protected swing, 2R, 10h -- identical to prior readings a/b. Shared level = each
          asset's prior trading-day low (longs) / high (shorts), 18:00 NY roll, from the
          inner-joined H1 bars. SMT present iff exactly one asset's running extreme today
          (through the decision bar) went beyond its level; then gold is right iff gold did NOT
          take its level while XAU_EUR did (higher low -> stronger, for a long; lower high ->
          weaker, for a short). Without SMT: separation of the decision close
          from the shared level / own prior-day range; farther above the low = stronger,
          farther below the high = weaker. gate = gold is the right asset.
  u1007b  gold 1h C2 = sweeps prior 1h bar's low (high), closes back at/above (at/below) it,
          closes bullish (bearish) -- the sibling gold-correlated-assets 1h C2 definition.
          Keep only C2s where XAU_EUR also swept its own prior-hour extreme on that hour
          (both swept = the closure case; one-sided = SMT, tested elsewhere). gate = XAU_EUR
          could NOT close back above its C1 low (below its C1 high) -> gold the stronger
          (weaker) asset; complement = XAU_EUR closed back too. Trade gold: next M1 open,
          reversal direction, stop C2 extreme, 2R, 10h.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03b")
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import concept_lab as cl  # noqa: E402
from _common import cisd_book  # noqa: E402  (the prior readings' baseline book)

CID = "relative-strength-weakness"
H1 = pd.Timedelta(hours=1)
MAX_HOLD = "10h"
RR = 2.0
EUR_FILE = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_own_02b/data/xau_eur_h1.parquet")
_RAW = {}


def xau_eur():
    if "e" not in _RAW:
        d = pd.read_parquet(EUR_FILE)[["open", "high", "low", "close"]].astype("float64")
        d.index = pd.DatetimeIndex(d.index).tz_convert("UTC")
        _RAW["e"] = d.sort_index()
    return _RAW["e"]


def eur_cut(m1):
    """XAU_EUR H1 cut to gold's last (possibly partial) bar: the probe truncates it too."""
    x = xau_eur()
    return x[x.index + H1 <= m1.index[-1] + H1]


def detect_prio(m1):
    ev, _ = cisd_book(m1, "1h")
    g = cl.build_bars(m1, "1h")
    x = eur_cut(m1)
    idx = g.index.intersection(x.index)
    G, X = g.loc[idx], x.loc[idx]
    P = pd.DataFrame({"g_high": G.high, "g_low": G.low, "g_close": G.close,
                      "e_high": X.high, "e_low": X.low, "e_close": X.close,
                      "close_time": G.close_time}, index=idx)
    td = cl.trading_day(P.index)
    k = td.to_numpy()
    day = P.assign(td=td).groupby("td").agg(g_h=("g_high", "max"), g_l=("g_low", "min"),
                                            e_h=("e_high", "max"), e_l=("e_low", "min"))
    pr = day.shift(1).reindex(td).set_axis(P.index)   # prior trading day, complete
    run = {"g_rh": P["g_high"].groupby(k).cummax().to_numpy(),
           "g_rl": P["g_low"].groupby(k).cummin().to_numpy(),
           "e_rh": P["e_high"].groupby(k).cummax().to_numpy(),
           "e_rl": P["e_low"].groupby(k).cummin().to_numpy()}   # today's running extreme, through each bar
    ct = cl.data.utc_ns(pd.DatetimeIndex(P["close_time"]))
    tn = cl.data.utc_ns(pd.DatetimeIndex(ev["decision_time"]))
    j = np.minimum(np.searchsorted(ct, tn), len(ct) - 1)
    hit = ct[j] == tn                                  # the joined bar closing at the decision
    ev, j = ev[hit].reset_index(drop=True), j[hit]
    gh, gl = pr["g_h"].to_numpy()[j], pr["g_l"].to_numpy()[j]
    eh, el = pr["e_h"].to_numpy()[j], pr["e_l"].to_numpy()[j]
    ok = ~np.isnan(gh) & ~np.isnan(eh) & (gh > gl) & (eh > el)
    ev, j, gh, gl, eh, el = ev[ok].reset_index(drop=True), j[ok], gh[ok], gl[ok], eh[ok], el[ok]
    d = ev["direction"].to_numpy()
    gc, ec = P["g_close"].to_numpy()[j], P["e_close"].to_numpy()[j]
    long_ = d == 1
    took_g = np.where(long_, run["g_rl"][j] < gl, run["g_rh"][j] > gh)
    took_e = np.where(long_, run["e_rl"][j] < el, run["e_rh"][j] > eh)
    smt = took_g != took_e
    sep_g = np.where(long_, (gc - gl) / (gh - gl), (gh - gc) / (gh - gl))
    sep_e = np.where(long_, (ec - el) / (eh - el), (eh - ec) / (eh - el))
    sep_right = sep_g > sep_e          # long: farther above its low = stronger; short: farther below its high = weaker
    ev["smt"] = smt
    ev["sep_right"] = sep_right
    ev["gold_right"] = np.where(smt, ~took_g, sep_right)
    return ev.drop(columns=["bar_pos", "px"])


def detect_c2(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "eur_fail_close"]
    g = cl.build_bars(m1, "1h")
    if len(g) < 3:
        return pd.DataFrame(columns=cols)
    X = eur_cut(m1).reindex(g.index)                   # NaN where XAU_EUR lacks the hour
    o, h, l, c = (g[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    eh, el, ec = (X[k].to_numpy(float) for k in ("high", "low", "close"))
    sh = lambda a: np.r_[np.nan, a[:-1]]               # noqa: E731  C1 = previous gold bar
    ph, pl, eph, epl = sh(h), sh(l), sh(eh), sh(el)
    have = np.isfinite(eh) & np.isfinite(el) & np.isfinite(ec) & np.isfinite(eph) & np.isfinite(epl)
    bull = (l < pl) & (c >= pl) & (c > o)
    bear = (h > ph) & (c <= ph) & (c < o)
    with np.errstate(invalid="ignore"):
        e_swept = np.where(bull, el < epl, eh > eph)
        e_back = np.where(bull, ec >= epl, ec <= eph)
    sel = (bull | bear) & have & e_swept
    i = np.flatnonzero(sel)
    if not len(i):
        return pd.DataFrame(columns=cols)
    d = np.where(bull[i], 1, -1)
    close = pd.DatetimeIndex(g["close_time"].to_numpy()[i]).tz_convert("UTC")
    return pd.DataFrame({"decision_time": close, "available_at": close, "direction": d,
                         "stop_px": np.where(d == 1, l[i], h[i]), "rr": RR,
                         "eur_fail_close": ~e_back[i].astype(bool)})


SRC_COMMON = {
    "correlate": "corpus: yH4eYwUgdTY 'This asset here on the left or gold euro is stronger' (gold vs gold-euro example); OANDA XAU_EUR H1 mid, liquidity_own_02b/data (2015-12-01 on)",
    "rr": "phase3: locked 2R target",
    "max_hold": "phase3: 10 entry-TF bars (1h -> 10h wall clock), as prior readings a/b",
}


def run_prio():
    ev = cl.cache_frame("rsw_u1007a_cisd1h_xaueur_prio", lambda: detect_prio(cl.load_m1()))
    agree = float((ev["gold_right"] == ev["sep_right"]).mean())
    print("u1007a", len(ev), "smt share", round(float(ev.smt.mean()), 3), "gate", round(float(ev.gold_right.mean()), 3),
          "agree w/ separation-only", round(agree, 3))
    probe = cl.probe_lookahead(detect_prio, ev, lookback="10D")
    res = cl.gate_test(ev, "gold_right", mask_available_at="decision_time", max_hold=MAX_HOLD, claim="+")
    rules = [
        "gold 1h and XAU_EUR H1 (OANDA mid) inner-joined on gold 1h labels; correlate cut at gold's last bar",
        "baseline: gold 1h rung-0 CISD (series_open, 2/2, max_wait 3), decide at confirm-bar close, next M1 open, stop protected swing, 2R, 10h; CISD direction = side",
        "shared level per asset: prior trading-day (18:00 NY) low for longs / high for shorts, from the joined bars",
        "SMT: exactly one asset's running low (high) today through the decision bar went beyond its level -> gold right iff gold did NOT take its level",
        "no SMT (neither or both took it): separation = decision close's distance from the shared low (longs, larger = stronger) / below the shared high (shorts, larger = weaker), / own prior-day range -> gold right iff gold's > XAU_EUR's",
        "gate = gold is the right asset (stronger for longs, weaker for shorts); complement = XAU_EUR is; claim '+'",
    ]
    params = {"baseline_tf": "1h", "correlate": "XAU_EUR H1", "reference": "prior-day low (long) / high (short)",
              "priority": "SMT first, separation only without SMT", "normalisation": "own prior-day range",
              "max_wait": 3, "rr": RR, "max_hold": MAX_HOLD}
    src = dict(SRC_COMMON)
    src.update({
        "baseline_tf": "phase3: rung-0 1h CISD book; 1H is the finest the correlate supports (same baseline as prior readings a/b)",
        "reference": "corpus: library precondition 'A shared reference level exists across the assets (e.g. previous day high/low)'; yH4eYwUgdTY 'the one that makes the higher low is the stronger asset' (lows for longs)",
        "priority": "corpus: yH4eYwUgdTY 'this is what I use when SMT is not present'",
        "normalisation": "declared-before-run: points not comparable across assets; divide by own prior-day range (as prior reading a)",
        "max_wait": "phase3: locked CISD config max_wait=3",
    })
    notes = (f"{len(ev)} gold 1h CISDs; SMT present on {ev.smt.mean():.1%}; gate fires {ev.gold_right.mean():.1%}; "
             f"priority ranking equals separation-only on {agree:.1%} of rows. CISD-closure test not re-run "
             "(= relative-strength-asset-selection__u1007a, gold vs XAUGBP, NULL).")
    return res, rules, params, src, probe, notes


def run_c2():
    ev = cl.cache_frame("rsw_u1007b_c2_1h_xaueur", lambda: detect_c2(cl.load_m1()))
    print("u1007b", len(ev), "gate", round(float(ev.eur_fail_close.mean()), 3))
    probe = cl.probe_lookahead(detect_c2, ev, lookback="10D")
    res = cl.gate_test(ev, "eur_fail_close", mask_available_at="decision_time", max_hold=MAX_HOLD, claim="+")
    rules = [
        "gold 1h bars from certified M1; XAU_EUR H1 (OANDA mid) read at the same labels; rows dropped unless XAU_EUR has both C1 and C2 hours",
        "gold C2 = sweeps the prior 1h bar's low (high), closes at/above (at/below) it, closes bullish (bearish)",
        "keep only C2s where XAU_EUR also swept its own prior-hour low (high) on that hour",
        "gate = XAU_EUR did not close back above its C1 low (below its C1 high) -> gold is the stronger (weaker) asset; complement = XAU_EUR closed back too",
        "trade gold: next M1 open after the C2 close, reversal direction, stop at the C2 extreme, 2R, 10h wall clock; claim '+'",
    ]
    params = {"tf": "1h", "correlate": "XAU_EUR H1", "c2": "sweep prior bar extreme, close back inside, reversal-coloured close",
              "discriminator": "correlate closes back beyond its C1 extreme or not", "stop": "C2 extreme",
              "rr": RR, "max_hold": MAX_HOLD}
    src = dict(SRC_COMMON)
    src.update({
        "tf": "declared-before-run: 1h, the finest timeframe the correlate supports; the source states no timeframe",
        "c2": "corpus: yH4eYwUgdTY 'we sweep out the previous low and we close a nice and bullish'; same C2 rule as sibling gold-correlated-assets 1h",
        "discriminator": "corpus: yH4eYwUgdTY 'we can't close bullish or back above candle one's low'",
        "stop": "declared-before-run: C2 extreme (protected low of the C2), as sibling gold-correlated-assets C2 book",
    })
    notes = (f"{len(ev)} gold 1h C2s where XAU_EUR also swept; XAU_EUR failed to close back on "
             f"{ev.eur_fail_close.mean():.1%}. Both-swept closure case only (one-sided = SMT, tested elsewhere).")
    return res, rules, params, src, probe, notes


RUN = {"u1007a": run_prio, "u1007b": run_c2}

if __name__ == "__main__":
    for rd in (sys.argv[1:] or list(RUN)):
        res, rules, params, src, probe, notes = RUN[rd]()
        print(" probe", probe.get("passed"))
        for kk in ("n", "n_gated", "n_complement", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                   "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "halves"):
            print(" ", kk, res.get(kk))
        p = cl.write_result(CID, rd, res, operationalization={"rules": rules, "params": params},
                            params_source=src, script=__file__, probe=probe, notes=notes)
        print("wrote", p)
