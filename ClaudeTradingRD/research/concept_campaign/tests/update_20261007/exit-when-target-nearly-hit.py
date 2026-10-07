"""exit-when-target-nearly-hit (TTrades, h1ZQWWQDhKA) — trade_test on the decision point.

Claim: once price is ~one point from TP and starts reversing, exit instead of holding
("now you're risking one point for all of that").

Parent book (same as break-even-management): 15m rung-0 CISD, entry next M1 open,
protected-swing stop, fixed 2R target, 150-minute hold, resolved on M1.
The exit rule only differs from holding at the moment the parent, still open, has
come within NEAR of its target and then reverses. At that moment the exiter is flat
and the holder keeps the ORIGINAL stop and target, so the claim is directional:
  event = close of the first M1 bar (at/after the near-target touch, parent still
          open, bar not touching stop/target) that closes >= REV below the trade's
          high-water mark
  trade = continue in the parent direction, parent stop, parent target, parent's
          remaining hold.
claim '-': continuing from there is worse than a matched random entry with the same
geometry, i.e. exiting beats holding.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
from _common import *   # noqa  (cl, np, pd, cisd_book, m1_arrays, show, BASE_*, HOLD*)

CID = "exit-when-target-nearly-hit"
READING = "u1007a"
TF = "15min"
RR = 2.0
NEAR_R = 0.1     # "one point" from TP, in R
REV_R = 0.1      # "price is reversing": a close one more 'point' back off the high-water mark
PARENT_HOLD = pd.Timedelta(HOLD[TF])
WMAX = 200
TOD_TOL = 30     # audit 2026-10-07: events cluster 0.3x-2.7x by NY hour -> README trap 9
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]


def detect(m1):
    ev, _, _ = cisd_book(m1, TF)
    tn, o, h, l_, c = m1_arrays(m1)
    N = len(tn)
    if ev.empty or N == 0:
        return pd.DataFrame({k: pd.Series(dtype="float64") for k in COLS})
    dec = cl.data.utc_ns(pd.DatetimeIndex(ev["decision_time"])).astype(np.int64)
    s = ev["direction"].to_numpy().astype(float)
    stop = ev["stop_px"].to_numpy(float)
    i0 = np.searchsorted(tn, dec, side="left")
    ok = i0 < N
    i0c = np.minimum(i0, N - 1)
    entry = o[i0c]
    risk = s * (entry - stop)
    ok &= np.isfinite(risk) & (risk > 0)
    tgt = entry + s * RR * risk
    end_ns = dec + PARENT_HOLD.value
    i1 = np.searchsorted(tn, end_ns, side="left")
    K = np.arange(WMAX)
    idx = i0c[:, None] + K[None, :]
    inwin = (idx < i1[:, None]) & (idx < N)
    idx = np.minimum(idx, N - 1)
    up = np.where(s[:, None] > 0, h[idx], -l_[idx])
    dn = np.where(s[:, None] > 0, l_[idx], -h[idx])
    cc = s[:, None] * c[idx]
    S, T, R = (s * stop)[:, None], (s * tgt)[:, None], risk[:, None]
    stop_hit = inwin & (dn <= S)
    tgt_hit = inwin & (up >= T)
    near = inwin & (up >= T - NEAR_R * R)
    BIG = WMAX + 1

    def first(m):
        return np.where(m.any(1), m.argmax(1), BIG)
    f_stop, f_tgt, f_near = first(stop_hit), first(tgt_hit), first(near)
    ok &= (f_near < f_stop) & (f_near < f_tgt)        # near-target reached, parent still open
    hwm = np.maximum.accumulate(np.where(inwin, up, -np.inf), axis=1)
    rev = inwin & (K[None, :] >= f_near[:, None]) & (cc <= hwm - REV_R * R) \
        & ~stop_hit & ~tgt_hit
    f_rev = first(rev)
    ok &= (f_rev < f_stop) & (f_rev < f_tgt) & (f_rev < BIG)
    fr = np.minimum(f_rev, WMAX - 1)
    rev_close = tn[np.minimum(i0c + fr, N - 1)] + 60_000_000_000
    rem = end_ns - rev_close
    ok &= rem > 0
    t = pd.to_datetime(rev_close[ok], utc=True)
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": s[ok].astype(int), "stop_px": stop[ok],
                        "target_px": tgt[ok], "max_hold": pd.to_timedelta(rem[ok], unit="ns")})
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame(f"near_tp_rev_{TF}_n{NEAR_R}_r{REV_R}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["max_hold"].describe())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, claim="-", ctrl_tod_tol_min=TOD_TOL)
    show(res)
    op = {"rules": [
        "parent: 15m rung-0 CISD (series_open, 2/2, max_wait 3), entry next M1 open, protected-swing stop, 2R target, 150min hold, resolved on M1",
        f"near target: parent's favourable excursion reaches within {NEAR_R}R of the target before any stop/target hit",
        f"reversing: first M1 bar at/after that touch whose close is >= {REV_R}R back off the trade's high-water mark (bar must not touch stop or target)",
        "decide at that bar's close; continue in the parent direction with the parent's stop, target and remaining hold",
        "claim -: holding from the near-target reversal is worse than a matched random entry of the same geometry -> exiting beats holding"],
        "params": {"parent_tf": TF, **BASE_PARAMS, "parent_hold": HOLD[TF], "near_R": NEAR_R,
                   "rev_R": REV_R, "grid4h": "n/a", "ctrl_tod_tol_min": TOD_TOL}}
    src = {"parent_tf": "phase3: primary stack entry TF (README gate example)",
           **{k: BASE_SRC for k in BASE_PARAMS}, "parent_hold": HOLD_SRC,
           "near_R": "corpus: h1ZQWWQDhKA 'not taking your profit if it's like one point away' -- one MNQ point on an intraday target is a few % of the target distance; declared-before-run as 5% of the 2R target = 0.1R",
           "rev_R": "corpus: h1ZQWWQDhKA 'one point away and price is reversing' -- 'reversing' undefined; declared-before-run as a close one more 'point' (0.1R) back off the high-water mark",
           "grid4h": "declared-before-run: no 4h bars used",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9 -- not a timing concept, but events cluster by NY hour (0.3x-2.7x the M1 base rate; audit 2026-10-07), so the control holds the NY clock fixed"}
    p = cl.write_result(CID, READING, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, allow_unknown_id=True,
                        notes=("Single pre-declared reading. The source gives one MNQ example and says "
                               "'to each their own'. The control geometry (target ~0.2R, stop ~2R away) "
                               "implies a high base win rate, so the sanity floor may bind."))
    print("wrote", p)
