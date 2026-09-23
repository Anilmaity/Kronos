"""strat-scalping-hour-two-filter (guest: Alex's Options, TheSTRAT) -> gate_test.

Claim ('+'): sub-15m scalps taken while the hourly candle is a 2 in the trade's
direction beat those taken while the hour is a 1 (inside) — the concept's own
measurable "win rate of sub-15m signals while the hour is a 2 vs a 1".
Declared before the run:
  * Baseline scalp book: phase-3 bare 5m CISD (5m is in the concept's ltf list), 2R,
    stop at the protected swing, 50 min hold.
  * STRAT hour typing vs the PREVIOUS 1h candle (UTC/NY whole hours): 1 = inside
    (high <= prev high and low >= prev low); 2u = high > prev high, low >= prev low;
    2d mirrored; 3 = both sides taken.
  * Baseline restricted to events whose hour is a 2 IN the trade's direction (gated) or
    a 1 (complement). Hours that are a 3, or a 2 against the trade ("in conflict"), are
    dropped: the concept compares 2 vs 1.
  * reading a (live, "his usage implies live"): the CURRENT hour's running high/low
    from M1 bars closed by the decision time.
    reading b (confirmed at close): the last COMPLETED 1h candle.
  * The volatility precondition (gappers / earnings names) has no gold analogue and is
    not applied; the HTF-continuity precondition is tested under strat-timeframe-continuity.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_guest_01c")
from _common import PHASE3, cisd_book, cl, last_closed_idx, np, pd, summary  # noqa: E402

CID = "strat-scalping-hour-two-filter"
TF, HOLD = "5min", "50min"


def hour_types(m1, times, live: bool):
    """(up, dn, ok) for the hour judged at `times`."""
    b = cl.build_bars(m1, "1h")
    H, L = b["high"].to_numpy(), b["low"].to_numpy()
    t = pd.DatetimeIndex(times)
    n = len(t)
    if live:
        starts = cl.data.utc_ns(pd.DatetimeIndex(b.index))
        mi = cl.data.utc_ns(pd.DatetimeIndex(m1.index))
        pos = np.searchsorted(starts, mi, side="right") - 1
        g = pd.Series(pos)
        cmax = pd.Series(m1["high"].to_numpy()).groupby(g).cummax().to_numpy()
        cmin = pd.Series(m1["low"].to_numpy()).groupby(g).cummin().to_numpy()
        closes = mi + np.int64(60_000_000_000)
        i = np.searchsorted(closes, cl.data.utc_ns(t), side="right") - 1
        ok = i >= 0
        ii = np.clip(i, 0, None)
        j = pos[ii]
        ok &= j >= 1
        jj = np.clip(j, 1, None)
        rh, rl = cmax[ii], cmin[ii]
        ph, pl = H[jj - 1], L[jj - 1]
    else:
        k = last_closed_idx(b, t)
        ok = k >= 1
        kk = np.clip(k, 1, None)
        rh, rl = H[kk], L[kk]
        ph, pl = H[kk - 1], L[kk - 1]
    up = ok & (rh > ph)
    dn = ok & (rl < pl)
    return up, dn, ok


def make_detect(live: bool):
    def detect(m1):
        ev = cisd_book(m1, TF)
        if ev.empty:
            return ev.assign(hour_two=pd.Series(dtype=bool))
        up, dn, ok = hour_types(m1, ev["decision_time"], live)
        d = ev["direction"].to_numpy()
        two_with = ((d == 1) & up & ~dn) | ((d == -1) & dn & ~up)
        inside = ok & ~up & ~dn
        ev["hour_two"] = two_with
        ev = ev[two_with | inside].reset_index(drop=True)
        return ev
    return detect


if __name__ == "__main__":
    for reading, live in (("a", True), ("b", False)):
        detect = make_detect(live)
        ev = cl.cache_frame(f"tg01c_cisd5m_hour2_{'live' if live else 'closed'}",
                            lambda: detect(cl.load_m1()))
        print(reading, len(ev), ev["hour_two"].mean())
        probe = cl.probe_lookahead(detect, ev, lookback="10D")
        print("probe", probe.get("passed"))
        res = cl.gate_test(ev, "hour_two", mask_available_at="decision_time", max_hold=HOLD)
        print(summary(res))
        hour_rule = ("CURRENT 1h candle, running high/low from M1 closed by the decision"
                     if live else "last COMPLETED 1h candle")
        op = {"rules": [
            "baseline: 5m bare CISD (series_open, swing 2/2, max_wait 3), decide at the "
            "confirming bar close, enter next M1 open, stop protected swing, 2R, 50 min",
            f"hour typed vs the previous 1h candle using the {hour_rule}: 1 inside, 2u, 2d, 3",
            "kept: hour is a 2 in the trade's direction (gated) or a 1 (complement); 3s and "
            "conflicting 2s dropped"],
            "params": {"tf": TF, "htf": "1h", "hour_read": "live" if live else "closed",
                       "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
                       "rr": 2.0, "max_hold": HOLD, "grid4h": "n/a"}}
        src = {"tf": "declared-before-run: 5m (concept ltf list 15/5/3/1m); phase-3 bare CISD as scalp book",
               "htf": "corpus: 1XWyy6Q-_8Q 'anytime this hour is two that's when you can start scalping'",
               "hour_read": ("declared-before-run: live read (concept ambiguity: 'his usage implies live')"
                             if live else "declared-before-run: confirmed-at-close alternative reading"),
               "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
               "max_hold": "phase3: 10 entry-TF bars (§1.13)",
               "grid4h": "declared-before-run: not used"}
        p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe,
                            notes="Tests the hour-2 gate only; the gapper/earnings volatility "
                                  "precondition has no XAUUSD analogue.")
        print(p)
