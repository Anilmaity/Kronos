"""risk_own_01b / hedge-not-double-exposure (specified) — gate_test.

Swing positions: the 1D rung-0 CISD book (daily-chart swing setups), entered at the
next M1 open after the daily confirming close, stop at the protected swing, 2R
target, time exit after SWING_HOLD; resolved on M1 (stop first on ties).
Intraday book: the 15m rung-0 CISD book, restricted to signals that fire WHILE a
swing is open (the concept's precondition). If several swings are open, the most
recent one sets the swing direction.
Kept (what the rule trades): intraday signals AGAINST the open swing (the hedge);
complement (what the rule skips): signals in the SAME direction ("doubles exposure").
Claim +: the rule's selection is not an expectancy cost — kept beats skipped.
(The exposure-halving itself is arithmetic and needs no test; this measures what
the rule costs or earns per trade.)
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
from _common import *   # noqa

TF = "15min"
SWING_HOLD = pd.Timedelta(days=14)     # ~10 trading days


def swing_book(m1):
    sw, _, _ = cisd_book(m1, "1D")
    if sw.empty:
        return pd.DataFrame(columns=["dec", "exit", "dir"])
    tn, o, h, l_, c = m1_arrays(m1)
    dec = cl.data.utc_ns(pd.DatetimeIndex(sw["decision_time"])).astype(np.int64)
    rows = []
    for dt, s, st in zip(dec, sw["direction"].to_numpy(), sw["stop_px"].to_numpy()):
        i0 = np.searchsorted(tn, dt, side="left")
        if i0 >= len(tn):
            continue
        entry = o[i0]
        risk = s * (entry - st)
        if not risk > 0:
            continue
        tgt = entry + s * 2.0 * risk
        end_ns = dt + SWING_HOLD.value
        i1 = np.searchsorted(tn, end_ns, side="left")
        hh, ll = h[i0:i1], l_[i0:i1]
        if s > 0:
            hit = (ll <= st) | (hh >= tgt)
        else:
            hit = (hh >= st) | (ll <= tgt)
        k = np.flatnonzero(hit)
        ex = tn[i0 + k[0]] + 60_000_000_000 if len(k) else end_ns   # close of the exit bar
        rows.append((dt, ex, s))
    return pd.DataFrame(rows, columns=["dec", "exit", "dir"])


def detect(m1):
    ev, _, _ = cisd_book(m1, TF)
    ev = ev[["decision_time", "available_at", "direction", "stop_px", "rr"]].copy()
    sb = swing_book(m1)
    t = cl.data.utc_ns(pd.DatetimeIndex(ev["decision_time"])).astype(np.int64)
    sdir = np.zeros(len(ev), int)
    sdec = np.full(len(ev), np.iinfo(np.int64).min)
    for dt, ex, s in zip(sb["dec"].to_numpy(), sb["exit"].to_numpy(), sb["dir"].to_numpy()):
        # open at t iff swing decided at/before t and not exited by t (exit = close of
        # the bar that hit, or the time exit) — both known from data <= t
        m = (t >= dt) & (t < ex) & (dt >= sdec)
        sdir[m] = s
        sdec[m] = dt
    keep = sdir != 0
    ev = ev[keep].reset_index(drop=True)
    ev["swing_dir"] = sdir[keep]
    ev["against_swing"] = ev["direction"].to_numpy() != ev["swing_dir"].to_numpy()
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"hedge_{TF}_hold14d", lambda: detect(cl.load_m1()))
    print(len(ev), ev["against_swing"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "against_swing", mask_available_at="decision_time", max_hold=HOLD[TF], claim="+")
    show(res)
    op = {"rules": ["swing book: 1D rung-0 CISD (series_open, 2/2, max_wait 3), entry next M1 open, protected-swing stop, 2R, time exit 14 calendar days; resolved on M1",
                    "intraday book: 15m rung-0 CISD, only signals fired while a swing is open (most recent open swing sets direction)",
                    "kept: intraday signal against the swing (hedge); complement: same direction (skipped by the rule)",
                    "claim +: kept beats skipped, control-adjusted"],
          "params": {"baseline_tf": TF, **BASE_PARAMS, "max_hold": HOLD[TF], "swing_tf": "1D",
                     "swing_hold": "14D", "swing_rr": 2.0, "overlap_rule": "most recent open swing", "grid4h": "n/a"}}
    src = {"baseline_tf": "phase3: primary stack entry TF (README gate example)",
           **{k: BASE_SRC for k in BASE_PARAMS}, "max_hold": HOLD_SRC,
           "swing_tf": "corpus: NESSCPMzWR0 daily-chart swing setups ('six to eight times a year'); the rung-0 1D book stands in",
           "swing_hold": "phase3: 10 entry-TF bars (§1.13) -> ~10 trading days = 14 calendar days (declared-before-run)",
           "swing_rr": "method_spec: §5.3 2R floor",
           "overlap_rule": "declared-before-run",
           "grid4h": "declared-before-run: no 4h bars used"}
    p = cl.write_result("hedge-not-double-exposure", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="The concept's claim is about exposure, not edge; this measures the per-trade expectancy cost of its selection. The 1D rung-0 book fires ~35/yr, far more than his 6-8/yr swings.")
    print("wrote", p)
