"""htf-poi-gate-before-ltf (contested) — "Do not drop timeframes until the POI is tagged".

Claim: lower-timeframe entries are only worth taking after price has returned to a
higher-timeframe point of interest marked before the session. Tested as a gate_test on
a baseline book of lower-timeframe entries (the campaign's canonical CISD entry model,
phase-3 locked: series_open, 2/2, max_wait 3, min_series 1; stop at the protected
swing; 2R; hold 10 entry-TF bars). gate = a marked HTF POI was tagged earlier in the
same trading day (18:00 NY roll), before the CISD decision; claim '+'.

POIs are marked at the trading-day open S (everything known by S):
  * HTF fair value gaps (three-bar) formed within the last N HTF bars before S and still
    unfilled at S (price never traded back to the gap's near edge between its formation
    and S). Bullish gap: near edge = 3rd bar low (support); bearish: 3rd bar high.
  * the previous trading day's high and low (prior_hilo 1D, min_coverage 0.5).
  "Tagged" = first M1 bar after S that trades to the level (the concept leaves "reached"
  undefined, so the near edge is used); known at that M1 bar's close.

Reading a (education_ict_02, own voice): 4H POIs (4H FVG, forex grid, last 30 4H bars)
  + PDH/PDL; entries on the paired 15m; no cap, and direction-agnostic ("the lower
  timeframe supplies either the entry INTO the level or the entry AWAY from it").
Reading b (t_talks_02 variant): at most two POIs, on the 1H (1H FVGs, last 24 1H bars)
  + PDH/PDL, each in line with the daily bias; bias = the previous trading day's candle
  direction (close vs open); aligned POIs = support for a bullish bias (bullish FVGs,
  PDL), resistance for a bearish bias (bearish FVGs, PDH); the two nearest to the day's
  opening price are kept. Entries on the paired 5m, bias-aligned CISDs only (the
  baseline), gate = one of the two marked POIs tagged earlier that day.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl, np, pd, cisd_book, show, PHASE3_SRC, HOLD_SRC  # noqa: E402

CID = "htf-poi-gate-before-ltf"
CFG = {"a": dict(htf="4h", ltf="15min", fvg_lookback=30, cap=None, aligned=False,
                 hold="150min"),
       "b": dict(htf="1h", ltf="5min", fvg_lookback=24, cap=2, aligned=True,
                 hold="50min")}


def _ns(x) -> np.ndarray:
    return pd.DatetimeIndex(x).tz_convert("UTC").as_unit("ns").asi8


def day_pois(m1: pd.DataFrame, htf: str, fvg_lookback: int, cap, aligned: bool):
    """Per trading day: tag times (ns, the tag bar's close) of that day's marked POIs."""
    d1 = cl.build_bars(m1, "1D")
    S = pd.DatetimeIndex(d1.index).tz_convert("UTC").as_unit("ns")
    E = pd.DatetimeIndex(d1["close_time"]).tz_convert("UTC").as_unit("ns")
    day_open = d1["open"].to_numpy(float)
    ph = cl.prior_hilo(S, "1D", m1=m1, min_coverage=0.5)
    bias = np.sign(ph["close"].to_numpy(float) - ph["open"].to_numpy(float))
    hb = cl.build_bars(m1, htf)
    h, l_ = hb["high"].to_numpy(float), hb["low"].to_numpy(float)
    h2, l2 = np.r_[np.nan, np.nan, h[:-2]], np.r_[np.nan, np.nan, l_[:-2]]
    bull, bear = l_ > h2, h < l2
    fi = np.flatnonzero(bull | bear)
    f_ct = _ns(hb["close_time"])[fi]
    f_lvl = np.where(bull[fi], l_[fi], h[fi])
    f_dir = np.where(bull[fi], 1, -1)
    hct = _ns(hb["close_time"])
    rows = []                                               # (day k, level, dir, formed_ns)
    Sn = S.asi8
    for k in range(len(S)):
        n_before = np.searchsorted(hct, Sn[k], side="right")   # HTF bars closed by S
        lo_pos = n_before - fvg_lookback
        sel = (fi >= lo_pos) & (fi < n_before)
        for j in np.flatnonzero(sel):
            rows.append((k, f_lvl[j], f_dir[j], f_ct[j]))
        for lvl, dr in ((ph["low"].iloc[k], 1), (ph["high"].iloc[k], -1)):
            if np.isfinite(lvl):
                rows.append((k, float(lvl), dr, -1))
    P = pd.DataFrame(rows, columns=["k", "level", "dir", "formed"])
    if P.empty:
        return {}
    side = np.where(P["dir"].to_numpy() > 0, "below", "above")
    Sk = pd.to_datetime(Sn[P["k"].to_numpy()], utc=True)
    Ek = pd.to_datetime(E.asi8[P["k"].to_numpy()], utc=True)
    unfilled = np.ones(len(P), bool)
    isf = P["formed"].to_numpy() >= 0
    for sd in ("above", "below"):
        m = isf & (side == sd)
        if m.any():
            unfilled[m] = ~cl.touch(pd.to_datetime(P["formed"].to_numpy()[m], utc=True),
                                    P["level"].to_numpy()[m], sd,
                                    until=Sk[m], m1=m1)["hit"].to_numpy()
    # a price already beyond the level at S (gap open) would 'tag' it at once; keep only
    # levels on the correct side of the day's opening price
    op = day_open[P["k"].to_numpy()]
    right_side = np.where(P["dir"].to_numpy() > 0, op > P["level"].to_numpy(),
                          op < P["level"].to_numpy())
    P = P[unfilled & right_side].reset_index(drop=True)
    side = np.where(P["dir"].to_numpy() > 0, "below", "above")
    if aligned:
        b = bias[P["k"].to_numpy()]
        P = P[P["dir"].to_numpy() == b].reset_index(drop=True)
        side = np.where(P["dir"].to_numpy() > 0, "below", "above")
    if cap is not None and len(P):
        P["dist"] = np.abs(day_open[P["k"].to_numpy()] - P["level"].to_numpy())
        P = (P.sort_values(["k", "dist"], kind="stable").groupby("k").head(cap)
             .sort_values(["k"], kind="stable").reset_index(drop=True))
        side = np.where(P["dir"].to_numpy() > 0, "below", "above")
    tag = np.full(len(P), np.iinfo(np.int64).max)
    Sk = pd.to_datetime(Sn[P["k"].to_numpy()], utc=True)
    Ek = pd.to_datetime(E.asi8[P["k"].to_numpy()], utc=True)
    for sd in ("above", "below"):
        m = side == sd
        if m.any():
            r = cl.touch(Sk[m], P["level"].to_numpy()[m], sd, until=Ek[m], m1=m1)
            ht = pd.DatetimeIndex(r["hit_time"])
            t_ = np.where(r["hit"].to_numpy(), ht.as_unit("ns").asi8 + 60_000_000_000,
                          np.iinfo(np.int64).max)
            tag[m] = t_
    out = {}
    for k, t_ in zip(P["k"].to_numpy(), tag):
        out.setdefault(Sn[k], []).append(t_)
    return {"days": Sn, "ends": E.asi8, "tags": out, "bias": bias}


def make_detect(reading: str):
    c = CFG[reading]

    def detect(m1: pd.DataFrame) -> pd.DataFrame:
        cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "tagged"]
        ev = cisd_book(m1, c["ltf"])
        if ev.empty:
            return pd.DataFrame(columns=cols)
        dp = day_pois(m1, c["htf"], c["fvg_lookback"], c["cap"], c["aligned"])
        if not dp:
            return pd.DataFrame(columns=cols)
        dn = _ns(ev["decision_time"])
        k = np.searchsorted(dp["days"], dn - 1, side="right") - 1      # day the bar closed in
        okd = (k >= 0) & (dn <= dp["ends"][np.clip(k, 0, None)])
        ev, dn, k = ev[okd].reset_index(drop=True), dn[okd], k[okd]
        tagged = np.array([any(t_ <= d for t_ in dp["tags"].get(dp["days"][kk], []))
                           for kk, d in zip(k, dn)], bool)
        if c["aligned"]:
            b = dp["bias"][k]
            keep = ev["direction"].to_numpy() == b
            ev, tagged = ev[keep].reset_index(drop=True), tagged[keep]
        out = pd.DataFrame({"decision_time": ev["decision_time"],
                            "available_at": ev["available_at"],
                            "direction": ev["direction"], "stop_px": ev["stop_px"],
                            "rr": 2.0, "tagged": tagged})
        return out

    return detect


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    for rd in which:
        c = CFG[rd]
        det = make_detect(rd)
        ev = cl.cache_frame(f"hpg_{rd}_{c['htf']}_{c['ltf']}_lb{c['fvg_lookback']}_cap{c['cap']}"
                            f"_al{c['aligned']}", lambda: det(cl.load_m1()))
        print(rd, "rows", len(ev), "tagged share", float(ev["tagged"].mean()))
        probe = cl.probe_lookahead(det, ev, lookback="20D")
        res = cl.gate_test(ev, "tagged", mask_available_at="decision_time",
                           max_hold=c["hold"], claim="+")
        show(res)
        rules_ = [
            f"baseline: {c['ltf']} CISD (series_open, 2/2, max_wait 3, min_series 1), decide "
            f"at the confirming close, enter next M1 open, stop at the protected swing, 2R, "
            f"hold {c['hold']}",
            f"POIs marked at the 18:00 NY day open: unfilled {c['htf']} three-bar FVGs formed "
            f"in the last {c['fvg_lookback']} {c['htf']} bars (near edge) + previous day's "
            "high/low; only levels on the far side of the day's open price",
            "tagged = an M1 bar after the day open trades to the level; known at that bar's "
            "close; gate = any marked POI tagged before the CISD decision the same day"]
        if rd == "b":
            rules_ += ["bias = previous day's candle direction; baseline keeps only "
                       "bias-aligned CISDs; POIs kept: aligned ones (support for bullish, "
                       "resistance for bearish), the 2 nearest to the day's open"]
        params = {"htf": c["htf"], "ltf": c["ltf"], "fvg_lookback_bars": c["fvg_lookback"],
                  "poi_cap": c["cap"], "bias_aligned": c["aligned"], "rr": 2.0,
                  "max_hold": c["hold"], "grid4h": "forex", "tag_edge": "near",
                  "pdx_min_coverage": 0.5}
        src = {"htf": "corpus: htf-poi-gate-before-ltf 'drop only to the paired timeframe: "
                      "4H POI -> 15m -> 1m, or 1H POI -> 5m'",
               "ltf": "corpus: htf-poi-gate-before-ltf (paired timeframe rule)",
               "fvg_lookback_bars": "declared-before-run: POIs from the last ~5 trading days "
                                    "(30 4H bars) / last day (24 1H bars)",
               "poi_cap": "corpus: htf-poi-gate-before-ltf 'Mark at most one or two points of "
                          "interest before the session' (reading b); none in reading a",
               "bias_aligned": "corpus: 'Each must be in line with the daily bias' (reading "
                               "b); bias = previous-candle direction, method_spec §2.3",
               "rr": PHASE3_SRC, "max_hold": HOLD_SRC,
               "grid4h": "phase3: forex 4H grid (locked default, carried as a knob)",
               "tag_edge": "declared-before-run: 'Reached' undefined; near edge",
               "pdx_min_coverage": "declared-before-run: README trap 6"}
        print(cl.write_result(CID, rd, res, operationalization={"rules": rules_,
                                                                "params": params},
                              params_source=src, script=__file__, probe=probe,
                              notes="Gate stamp = decision time: POIs are fixed at the day "
                                    "open and the tag is an M1 bar closed before the CISD "
                                    "decision."))
