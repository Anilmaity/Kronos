"""cross-asset-reversal-confirmation -- update 2026-10-07 (TTrades live_01/08/09 drafts).

New claims vs the library entry (already tested as readings a/b):
  live_01: confirmation = a 5-minute closure through on the weakest asset.
  live_08: the tell is whichever correlated asset is closest to the relevant level.
  live_09: preferred reversal = ANOTHER sweep of the weakest's low (fresh SMT), not a run all
           the way down to the deeper / distant low ("too much time and range").
Only live_09 is testable here: silver (the only correlate with history) exists at H1 since
2010 but only at M15 since 2024-12 (no 5m; and <2 years fails the H1/H2 split), and a
proximity rule needs >=3 correlated assets (we have a pair).

Reading u1007a (gate_test, claim '+'): same baseline as reading a (phase-3 1h gold CISD,
kept when gold long & gold stronger / gold short & gold weaker vs silver, % from 18:00 NY
open). Sample restricted to events where silver DID reverse in (t-3h, t]. Gate = the
reversal was the shallow "another sweep" form: a silver 1h bar took the most recent
confirmed 2/2 swing low, closed back above it, and stayed above the prior 20-bar low.
Complement = the deep form: a silver bar took the prior 20-bar low and closed back above it.
(Mirror for gold shorts: silver, the stronger, sweeps its swing high / 20-bar high.)
"""
from __future__ import annotations

import importlib.util
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a")
from _common import PHASE3, cl, np, pd, summary  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "carc_prior", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/"
                  "structure_own_03a/cross-asset-reversal-confirmation.py")
_prior = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_prior)

CID = "cross-asset-reversal-confirmation"
H1 = pd.Timedelta(hours=1)
LB, WIN, SW, HOLD = 20, 3, 2, "10h"


def _last_swing(vals, is_low):
    """Value of the most recent 2/2 fractal confirmed by the close of the PREVIOUS bar."""
    s = pd.Series(vals)
    nb = [s.shift(k) for k in (1, 2, -1, -2)]
    if is_low:
        fr = (s < nb[0]) & (s < nb[1]) & (s < nb[2]) & (s < nb[3])
    else:
        fr = (s > nb[0]) & (s > nb[1]) & (s > nb[2]) & (s > nb[3])
    # fractal at i is known at close of i+SW -> place at i+SW, then usable from bar i+SW+1
    lvl = s.where(fr).shift(SW).ffill().shift(1)
    return lvl.to_numpy(float)


def detect(m1):
    g = cl.build_bars(m1, "1h")
    cutoff = m1.index[-1] + pd.Timedelta(minutes=1)
    s = _prior._xag()
    s = s[(s.index >= g.index[0] - 30 * H1) & (s.index + H1 <= cutoff)].copy()
    s["close_time"] = s.index + H1
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "shallow"]
    ev = _prior._cisd(g)
    if ev.empty or s.empty:
        return pd.DataFrame(columns=cols)
    t = pd.DatetimeIndex(g.loc[ev["confirm_time"], "close_time"])
    d = np.where(ev["direction"] == "bullish", 1, -1)
    tn = cl.data.utc_ns(t)

    def rs(frame):  # identical to reading a's strength rule
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

    sh, sl, sc = (s[k].to_numpy(float) for k in ("high", "low", "close"))
    ph = pd.Series(sh).rolling(LB).max().shift(1).to_numpy()
    pl = pd.Series(sl).rolling(LB).min().shift(1).to_numpy()
    swl, swh = _last_swing(sl, True), _last_swing(sh, False)
    deep_lo = (sl < pl) & (sc > pl)
    deep_hi = (sh > ph) & (sc < ph)
    shal_lo = (sl < swl) & (sc > swl) & (sl >= pl)
    shal_hi = (sh > swh) & (sc < swh) & (sh <= ph)
    sct = cl.data.utc_ns(pd.DatetimeIndex(s["close_time"]))
    hi_i = np.searchsorted(sct, tn, side="right")
    lo_i = np.searchsorted(sct, tn - np.int64(WIN * 3600 * 10**9), side="right")

    def cnt(x):
        c = np.r_[0, np.cumsum(x)]
        return c[hi_i] - c[lo_i]
    deep = np.where(d > 0, cnt(deep_lo), cnt(deep_hi)) > 0
    shal = np.where(d > 0, cnt(shal_lo), cnt(shal_hi)) > 0
    keep &= deep | shal
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
                        "shallow": shal & ~deep})[keep]
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    ev = cl.cache_frame("carc_u1007a_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["shallow"].mean(), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "shallow", mask_available_at="decision_time", max_hold=HOLD)
    print(summary(res))
    rules = [
        "pair: gold (traded) vs silver XAG_USD H1 (OANDA), silver bars closed by the decision only",
        "strength = % change from the 18:00-NY trading-day open to the latest closed 1h bar",
        "baseline: phase-3 bare 1h gold CISD (series_open, swing 2/2, max_wait 3), stop protected "
        "swing, 2R, 10h; kept when gold long & gold stronger, or gold short & gold weaker",
        f"sample: silver reversed in (t-{WIN}h, t]: shallow or deep form (below)",
        f"shallow ('another sweep'): silver 1h bar took the latest confirmed 2/2 swing low, "
        f"closed back above it, low stayed >= prior {LB}-bar low (mirror highs for shorts)",
        f"deep ('all the way to the deeper low'): silver bar took the prior {LB}-bar low and "
        "closed back above it; if both forms occur in the window the event counts as deep",
        "gate = shallow; complement = deep; claim '+' (shallow form better)",
        "untested parts: 5m closure (no silver 5m data), proximity-tell (needs >=3 correlates), "
        "fresh-SMT condition not separately required"]
    params = {"tf": "1h", "level_rule": "series_open", "swing": "2/2", "max_wait": 3, "rr": 2.0,
              "max_hold": HOLD, "strength": "pct change from 18:00 NY open",
              "correlate": "XAG_USD H1", "deep_lookback": LB, "swing_fractal": "2/2",
              "window_h": WIN}
    src = {"tf": "corpus: cross-asset-reversal-confirmation.yaml timeframes htf 1H",
           "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "strength": "method_spec: §2.6 'Separation — distance travelled from the shared reference'",
           "correlate": "method_spec: §2.6 SMT/PSP with the correlated asset (silver)",
           "deep_lookback": "phase3: lookback 20 knob; corpus Hlwq1dRjBZo 'not a run all the way "
                            "down to the deeper low' -> deeper low = prior 20-bar extreme (declared-before-run)",
           "swing_fractal": "corpus: Hlwq1dRjBZo 'I like another sweep personally' -> sweep of the "
                            "latest swing low; swing def = phase3 2/2 (declared-before-run)",
           "window_h": "phase3/prior reading a: 'the next couple of candles' -> 3h (reused, not refit)"}
    p = cl.write_result(CID, "u1007a", res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="Tests only live_09's second-sweep vs deep-run preference. live_01's "
                              "5m closure and live_08's proximity tell are not testable with a "
                              "gold/silver H1 pair.")
    print("wrote", p)


if __name__ == "__main__":
    main()
