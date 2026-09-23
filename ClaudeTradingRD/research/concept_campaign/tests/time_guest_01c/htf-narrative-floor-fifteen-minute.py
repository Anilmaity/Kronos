"""htf-narrative-floor-fifteen-minute (guest: AM Trades) -> gate_test.

Claim ('+'): narrative built on the hourly (the "sweet spot", hourly-to-daily) is
better than narrative built on the 15-minute (the floor) — the concept's measurable
"expectancy of setups whose narrative was formed on the 15-minute vs on the hourly/daily".
Declared before the run:
  * Narrative = the method spec §2.3 previous-candle engine applied to the LAST COMPLETED
    candle of the narrative timeframe: continuation closure (takes the prior high/low and
    closes outside) -> same direction; reversal closure (takes one side, closes back
    inside) -> opposite direction; both sides taken or inside bar -> no narrative (0).
  * Execution book (below the 15m = execution only): phase-3 bare 5m CISD, 2R, stop at
    the protected swing, 50 min hold.
  * Only events where the 1H narrative and the 15m narrative are both set and DISAGREE
    are kept — these are the trades where the choice of narrative timeframe decides the
    trade. Gated = the 5m entry agrees with the 1H narrative (and so fights the 15m one);
    complement = agrees with the 15m narrative.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_guest_01c")
from _common import PHASE3, cisd_book, cl, last_closed_idx, np, pd, summary  # noqa: E402

CID = "htf-narrative-floor-fifteen-minute"
TF, HOLD = "5min", "50min"
HTF, FLOOR = "1h", "15min"


def implied_bias(b: pd.DataFrame) -> np.ndarray:
    """§2.3 previous-candle engine: bias implied by each bar for the NEXT bar."""
    h, l, c = (b[k].to_numpy() for k in ("high", "low", "close"))
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    th, tl = h > ph, l < pl
    imp = np.zeros(len(b), int)
    oh, ol = th & ~tl, tl & ~th
    imp[oh & (c > ph)] = 1
    imp[oh & ~(c > ph)] = -1
    imp[ol & (c < pl)] = -1
    imp[ol & ~(c < pl)] = 1
    return imp


def narrative(m1, tf, times):
    b = cl.build_bars(m1, tf)
    k = last_closed_idx(b, times)
    imp = implied_bias(b)
    return np.where(k >= 1, imp[np.clip(k, 0, None)], 0)


def detect(m1):
    ev = cisd_book(m1, TF)
    if ev.empty:
        return ev.assign(htf_aligned=pd.Series(dtype=bool))
    nh = narrative(m1, HTF, ev["decision_time"])
    nf = narrative(m1, FLOOR, ev["decision_time"])
    keep = (nh != 0) & (nf != 0) & (nh != nf)
    ev["htf_aligned"] = ev["direction"].to_numpy() == nh
    return ev[keep].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("tg01c_cisd5m_narr_1h_vs_15m", lambda: detect(cl.load_m1()))
    print(len(ev), ev["htf_aligned"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "htf_aligned", mask_available_at="decision_time", max_hold=HOLD)
    print(summary(res))
    op = {"rules": [
        "narrative = §2.3 previous-candle engine on the last completed candle of the TF "
        "(continuation closure -> same side, reversal closure -> opposite, both/inside -> none)",
        "execution: 5m bare CISD (series_open, swing 2/2, max_wait 3), next M1 open, stop "
        "protected swing, 2R, 50 min",
        "kept: 1H and 15m narratives both set and opposite; gated = entry agrees with 1H "
        "narrative, complement = entry agrees with 15m narrative"],
        "params": {"htf": HTF, "floor_tf": FLOOR, "tf": TF, "inside_bar": "no narrative",
                   "level_rule": "series_open", "swing": "2/2", "max_wait": 3, "rr": 2.0,
                   "max_hold": HOLD, "grid4h": "n/a"}}
    src = {"htf": "corpus: CrUfTskOveo 'i think hourly to daily is your sweet spot for sure even for day trades'",
           "floor_tf": "corpus: CrUfTskOveo 'the absolute lowest you can go for a hard time from narrative'",
           "tf": "declared-before-run: 5m execution (below the 15m floor = execution only); phase-3 bare CISD",
           "inside_bar": "declared-before-run: method_spec §2.3 inside bar = no information (no trend default)",
           "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "grid4h": "declared-before-run: not used"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Narrative operationalised with the channel's previous-candle "
                              "engine (the guest gives no narrative algorithm). Daily narrative "
                              "not separately tested; 1H stands for the hourly-to-daily band.")
    print(p)
