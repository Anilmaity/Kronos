"""smt-swing-point-substitute (TTrades own voice, contested) — batch structure_own_02a.

Claim: where the model needs a sweep to validate a swing point / protected swing and THIS
asset did not sweep but the correlated asset did, treat the level as swept: close through
the opposing candles that made the failure swing and the unswept extreme is protected
("SMT waives the sweep, not the confirmation", method_spec §2.6/§3.8). Correlate =
XAG_USD (silver), the method's sanctioned gold correlate; bars are inner-joined on shared
1h labels.

Readings (the two distinct uses in the yaml variants):
  a  intraday protected-swing substitution (1H), trade_test:
       level = gold's most recent confirmed 2/2 swing low at bar p (silver's level = its
       own low on bar p). Within 20 bars a gold failure swing forms at pos: gold's lowest
       low since p, below its 2 prior lows, but ABOVE the gold level (no gold bar in
       (p, closure] trades below it), while silver trades below its level somewhere in
       [pos-2, closure]. Closure = first gold close above the OPEN of the first candle of
       the down-close series into pos, within 10 bars, no new gold extreme first.
       Long at the next M1 open, stop = the unswept gold low, 2R, 10h exit. Mirror at highs.
  b  daily C2 substitution, gate_test: baseline = trading days (18:00 NY) that take the
       previous day's low, close back above it and do not take its high (mirror), traded
       next day toward the reversal (stop = day extreme, target = previous day's opposite
       extreme, 1380 trading minutes). Gate = SMT: silver did NOT take its own previous-day
       low that day (divergence at the swept level). claim '+': SMT-licensed C2 days beat
       C2 days without it. Days lacking silver data are dropped.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a")
from _common import _xag_raw, cl, np, pair_1h, pd, summary  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

CID = "smt-swing-point-substitute"
LB, MAX_K, RR, HOLD = 20, 10, 2.0, "10h"


def detect_a(m1):
    P = pair_1h(m1)
    n = len(P)
    gh, gl, go, gc = (P[k].to_numpy(float) for k in ("high", "low", "open", "close"))
    sh, sl = P["s_high"].to_numpy(float), P["s_low"].to_numpy(float)
    sw = swing_points(P[["high", "low"]], 2, 2)
    rows = []
    for bull in (True, False):
        x = gl if bull else -gh
        sx = sl if bull else -sh
        oo, cc = (go, gc) if bull else (-go, -gc)
        opp = cc < oo
        piv = np.flatnonzero(sw["swing_low" if bull else "swing_high"].to_numpy())
        for pos in range(3, n - 1):
            # most recent gold swing at p confirmed before pos, within LB bars
            k = np.searchsorted(piv, pos - 2, side="right") - 1
            if k < 0:
                continue
            p = piv[k]
            if p + 2 > pos - 1 or pos - p > LB:
                continue
            lvl_g, lvl_s = x[p], sx[p]
            xp = x[pos]
            if not (x[pos - 2:pos] > xp).all():
                continue
            if not (x[p + 1:pos] > xp).all() or not xp > lvl_g:
                continue
            end = pos
            while end > 0 and not opp[end]:
                end -= 1
                if pos - end > 2:
                    end = -1
                    break
            if end < 0 or not opp[end]:
                continue
            start = end
            while start > 0 and opp[start - 1] and (end - start + 1) < 10:
                start -= 1
            lvl = oo[start]
            for j in range(pos + 1, min(n, pos + MAX_K + 1)):
                if x[j] < xp:
                    break
                if cc[j] > lvl:
                    if (sx[max(pos - 2, p + 1):j + 1] < lvl_s).any():
                        rows.append((j, 1 if bull else -1, xp if bull else -xp))
                    break
    ev = pd.DataFrame(rows, columns=["j", "dir", "extreme"])
    ev = ev.drop_duplicates(["j", "dir"]).sort_values(["j", "dir"]).reset_index(drop=True)
    ct = pd.DatetimeIndex(P["close_time"].to_numpy()[ev["j"].to_numpy()])
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": ev["dir"].to_numpy().astype(int),
                         "stop_px": ev["extreme"].to_numpy(), "rr": RR})


def detect_b(m1):
    b = cl.build_bars(m1, "1D")
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    nm = b["n_m1"].to_numpy(float)
    good = nm >= 0.5 * np.median(nm)
    ph, pl = np.roll(h, 1), np.roll(l, 1)
    bull = (l < pl) & (c > pl) & (h <= ph)
    bear = (h > ph) & (c < ph) & (l >= pl)
    ok = good & np.roll(good, 1)
    ok[0] = False
    sel = np.flatnonzero(ok & (bull | bear))
    # silver per gold trading day, cut at the input's last minute
    cutoff = m1.index[-1] + pd.Timedelta(minutes=1)
    s = _xag_raw()
    s = s[(s.index + pd.Timedelta(hours=1) <= cutoff) & (s.index >= m1.index[0].floor("h"))]
    td = cl.trading_day(s.index)
    s_hi, s_lo = s["high"].groupby(td).max(), s["low"].groupby(td).min()
    gtd = cl.trading_day(b.index)
    rows = []
    for i in sel:
        d, dprev = gtd[i], gtd[i - 1]
        if d not in s_hi.index or dprev not in s_hi.index:
            continue
        is_bull = bool(bull[i])
        smt = (s_lo[d] >= s_lo[dprev]) if is_bull else (s_hi[d] <= s_hi[dprev])
        rows.append((i, 1 if is_bull else -1, l[i] if is_bull else h[i],
                     ph[i] if is_bull else pl[i], bool(smt)))
    ev = pd.DataFrame(rows, columns=["i", "dir", "stop", "target", "smt"])
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[ev["i"].to_numpy()])
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": ev["dir"].to_numpy().astype(int),
                         "stop_px": ev["stop"].to_numpy(), "target_px": ev["target"].to_numpy(),
                         "smt": ev["smt"].to_numpy(bool)})


def main():
    corr_src = "method_spec: §2.6 SMT = one shared level, one asset trades beyond, the other does not; silver = sanctioned gold correlate (fetch_correlated.py)"
    # reading a
    ev = cl.cache_frame(f"smtsub_a_{LB}_{MAX_K}", lambda: detect_a(cl.load_m1()))
    probe = cl.probe_lookahead(detect_a, ev, lookback="30D")
    res = cl.trade_test(ev, max_hold=HOLD)
    print("reading a\n" + summary(res))
    rules = ["gold 1h and XAG_USD H1 inner-joined on shared bar labels",
             "level: gold's most recent confirmed 2/2 swing low at bar p; silver's level = its "
             "low on bar p (mirror at highs)",
             f"failure swing at pos (<= {LB} bars after p): gold's lowest low since p, below "
             "its 2 prior lows, ABOVE the gold level; silver trades below its level within "
             "[pos-2, closure]",
             f"closure: first gold close above the open of the first candle of the down-close "
             f"series into pos, within {MAX_K} bars, no new gold extreme first",
             f"long at next M1 open, stop = the unswept gold low, {RR}R, exit after {HOLD}"]
    p = cl.write_result(CID, "a", res, operationalization={"rules": rules, "params": {
        "tf": "1h", "swing": "2/2", "lookback": LB, "max_k": MAX_K, "rr": RR, "max_hold": HOLD,
        "correlate": "XAG_USD H1"}},
        params_source={"tf": "corpus yaml timeframes ltf 1H", "swing": "phase3: fractal 2/2",
                       "lookback": "phase3: SMT lookback 20 knob",
                       "max_k": "declared-before-run: closure within 10 bars of the failure swing",
                       "rr": "phase3: 2R", "max_hold": "phase3: 1h book 10h exit",
                       "correlate": corr_src},
        script=__file__, probe=probe,
        notes="Trade of the substituted setups alone vs a matched random entry. The 'failure "
              "swing near the level' has no tolerance in the corpus; any unswept low after "
              "the level within 20 bars qualifies.")
    print("  wrote", p)
    # reading b
    ev = cl.cache_frame("smtsub_b_1d", lambda: detect_b(cl.load_m1()))
    probe = cl.probe_lookahead(detect_b, ev, lookback="60D")
    res = cl.gate_test(ev, "smt", mask_available_at="decision_time", max_hold="1380min",
                       hold_basis="bars")
    print("reading b\n" + summary(res))
    rules = ["trading-day bars (18:00 NY), stub days (< 50% median M1 count) skipped",
             "C2 day: takes the previous day's low, closes back above it, does not take its "
             "high (mirror) -> trade next day toward the reversal at the next M1 open, stop = "
             "the day's extreme, target = previous day's opposite extreme, 1380 trading minutes",
             "gate SMT: silver's low that trading day stayed at/above silver's previous-day "
             "low (mirror for highs); days without silver data dropped"]
    p = cl.write_result(CID, "b", res, operationalization={"rules": rules, "params": {
        "tf": "1D", "max_hold": "1380min", "hold_basis": "bars", "min_coverage": 0.5,
        "correlate": "XAG_USD H1 aggregated to gold trading days"}},
        params_source={"tf": "corpus yaml variant: 'a day that takes out the previous day's low and closes above it, with an SMT present, may be treated as a candle 2 closure'",
                       "max_hold": "declared-before-run: one trading day (next-day model)",
                       "hold_basis": "declared-before-run: trading time across the halt",
                       "min_coverage": "declared-before-run: README trap 6 stub sessions",
                       "correlate": corr_src},
        script=__file__, probe=probe,
        notes="SMT is judged on the full C2 day (known at its close = the decision).")
    print("  wrote", p)


if __name__ == "__main__":
    main()
