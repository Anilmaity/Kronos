"""lack-of-displacement-entry — "Trade the lack of displacement" (TTrades own voice, 5rbFskdmEmU).

Batch entry_own_04a. trade_test, claim '+'.

Operationalisation (all declared BEFORE the first run):
  side of the curve (HTF = 15m, "I prefer to wait for a higher time frame low to be broken"):
    15m fractal swings 2/2 (usable once the 2 right bars have closed). A DISPLACEMENT break =
    the first 15m candle to CLOSE beyond the most recent confirmed swing (threshold_fits
    component (a), structural, A-grade) AND the N=4 window from that candle has
    win_range/pre_range >= 1.5 and distance-beyond-level/pre_range >= 0.65 (component (b),
    B-grade defaults). Up-break -> buy side (+1), down-break -> sell side (-1). The side is
    known at the close of the 4th window candle and holds until the opposite displacement.
  entry (LTF = 1m): each 1m short-term low (fractal 2/2, usable after its 2 right bars closed)
    that is TAKEN (a 1m low below it) by a candle that CLOSES BACK ABOVE it = a failure to
    displace -> long, when on the buy side. Mirror: short-term high taken by a candle that
    closes back below it, on the sell side -> short. A take that closes beyond = displacement,
    no trade (it is the concept's invalidation / continuation read).
  decide at the sweep candle's close; enter next M1 open (harness).
  stop: the sweep candle's extreme (the swept low/high). target 2R. max_hold 10 entry-TF bars.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402
import concept_lab as cl  # noqa: E402

CID = "lack-of-displacement-entry"
P = {"side_tf": "15min", "entry_tf": "1min", "swing": "2/2", "disp_N": 4, "disp_r": 1.5,
     "disp_d": 0.65, "rr": 2.0, "max_hold": "10min"}


def _swings(h, l):
    n = len(h)
    ish = np.zeros(n, bool)
    isl = np.zeros(n, bool)
    if n >= 5:
        m = slice(2, n - 2)
        ish[m] = (h[m] > h[1:n - 3]) & (h[m] > h[0:n - 4]) & (h[m] >= h[3:n - 1]) & (h[m] >= h[4:n])
        isl[m] = (l[m] < l[1:n - 3]) & (l[m] < l[0:n - 4]) & (l[m] <= l[3:n - 1]) & (l[m] <= l[4:n])
    return ish, isl


def _current_level(flag, px):
    """Level + id of the most recent swing whose confirmation (bar i+2) closed by bar j-1."""
    n = len(px)
    pos = np.where(flag)[0]
    eff = pos + 3
    ok = eff < n
    lvl = np.full(n, np.nan)
    sid = np.full(n, np.nan)
    lvl[eff[ok]] = px[pos[ok]]
    sid[eff[ok]] = pos[ok]
    lvl = pd.Series(lvl).ffill().to_numpy()
    sid = pd.Series(sid).ffill().to_numpy()
    return lvl, sid


def _first_in_group(cond, sid):
    s = pd.Series(cond & ~np.isnan(sid))
    g = pd.Series(np.nan_to_num(sid, nan=-1))
    cs = s.astype(int).groupby(g).cumsum()
    return (s & (cs == 1)).to_numpy()


def side_frame(b):
    h, l, c = (b[k].to_numpy() for k in ("high", "low", "close"))
    ct = b["close_time"].to_numpy()
    n = len(b)
    ish, isl = _swings(h, l)
    N = P["disp_N"]
    rows = []
    for flag, px, sgn in ((ish, h, 1), (isl, l, -1)):
        lvl, sid = _current_level(flag, px)
        brk = (c > lvl) if sgn == 1 else (c < lvl)
        first = _first_in_group(np.nan_to_num(brk, nan=False).astype(bool), sid)
        for k in np.where(first)[0]:
            if k + N - 1 >= n or k - N < 0:
                continue
            wh, wl = h[k:k + N].max(), l[k:k + N].min()
            pre = h[k - N:k].max() - l[k - N:k].min()
            if pre <= 0:
                continue
            dist = (wh - lvl[k]) if sgn == 1 else (lvl[k] - wl)
            if (wh - wl) / pre >= P["disp_r"] and dist / pre >= P["disp_d"]:
                rows.append((ct[k + N - 1], sgn))
    if not rows:
        return pd.DataFrame({"t": pd.DatetimeIndex([], tz="UTC"), "side": []})
    sf = pd.DataFrame(rows, columns=["t", "side"])
    sf["t"] = pd.to_datetime(sf["t"], utc=True)
    # two opposite breaks stamped at the same close: ambiguous -> keep the later-sorted
    # deterministic one (sort by time then side) — drop exact-time duplicates entirely
    sf = sf.sort_values(["t", "side"]).drop_duplicates("t", keep=False)
    return sf.reset_index(drop=True)


def detect(m1):
    b15 = cl.build_bars(m1, P["side_tf"])
    sf = side_frame(b15)
    b1 = cl.build_bars(m1, P["entry_tf"])
    h, l, c = (b1[k].to_numpy() for k in ("high", "low", "close"))
    ct = pd.DatetimeIndex(b1["close_time"])
    ish, isl = _swings(h, l)
    out = []
    # longs: short-term low taken, close back above
    lvl, sid = _current_level(isl, l)
    take = np.nan_to_num(l < lvl, nan=False).astype(bool)
    first = _first_in_group(take, sid)
    fail = first & (c > lvl)
    out.append(pd.DataFrame({"decision_time": ct[fail], "direction": 1, "stop_px": l[fail]}))
    lvl, sid = _current_level(ish, h)
    take = np.nan_to_num(h > lvl, nan=False).astype(bool)
    first = _first_in_group(take, sid)
    fail = first & (c < lvl)
    out.append(pd.DataFrame({"decision_time": ct[fail], "direction": -1, "stop_px": h[fail]}))
    ev = pd.concat(out, ignore_index=True).sort_values(["decision_time", "direction"])
    ev = ev.reset_index(drop=True)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "side_at"]
    if ev.empty or sf.empty:
        return pd.DataFrame(columns=cols)
    j = pd.merge_asof(ev[["decision_time"]].reset_index(),
                      sf.rename(columns={"t": "side_t"}), left_on="decision_time",
                      right_on="side_t", direction="backward").set_index("index")
    ev["side"] = j["side"].to_numpy()
    ev["side_at"] = pd.to_datetime(j["side_t"].to_numpy(), utc=True)
    ev = ev[ev["side"].notna() & (ev["side"] == ev["direction"])].copy()
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = P["rr"]
    return ev[cols].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("lode_15m_side_1m_entry_v1", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=P["max_hold"])
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "ties", "exposure_bars", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "side of the curve from 15m: first 15m CLOSE beyond the latest confirmed 2/2 swing, "
        "with N=4 window win_range/pre_range>=1.5 and distance/pre_range>=0.65; up=buy side, "
        "down=sell side; known at the 4th window candle's close; holds until the opposite",
        "buy side: 1m 2/2 short-term low first taken by a candle that closes back ABOVE it "
        "(no displacement) -> long; sell side mirror with short-term highs -> short",
        "decide at the sweep candle close, enter next M1 open; stop at the sweep candle's "
        "extreme; target 2R; time exit after 10 minutes"], "params": P}
    src = {"side_tf": "corpus: 5rbFskdmEmU 'I prefer to wait for a higher time frame low to be "
                      "broken' + concept timeframes.htf [15m, 5m]",
           "entry_tf": "corpus: concept timeframes.ltf [1m] (5rbFskdmEmU)",
           "swing": "phase3: 2/2 fractal swings (conjunction_preregistration locked config)",
           "disp_N": "threshold_fits: displacement magnitude N=4 (grade B)",
           "disp_r": "threshold_fits: win_range/pre_range >= 1.5 (grade B)",
           "disp_d": "threshold_fits: distance/pre_range >= 0.65 (grade B)",
           "rr": "method_spec: §5.3 '2R described as normal' (no target stated in 5rbFskdmEmU)",
           "max_hold": "phase3: max_hold = 10 entry-TF bars (§1.13) -> 10 x 1m"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Stop/target are not given in the source video; the stop at the "
                              "swept extreme and 2R are declared defaults. The failure test is "
                              "the sweep candle itself closing back inside (the concept's "
                              "'small break followed by an immediate close back inside').")
    print(p)
