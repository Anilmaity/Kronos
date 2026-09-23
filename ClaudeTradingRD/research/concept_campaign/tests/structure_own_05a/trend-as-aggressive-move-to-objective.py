"""trend-as-aggressive-move-to-objective (TTrades own voice) — batch structure_own_05a.

"the way I define trend is an aggressive move reaching towards an objective" (NgFIza9qsGQ):
the objective is a marked higher-timeframe point of interest / liquidity pool; in a genuine
trend there are few (and shallow) pullbacks. Testable content: once price moves
AGGRESSIVELY toward an unreached HTF objective, it continues to that objective without a
deep retracement.

trade_test (1h move, 1D objective):
  aggressive : threshold_fits displacement, both components - a 1h CLOSE above the most
               recent confirmed 2/2 fractal swing high (structural gate), and over the
               N=4 candles from the break win_range/pre_range >= 1.5 and
               (window high - broken level)/pre_range >= 0.65 (pre_range = the 4 candles
               before the break); decided at the close of the 4th window candle
  objective  : the previous trading day's high (liquidity pool), still ABOVE that close and
               not yet traded in the current trading day (the move is reaching toward it)
  trade      : long at the next M1 open, target = the objective, stop = 0.5 of the window's
               leg (window low -> window high): a retracement deeper than 'shallow'
               (threshold_fits 0.50) means it is not a trend; exit after 10h
  mirror for bearish breaks toward the previous day's low.
claim '+' vs the matched random-entry control.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05a")
from _common import cl, np, pd, summary  # noqa: E402

CID = "trend-as-aggressive-move-to-objective"
TF = "1h"
N, R_CUT, D_CUT = 4, 1.5, 0.65
SHALLOW = 0.5
MAX_HOLD = "10h"
TOD_TOL = 30
MIN_COV = 0.5


def _events_side(o, h, l, c, bull):
    """Displacement breaks of the last confirmed 2/2 swing, one side. Works in 'high' space
    for bullish; bearish is run on negated prices."""
    n = len(c)
    rows = []
    last_sw = np.nan
    broken = True
    for j in range(4, n):
        k = j - 2                      # swing at k confirmed at the close of k+2 = j
        if k >= 2 and h[k] > h[k - 1] and h[k] > h[k - 2] and h[k] > h[k + 1] and h[k] > h[k + 2]:
            last_sw, broken = h[k], False
        # break on bar j+? : evaluated on the bar after confirmation onward
        if broken or not np.isfinite(last_sw):
            continue
        # j is the candidate break bar only if it closes above the level
        if c[j] > last_sw and j - N >= 0 and j + N - 1 < n:
            broken = True
            pre = h[j - N:j].max() - l[j - N:j].min()
            wh, wl = h[j:j + N].max(), l[j:j + N].min()
            if pre > 0 and (wh - wl) / pre >= R_CUT and (wh - last_sw) / pre >= D_CUT:
                rows.append((j, j + N - 1, last_sw, wh, wl))
        elif c[j] > last_sw:
            broken = True
    return rows


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    if len(b) < 20:
        return pd.DataFrame(columns=cols)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    td = cl.trading_day(b.index)
    rh = b["high"].groupby(td).cummax().to_numpy(float)
    rl = b["low"].groupby(td).cummin().to_numpy(float)
    out = []
    for bull in (True, False):
        s = 1.0 if bull else -1.0
        oo, hh, ll, cc = (o, h, l, c) if bull else (-o, -l, -h, -c)
        for j, e, lvl, wh, wl in _events_side(oo, hh, ll, cc, bull):
            out.append((e, 1 if bull else -1, s * (wl + SHALLOW * (wh - wl)), cc[e] * s))
    if not out:
        return pd.DataFrame(columns=cols)
    f = pd.DataFrame(out, columns=["e", "direction", "stop_px", "close"])
    e = f["e"].to_numpy()
    t = ct[e]
    lv = cl.prior_hilo(t, "1D", m1=m1, min_coverage=MIN_COV)
    pdh, pdl = lv["high"].to_numpy(float), lv["low"].to_numpy(float)
    d = f["direction"].to_numpy()
    cl_ = f["close"].to_numpy(float)
    tgt = np.where(d > 0, pdh, pdl)
    reach = np.where(d > 0, (pdh > cl_) & (rh[e] < pdh), (pdl < cl_) & (rl[e] > pdl))
    keep = np.isfinite(tgt) & reach & np.where(d > 0, f["stop_px"] < cl_, f["stop_px"] > cl_)
    res = pd.DataFrame({"decision_time": t[keep], "available_at": t[keep],
                        "direction": d[keep].astype(int),
                        "stop_px": f["stop_px"].to_numpy(float)[keep],
                        "target_px": tgt[keep]})
    return res.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    ev = cl.cache_frame(f"trendobj_{TF}_{N}_{R_CUT}_{D_CUT}_{SHALLOW}", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, claim="+", ctrl_tod_tol_min=TOD_TOL)
    print(summary(res))
    op = {"rules": [
        "1h close above the most recent confirmed 2/2 fractal swing high (first close through it)",
        "displacement: over the 4 candles from the break, window range / pre-break 4-candle range "
        ">= 1.5 and (window high - broken swing) / pre-break range >= 0.65; decided at the 4th "
        "window candle's close",
        "objective: previous trading day's high (coverage >= 0.5), above that close and not yet "
        "traded today",
        "long at next M1 open; stop = 50% of the window leg (window low -> high); target = the "
        "objective; exit after 10h; mirror for bearish toward the previous day's low"],
        "params": {"tf": TF, "swing": "2/2", "disp_N": N, "disp_r": R_CUT, "disp_d": D_CUT,
                   "stop_retrace": SHALLOW, "objective": "PDH/PDL unreached today",
                   "max_hold": MAX_HOLD, "ctrl_tod_tol_min": TOD_TOL, "min_coverage": MIN_COV}}
    src = {"tf": "declared-before-run: the move is read one timeframe under the 4H/1D objective (yaml htf 1D/4H)",
           "swing": "method_spec: §1.1 three-candle fractal / phase3 2/2",
           "disp_N": "threshold_fits: displacement N=4 (grade B)",
           "disp_r": "threshold_fits: r=1.5", "disp_d": "threshold_fits: d=0.65",
           "stop_retrace": "threshold_fits: shallow = pullback/impulse <= 0.50; corpus 'you do not want to see many pullbacks'",
           "objective": "corpus: NgFIza9qsGQ objective = marked HTF POI / liquidity pool (yaml preconditions); previous day extreme = method_spec §5.2 target #1",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9",
           "min_coverage": "declared-before-run: README trap 6 stub-session guard"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="'Aggressive' is unquantified in the unit; threshold_fits' displacement "
                              "(= aggressive, one term) supplies it. The HTF order-block objective is "
                              "replaced by the previous day's extreme (a liquidity pool, allowed by "
                              "the preconditions). The LTF mitigation-block entry is not modelled; "
                              "entry is at the displacement window's close.")
    print("wrote", p)


if __name__ == "__main__":
    main()
