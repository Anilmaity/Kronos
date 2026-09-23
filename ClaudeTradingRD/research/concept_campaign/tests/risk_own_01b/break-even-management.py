"""risk_own_01b / break-even-management (contested) — trade_test on the decision point.

Parent book: 15m rung-0 CISD (series_open, 2/2, max_wait 3), entry next M1 open,
stop at the protected swing, fixed 2R target, 150-minute hold (a 2R intraday
position, as in his CPI review).
Break-even only differs from holding on parents that first run to +TRIGGER_R and
then come BACK TO THE ENTRY PRICE. At that moment the break-even trader is out
(~0R) and the structural trader still holds a position with the ORIGINAL stop and
ORIGINAL target. So the BE decision is a directional claim about that moment:
  event   = close of the M1 bar that returns to entry after +1R was reached
            (parent still open: no stop/target hit before; bars touching the stop or
            target in the return bar are dropped as unresolvable)
  trade   = continue in the parent's direction, stop = parent stop, target = parent
            target, max_hold = the parent's remaining hold.
reading a (his own, intraday): "my trade is not invalidated at break even" — holding
through the return beats a matched random entry of the same geometry. Claim +.
The pro-break-even readings (scalp BE after a partial; 'a return to entry after
expansion means the move failed') are the mirror claim (-) of this same statistic:
a NEGATIVE here would support them. Not run separately (same hypothesis).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
from _common import *   # noqa

TF = "15min"
TRIGGER_R = 1.0
PARENT_HOLD = pd.Timedelta(HOLD[TF])
WMAX = 200


def detect(m1):
    ev, _, _ = cisd_book(m1, TF)
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    tn, o, h, l_, c = m1_arrays(m1)
    N = len(tn)
    dec = cl.data.utc_ns(pd.DatetimeIndex(ev["decision_time"])).astype(np.int64)
    s = ev["direction"].to_numpy().astype(float)
    stop = ev["stop_px"].to_numpy(float)
    i0 = np.searchsorted(tn, dec, side="left")
    ok = i0 < N
    i0c = np.minimum(i0, N - 1)
    entry = o[i0c]
    risk = s * (entry - stop)
    ok &= np.isfinite(risk) & (risk > 0)
    tgt = entry + s * 2.0 * risk
    end_ns = dec + PARENT_HOLD.value
    i1 = np.searchsorted(tn, end_ns, side="left")
    K = np.arange(WMAX)
    idx = i0c[:, None] + K[None, :]
    inwin = (idx < i1[:, None]) & (idx < N)
    idx = np.minimum(idx, N - 1)
    up = np.where(s[:, None] > 0, h[idx], -l_[idx])
    dn = np.where(s[:, None] > 0, l_[idx], -h[idx])
    E, S, T, R = (s * entry)[:, None], (s * stop)[:, None], (s * tgt)[:, None], risk[:, None]
    stop_hit = inwin & (dn <= S)
    tgt_hit = inwin & (up >= T)
    trig = inwin & (up >= E + TRIGGER_R * R)
    back = inwin & (dn <= E)
    BIG = WMAX + 1

    def first(m):
        return np.where(m.any(1), m.argmax(1), BIG)
    f_stop, f_tgt, f_trig = first(stop_hit), first(tgt_hit), first(trig)
    # trigger must come strictly before any stop; at/before target is fine only if
    # the target bar is later (a bar hitting both trigger and target ends the parent)
    ok &= (f_trig < f_stop) & (f_trig < f_tgt)
    after = back & (K[None, :] > f_trig[:, None])
    f_back = first(after)
    ok &= f_back < BIG
    ok &= (f_back <= f_stop) & (f_back <= f_tgt)      # nothing ended the parent before
    rr_ = np.arange(len(ev))
    fb = np.minimum(f_back, WMAX - 1)
    ok &= ~stop_hit[rr_, fb] & ~tgt_hit[rr_, fb]      # return bar itself unresolvable
    ret_close = tn[np.minimum(i0c + fb, N - 1)] + 60_000_000_000
    rem = end_ns - ret_close
    ok &= rem > 0
    t = pd.to_datetime(ret_close[ok], utc=True)
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": s[ok].astype(int), "stop_px": stop[ok],
                        "target_px": tgt[ok], "max_hold": pd.to_timedelta(rem[ok], unit="ns")})
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"be_return_{TF}_trig{TRIGGER_R}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["max_hold"].describe())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, claim="+")
    show(res)
    op = {"rules": ["parent: 15m rung-0 CISD, entry next M1 open, protected-swing stop, 2R target, 150min hold, resolved on M1",
                    f"event: first M1 bar after the parent reached +{TRIGGER_R}R that trades back to the entry price, parent still open; bars also touching stop/target dropped",
                    "decide at that bar's close; continue in the parent direction with the parent's stop, target and remaining hold",
                    "claim +: not invalidated at break-even -> continuation beats a matched random entry"],
          "params": {"parent_tf": TF, **BASE_PARAMS, "parent_hold": HOLD[TF], "trigger_R": TRIGGER_R, "grid4h": "n/a"}}
    src = {"parent_tf": "phase3: primary stack entry TF (README gate example)",
           **{k: BASE_SRC for k in BASE_PARAMS}, "parent_hold": HOLD_SRC,
           "trigger_R": "declared-before-run: 'expanded meaningfully' is unquantified in the corpus; half of the 2R target",
           "grid4h": "declared-before-run: no 4h bars used"}
    p = cl.write_result("break-even-management", "a", res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes=("One statistic decides both sides: BE is better than holding exactly when the "
                               "continuation from the return-to-entry point is worse than random (claim -). "
                               "The pro-BE reading was not run separately to avoid a duplicate hypothesis."))
    print("wrote", p)
