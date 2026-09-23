"""market-structure-break-significance (guest: AM Trades, CrUfTskOveo; host disagrees) -> gate_test.

Contested: AM Trades says a market structure BREAK (a close beyond an INTERMEDIATE-term
swing, i.e. a swing formed by a retracement rebalancing a fair value gap) is more
significant than an ordinary market structure SHIFT (a close beyond any swing). The host
says they are "all basically the same". One gate test decides between them:
claim '+' (AM Trades): MSB breaks beat ordinary MSS breaks on control-adjusted R.
A powered NULL is the host's reading; an EDGE is the guest's.

Reading (declared before the first run):
  * 30m bars (the only timeframe he attaches: "a 30-minute close above a high").
  * Swings: fractal 2/2, known at the close of the bar two after the swing.
  * Structure break: the first 30m CLOSE beyond a swing low (bearish) / high (bullish)
    within 96 bars (48h) of the swing's confirmation. All swings broken by the same bar
    form one event.
  * Intermediate-term (rebalanced) swing low: a bullish three-bar FVG completed in the 20
    bars before the swing bar, not traded below its bottom before the swing bar, with the
    swing low inside the gap (gap_low <= low <= gap_high). Mirror for highs.
  * Gate is_msb: at least one swing broken by the event bar is intermediate-term.
  * Trade: in the break direction at the next M1 open after the break bar's close; stop at
    the extreme since the most recent broken swing (for a short: the highest high from that
    swing bar through the break bar - the high that "must stay unviolated"); 2R; hold 10 bars
    = 300 min.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _common import swings22, from_ns  # noqa: E402

CID = "market-structure-break-significance"
TF = "30min"
WATCH = 96
FVG_LOOK = 20
RR = 2.0
MAX_HOLD = "300min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "is_msb", "n_broken"]


def _short_events(h, l, c, n):
    """Bearish breaks of swing lows; prices may be mirrored by the caller."""
    _, sl = swings22(h, l)
    # bullish FVG at k: l[k] > h[k-2], gap (h[k-2], l[k])
    fk = np.zeros(n, bool)
    fk[2:] = l[2:] > h[:-2]
    fk_idx = np.flatnonzero(fk)
    itl = {}
    brk = {}
    for i in np.flatnonzero(sl):
        # intermediate-term (rebalanced) swing low?
        is_it = False
        lo_k = np.searchsorted(fk_idx, i - FVG_LOOK, "left")
        hi_k = np.searchsorted(fk_idx, i, "left")
        for k in fk_idx[lo_k:hi_k]:
            g_lo, g_hi = h[k - 2], l[k]
            if not (g_lo <= l[i] <= g_hi):
                continue
            if k + 1 < i and l[k + 1:i].min() < g_lo:
                continue
            is_it = True
            break
        itl[i] = is_it
        j0, j1 = i + 3, min(n, i + 3 + WATCH)
        if j0 >= j1:
            continue
        hit = np.flatnonzero(c[j0:j1] < l[i])
        if len(hit):
            brk.setdefault(j0 + int(hit[0]), []).append(i)
    rows = []
    for j, sw in brk.items():
        s_last = max(sw)
        stop = h[s_last:j + 1].max()
        rows.append((j, stop, any(itl[s] for s in sw), len(sw)))
    return rows


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    if len(b) < 10:
        return pd.DataFrame(columns=COLS)
    h, l, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    ct = b["close_time"].values.astype("datetime64[ns]").astype(np.int64)
    n = len(b)
    out = []
    for j, stop, msb, nb in _short_events(h, l, c, n):
        out.append((int(ct[j]), -1, stop, msb, nb))
    for j, stop, msb, nb in _short_events(-l, -h, -c, n):
        out.append((int(ct[j]), 1, -stop, msb, nb))
    if not out:
        return pd.DataFrame(columns=COLS)
    o_ = pd.DataFrame(out, columns=["t", "direction", "stop_px", "is_msb", "n_broken"])
    dec = from_ns(o_["t"].to_numpy())
    ev = pd.DataFrame({"decision_time": dec, "available_at": dec,
                       "direction": o_["direction"].astype(int).to_numpy(),
                       "stop_px": o_["stop_px"].to_numpy(float), "rr": RR,
                       "is_msb": o_["is_msb"].astype(bool).to_numpy(),
                       "n_broken": o_["n_broken"].astype(int).to_numpy()})
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}_w{WATCH}_f{FVG_LOOK}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["is_msb"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "is_msb", mask_available_at="decision_time", max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "complement"):
        print(k, res.get(k))
    op = {"rules": [
        "30m bars; fractal 2/2 swings known two bars after the swing",
        "structure break: first 30m close beyond a swing within 96 bars of confirmation; "
        "swings broken by the same bar = one event",
        "intermediate-term (rebalanced) swing: swing extreme inside a same-side FVG completed "
        "in the 20 bars before it and not violated before the swing bar",
        "is_msb = the event breaks at least one intermediate-term swing",
        "trade the break at the next M1 open; stop = extreme since the most recent broken "
        "swing; 2R; hold 300 min",
        "gate_test: MSB vs ordinary MSS, control-adjusted"],
        "params": {"tf": TF, "watch_bars": WATCH, "fvg_lookback": FVG_LOOK, "rr": RR,
                   "max_hold": MAX_HOLD, "swing": "fractal 2/2"}}
    src = {"tf": "corpus: CrUfTskOveo MSS example is a 30-minute close ('a 30-minute close above "
                 "a high'); used for both arms",
           "watch_bars": "declared-before-run: a swing is live for 96 bars (48h)",
           "fvg_lookback": "declared-before-run: the rebalanced FVG must be formed within 20 bars "
                           "before the swing",
           "rr": "declared-before-run: no target stated; 2R (phase3 primary)",
           "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13)",
           "swing": "phase3: swing fractal left=2, right=2 (preregistration 1.16)"}
    notes = ("Contested concept: one gate answers both readings. EDGE would support AM Trades' "
             "MSB>MSS significance; a powered NULL supports the host's 'all basically the same'. "
             "Written as reading a (AM Trades); the host reading is the H0 of the same test, so no second test was run.")
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
