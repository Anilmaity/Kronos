"""trail-market-structure-swings — trail the stop along low-timeframe structure: after
displacement over the prior high, wait for a completed higher low and move the stop there
(CrUfTskOveo: "i'll trail that higher low make a new high").

The harness resolves fixed brackets only, so the management rule is scored where it
acts, following the campaign precedent for stop-management concepts (risk_guest_02a
no-stop-change-before-first-target / t1-t2-partial-system): an event is emitted at the
moment the rule MOVES the stop, and the position from there on (stop = the new higher
low, same original target, the rest of the original hold) is scored against a matched
random entry with the same stop distance, target distance and hold. If a structural
higher low really protects the position, that leg beats random geometry (claim '+').

Base book (phase-3 locked): 1h CISD (series_open, 2/2, max_wait 3, min_series 1),
decide at the confirming 1h close, entry = next M1 open, stop = protected swing,
target = 2R from that entry, hold 10h.
Trail rule, on 2-minute bars built from M1 (the corpus: "a one- or two-minute chart"):
  * prior high = the latest 2m 2/2 swing high confirmed by the entry decision (long;
    mirror for shorts).
  * displacement over it = the first 2m bar after entry that CLOSES above it.
  * completed higher low = the first 2m 2/2 swing low whose swing bar is after that
    break bar and which lies above the current (original) stop; known at the close of
    its 2nd right bar.
  * the original bracket must still be alive (no stop or target touch) through that
    close; the remaining hold must be >= 10 minutes.
  * event at that close: same direction, stop = the higher low, target = the original
    2R target, max_hold = original 10h deadline minus the event time. First trail only.
The first-partial/break-even step that precedes trailing in the corpus is not modelled
(the harness has no partials); only the structure trail is scored.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl, np, pd, cisd_book, show, PHASE3_SRC, HOLD_SRC  # noqa: E402

CID = "trail-market-structure-swings"
HOLD = pd.Timedelta("10h")
MIN_LEFT = pd.Timedelta("10min")
RR = 2.0
LTF = "2min"


def _swings(x: np.ndarray, left: int = 2, right: int = 2) -> np.ndarray:
    n = len(x)
    ok = np.zeros(n, bool)
    if n <= left + right:
        return ok
    ok[left:n - right] = True
    for k in range(1, left + 1):
        ok[left:n - right] &= x[left - k:n - right - k] < x[left:n - right]
    for k in range(1, right + 1):
        ok[left:n - right] &= x[left + k:n - right + k] <= x[left:n - right]
    return ok


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    ev = cisd_book(m1, "1h")
    if ev.empty:
        return pd.DataFrame(columns=cols)
    b = cl.build_bars(m1, LTF)
    bt = pd.DatetimeIndex(b.index).tz_convert("UTC").as_unit("ns").asi8
    bct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC").as_unit("ns").asi8
    H, L, C = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    sh = np.flatnonzero(_swings(H))            # swing-high bars
    sl = np.flatnonzero(_swings(-L))           # swing-low bars
    sh_conf = bct[np.minimum(sh + 2, len(bct) - 1)]
    sl_conf = bct[np.minimum(sl + 2, len(bct) - 1)]
    mt = pd.DatetimeIndex(m1.index).tz_convert("UTC").as_unit("ns").asi8
    mo = m1["open"].to_numpy(float)
    rows = []
    for dt, s, stop in zip(pd.DatetimeIndex(ev["decision_time"]).as_unit("ns").asi8,
                           ev["direction"].to_numpy(), ev["stop_px"].to_numpy(float)):
        p = np.searchsorted(mt, dt, side="left")
        if p >= len(mt):
            continue
        entry = mo[p]
        risk = s * (entry - stop)
        if not risk > 0:
            continue
        tgt = entry + s * RR * risk
        deadline = dt + HOLD.value
        # prior 2m swing extreme in the trade direction, confirmed by the decision
        if s > 0:
            ref_bars, ref_conf, px = sh, sh_conf, H
            hl_bars, hl_conf, hlpx = sl, sl_conf, L
        else:
            ref_bars, ref_conf, px = sl, sl_conf, L
            hl_bars, hl_conf, hlpx = sh, sh_conf, H
        n_ok = np.searchsorted(ref_conf, dt, side="right")
        n_ok = n_ok if n_ok <= len(ref_bars) else len(ref_bars)
        # confirmation stamps are sorted with the bars; take the last one known by dt
        kref = n_ok - 1
        while kref >= 0 and (ref_bars[kref] + 2 >= len(bct) or bct[ref_bars[kref] + 2] > dt):
            kref -= 1
        if kref < 0:
            continue
        ref = px[ref_bars[kref]]
        i0 = np.searchsorted(bt, dt, side="left")
        i1 = np.searchsorted(bct, deadline, side="right")        # bars closed by deadline
        if i1 <= i0:
            continue
        seg_c = C[i0:i1]
        brk = np.flatnonzero(s * (seg_c - ref) > 0)
        if len(brk) == 0:
            continue
        kb = i0 + brk[0]
        # first swing low (long) after the break bar, above the stop
        cand = hl_bars[(hl_bars > kb) & (hl_bars + 2 < i1)]
        cand = cand[s * (hlpx[cand] - stop) > 0]
        if len(cand) == 0:
            continue
        j = cand[0]
        ce = j + 2
        t_e = bct[ce]
        if t_e > mt[-1] + 60_000_000_000:
            continue
        # original bracket still alive through the event close
        seg_h, seg_l = H[i0:ce + 1], L[i0:ce + 1]
        if s > 0:
            alive = (seg_l.min() > stop) and (seg_h.max() < tgt)
        else:
            alive = (seg_h.max() < stop) and (seg_l.min() > tgt)
        if not alive:
            continue
        left = deadline - t_e
        if left < MIN_LEFT.value:
            continue
        rows.append((t_e, t_e, int(s), float(hlpx[j]), float(tgt), left))
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=cols)
    out["decision_time"] = pd.to_datetime(out["decision_time"], utc=True)
    out["available_at"] = pd.to_datetime(out["available_at"], utc=True)
    out["max_hold"] = pd.to_timedelta(out["max_hold"], unit="ns")
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("tmss_cisd1h_2m_first_trail", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, claim="+")
    show(res)
    op = {"rules": [
        "base: 1h CISD (series_open, 2/2, max_wait 3, min_series 1), decide at confirm "
        "close, entry next M1 open, stop protected swing, target 2R, hold 10h",
        "prior high = latest 2m 2/2 swing high (long) confirmed by the decision",
        "displacement = first 2m close beyond it after entry",
        "higher low = first 2m 2/2 swing low after the break bar, above the original stop, "
        "known at its 2nd right bar's close; original bracket untouched through then",
        "event: stop = the higher low, target = original 2R target, hold = rest of the 10h "
        "(>= 10 min); first trail only; scored vs matched random entry"],
        "params": {"entry_tf": "1h", "trail_tf": LTF, "swing": "2/2", "rr": RR,
                   "max_hold": "10h total", "min_left": "10min", "trails_scored": "first"}}
    src = {"entry_tf": PHASE3_SRC, "rr": PHASE3_SRC, "max_hold": HOLD_SRC,
           "swing": "phase3: 2/2 swings (§1.8)",
           "trail_tf": "corpus: CrUfTskOveo trail on 'a one- or two-minute chart'",
           "min_left": "declared-before-run: skip trails with under 10 minutes of hold left",
           "trails_scored": "declared-before-run: first stop move only, one event per trade"}
    print(cl.write_result(CID, None, res, operationalization={**op}, params_source=src,
                          script=__file__, probe=probe,
                          notes="Stop management scored at the moment of the stop move "
                                "(campaign precedent for management rules): the trailed leg "
                                "vs random geometry. The first partial / break-even step "
                                "and later trail steps are not modelled."))
