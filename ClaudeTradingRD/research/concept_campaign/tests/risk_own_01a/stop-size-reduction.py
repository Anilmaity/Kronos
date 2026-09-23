"""stop-size-reduction (contested) — two answers to "how do you reduce a stop that feels too big".

Reading A (W7Fu3Rx5iMs): keep the stop at structure and ENTER CLOSER TO IT — "move the
  limit deeper into the block so the distance to the same structural stop shrinks";
  same R multiple, now closer in price. Tested here.
Reading B (X4XSsv5CNqg): keep the stop, change POSITION SIZE. Sizing scales dollars, not
  R: every trade's R outcome is identical, so no R-based test can separate it from the
  baseline. Written as UNTESTABLE with that reason.

Reading A test — stacked variant rows on the phase-3 1h CISD entries:
  * complement rows: market entry (next M1 open after the confirming bar close), stop at
    the protected swing, 2R.
  * gated rows: a limit at the MEAN THRESHOLD of the opposing-candle block (50% between the
    series' opening edge — the CISD level — and its body extreme; spec §4.8 / §5.3
    'refine the entry ... to the mean threshold'), same stop, 2R of the new, smaller risk.
    The limit is live for 3 entry-TF bars (3h) after the decision and is cancelled if the
    market-entry 2R objective trades first (cancel-limit-after-target-run). The harness
    enters at the next M1 open after the bar that touches the limit (decision = that
    bar's close), which is the closest it can get to a resting limit fill.
claim '+': the refined (closer-to-invalidation) entry is the better trade, control-adjusted.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl, np, pd, cisd_raw, utc_ns, PHASE3_SRC  # noqa: E402

CID = "stop-size-reduction"
HOLD = "10h"
LIMIT_LIVE = pd.Timedelta("3h")


def detect(m1):
    b, ev = cisd_raw(m1, "1h")
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "limit_entry"]
    if ev is None:
        return pd.DataFrame(columns=cols)
    tn = utc_ns(m1.index)
    hi, lo = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    s = ev["direction"].to_numpy()
    close, stop = ev["close_px"].to_numpy(), ev["stop_px"].to_numpy()
    mt = 0.5 * (ev["level_px"].to_numpy() + ev["body_px"].to_numpy())
    tgt_mkt = close + 2.0 * (close - stop)                      # 2R of the market geometry
    dn = utc_ns(pd.DatetimeIndex(ev["decision_time"]))
    p0 = np.searchsorted(tn, dn, side="left")                   # first bar starting >= decision
    p1 = np.searchsorted(tn, dn + LIMIT_LIVE.value, side="left")
    fill_t = []
    valid = (s * (mt - stop) > 0) & (s * (close - mt) > 0)
    for k in range(len(ev)):
        fill_t.append(pd.NaT)
        if not valid[k] or p0[k] >= p1[k]:
            continue
        a, z = p0[k], p1[k]
        if s[k] > 0:
            touch = np.flatnonzero(lo[a:z] <= mt[k])
            tgt = np.flatnonzero(hi[a:z] >= tgt_mkt[k])
        else:
            touch = np.flatnonzero(hi[a:z] >= mt[k])
            tgt = np.flatnonzero(lo[a:z] <= tgt_mkt[k])
        if len(touch) == 0:
            continue
        if len(tgt) and tgt[0] <= touch[0]:                     # objective ran first: cancel
            continue
        j = a + touch[0]
        fill_t[-1] = m1.index[j] + pd.Timedelta(minutes=1)      # the touching bar's close
    fill_t = pd.DatetimeIndex(fill_t)
    has = ~fill_t.isna()
    mkt = ev[["decision_time", "available_at", "direction", "stop_px"]].assign(
        rr=2.0, limit_entry=False)
    lim = pd.DataFrame({"decision_time": fill_t[has], "available_at": fill_t[has],
                        "direction": s[has], "stop_px": stop[has], "rr": 2.0,
                        "limit_entry": True})
    out = pd.concat([mkt, lim]).sort_values(["decision_time", "limit_entry"], kind="stable")
    return out.reset_index(drop=True)[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("ssr_cisd1h_mt_limit_vs_market", lambda: detect(cl.load_m1()))
    print("rows", len(ev), "limit fills", int(ev["limit_entry"].sum()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "limit_entry", mask_available_at="decision_time", max_hold=HOLD,
                       claim="+")
    print({k: res.get(k) for k in ("n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "mde",
                                   "verdict", "verdict_detail", "ties", "exposure_bars",
                                   "ctrl_overlap", "n_events_in", "drop")})
    op = {"rules": [
        "entries: 1h CISD (series_open, 2/2 swings, max_wait 3); stop at the protected swing",
        "complement: market entry at the next M1 open after the confirming bar close, 2R",
        "gated: limit at the block mean threshold = 0.5*(CISD level + body extreme of the "
        "opposing series); live 3h; cancelled if the market-geometry 2R objective trades "
        "first; decision = close of the first M1 bar touching the limit, enter next M1 "
        "open, same stop, 2R of the new risk",
        "exit at stop, target or 10h from each row's decision"],
        "params": {"tf": "1h", "rr": 2.0, "limit_level": "block mean threshold",
                   "limit_live": "3h", "max_hold": HOLD}}
    src = {"tf": PHASE3_SRC, "max_hold": PHASE3_SRC, "rr": "method_spec §5.3: 2R",
           "limit_level": "method_spec §5.3: 'refine the entry ... to the mean threshold' "
                          "(the concept's 'deeper into the block')",
           "limit_live": "declared-before-run: 3 entry-TF bars (= phase-3 max_wait 3)"}
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Harness entries are at the next M1 open, so the limit is "
                              "approximated by entering right after the touching bar; a "
                              "fill whose own bar also reaches the stop cannot be scored "
                              "(the harness drops it as stop-not-beyond-entry), which "
                              "slightly flatters the limit arm — see drop counts.")
    print("wrote", p)

    cl.write_untestable(
        CID, "Reading B (keep the stop at structure, fix the dollar risk with position "
             "size) is pure sizing arithmetic: it changes dollars per trade, never the "
             "trade's R outcome, so it is identical to the baseline in every R-based test "
             "the harness can run.",
        reading="b", script=__file__)
    print("wrote untestable b")
