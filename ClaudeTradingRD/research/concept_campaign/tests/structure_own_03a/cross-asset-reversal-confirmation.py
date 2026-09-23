"""cross-asset-reversal-confirmation (TTrades own voice, contested) — batch structure_own_03a.

"The strongest asset must reverse for the weakest to expand": a short on the weaker of
two correlated assets is only actionable if the stronger one reverses off its high at
the same time; a long on the stronger needs the weaker to sweep a low and reverse.

Pair: gold (traded) and silver (the correlate; OANDA XAG_USD H1). Strength = separation
from the shared reference (method_spec §2.6 tool 2): % change from the 18:00-NY daily
open to the latest closed 1h bar; larger = stronger.
Baseline book: phase-3 bare 1h gold CISD (series_open, swing 2/2, max_wait 3), stop at
the protected swing, 2R, 10h — kept only when the strength ordering matches the concept
(gold short when gold is the weaker of the pair, gold long when gold is the stronger).
Gate (claim '+'): the paired asset (silver) has reversed:
  reading a (sweep-and-return, "reverse off its high and trade back into its range",
            "a reversal in the required asset needs a sweep"): a silver 1h bar closed in
            (t-3h, t] took out the prior 20 silver bars' high and closed back below it
            (for a gold short; mirror: took the 20-bar low and closed back above).
  reading b (closure reversal, the entry-model reversal): silver printed its own 1h CISD
            (phase-3 definition) in the trade direction, confirmed in (t-4h, t] ("waits
            until the next 4-hour candle open").
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a")
from _common import PHASE3, cl, np, pd, summary  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

CID = "cross-asset-reversal-confirmation"
XAG = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xag_h1_full.parquet")
H1 = pd.Timedelta(hours=1)
SWEEP_LB, WIN_A, WIN_B, HOLD = 20, 3, 4, "10h"
_X = {}


def _xag():
    if "x" not in _X:
        x = pd.read_parquet(XAG)
        x.index = pd.to_datetime(x.index, utc=True)
        _X["x"] = x[["open", "high", "low", "close"]].astype("float64").sort_index()
    return _X["x"]


def _cisd(b):
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    return ev


def detect(m1):
    g = cl.build_bars(m1, "1h")
    cutoff = m1.index[-1] + pd.Timedelta(minutes=1)
    s = _xag()
    s = s[(s.index >= g.index[0] - 30 * H1) & (s.index + H1 <= cutoff)].copy()
    s["close_time"] = s.index + H1
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "gate_a", "gate_b"]
    ev = _cisd(g)
    if ev.empty or s.empty:
        return pd.DataFrame(columns=cols)
    t = pd.DatetimeIndex(g.loc[ev["confirm_time"], "close_time"])
    d = np.where(ev["direction"] == "bullish", 1, -1)
    tn = cl.data.utc_ns(t)
    # --- strength: % change from the trading-day open (18:00 NY) to latest closed bar
    def rs(frame):
        ct = cl.data.utc_ns(pd.DatetimeIndex(frame["close_time"]))
        td = cl.trading_day(pd.DatetimeIndex(frame.index))
        day_open = pd.Series(frame["open"].to_numpy(), index=td).groupby(level=0).first()
        k = np.searchsorted(ct, tn, side="right") - 1
        ok = k >= 0
        kk = np.clip(k, 0, None)
        same = ok & np.asarray(td[kk] == cl.trading_day(t))
        op = day_open.reindex(td[kk]).to_numpy()
        return np.where(same, frame["close"].to_numpy()[kk] / op - 1.0, np.nan)
    rg, rsil = rs(g), rs(s)
    keep = np.isfinite(rg) & np.isfinite(rsil) & (((d < 0) & (rg < rsil)) | ((d > 0) & (rg > rsil)))
    # --- reading a: silver sweep of its 20-bar extreme and close back inside
    sh, sl, sc = (s[k].to_numpy(float) for k in ("high", "low", "close"))
    ph = pd.Series(sh).rolling(SWEEP_LB).max().shift(1).to_numpy()
    pl = pd.Series(sl).rolling(SWEEP_LB).min().shift(1).to_numpy()
    sw_hi = (sh > ph) & (sc < ph)          # reversal off a high (bearish)
    sw_lo = (sl < pl) & (sc > pl)          # reversal off a low (bullish)
    sct = cl.data.utc_ns(pd.DatetimeIndex(s["close_time"]))
    cum_hi = np.r_[0, np.cumsum(sw_hi)]
    cum_lo = np.r_[0, np.cumsum(sw_lo)]
    hi_i = np.searchsorted(sct, tn, side="right")
    lo_i = np.searchsorted(sct, tn - np.int64(WIN_A * 3600 * 10**9), side="right")
    n_hi = cum_hi[hi_i] - cum_hi[lo_i]
    n_lo = cum_lo[hi_i] - cum_lo[lo_i]
    gate_a = np.where(d < 0, n_hi > 0, n_lo > 0)
    # --- reading b: silver 1h CISD in the trade direction confirmed in (t-4h, t]
    sev = _cisd(s)
    gate_b = np.zeros(len(t), bool)
    if len(sev):
        sconf = cl.data.utc_ns(pd.DatetimeIndex(s.loc[sev["confirm_time"], "close_time"]))
        sdir = np.where(sev["direction"] == "bullish", 1, -1)
        for dd in (1, -1):
            ss = np.sort(sconf[sdir == dd])
            m = d == dd
            a = np.searchsorted(ss, tn[m] - np.int64(WIN_B * 3600 * 10**9), side="right")
            bnd = np.searchsorted(ss, tn[m], side="right")
            gate_b[m] = (bnd - a) > 0
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
                        "gate_a": gate_a, "gate_b": gate_b})[keep]
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    ev = cl.cache_frame("carc_1h_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev[["gate_a", "gate_b"]].mean().to_dict(), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    base = ["pair: gold (traded) vs silver XAG_USD H1 (OANDA), silver bars closed by the "
            "decision only",
            "strength = % change from the 18:00-NY trading-day open to the latest closed 1h "
            "bar; larger = stronger",
            "baseline: phase-3 bare 1h gold CISD (series_open, swing 2/2, max_wait 3), stop "
            "protected swing, 2R, 10h; kept when gold short & gold weaker, or gold long & "
            "gold stronger"]
    params = {"tf": "1h", "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
              "rr": 2.0, "max_hold": HOLD, "strength": "pct change from 18:00 NY open",
              "correlate": "XAG_USD H1"}
    src = {"tf": "corpus: cross-asset-reversal-confirmation.yaml timeframes htf 1H",
           "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "strength": "method_spec: §2.6 'Separation — distance travelled from the shared "
                       "reference; further = stronger'",
           "correlate": "method_spec: §2.6 SMT/PSP with the correlated asset (silver is "
                        "gold's correlate in this workspace)"}
    for reading, col, rule, xp, xs in (
            ("a", "gate_a", f"gate a: a silver 1h bar closed in (t-{WIN_A}h, t] swept the prior "
                            f"{SWEEP_LB} bars' high and closed back below it (gold short); "
                            "mirror for longs",
             {"sweep_lookback": SWEEP_LB, "window_h": WIN_A},
             {"sweep_lookback": "phase3: lookback 20 knob (backtest_conjunction)",
              "window_h": "corpus: yaml ambiguity 'the next couple of candles' -> the "
                          "decision bar and the two before it (declared-before-run)"}),
            ("b", "gate_b", f"gate b: silver 1h CISD (phase-3 def) in the trade direction "
                            f"confirmed in (t-{WIN_B}h, t]",
             {"window_h": WIN_B},
             {"window_h": "corpus: yaml ambiguity 'in practice he waits until the next "
                          "4-hour candle open and then re-reads'"})):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD)
        print(f"reading {reading}\n" + summary(res))
        p = cl.write_result(CID, reading, res,
                            operationalization={"rules": base + [rule],
                                                "params": {**params, **xp}},
                            params_source={**src, **xs}, script=__file__, probe=probe,
                            notes="Corpus examples are index/FX triads; gold-silver is the "
                                  "only correlate pair with history here, so strongest/weakest "
                                  "is a two-asset ranking.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
