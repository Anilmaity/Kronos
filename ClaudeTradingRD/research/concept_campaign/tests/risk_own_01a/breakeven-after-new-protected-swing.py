"""breakeven-after-new-protected-swing — is a NEW protected swing a sound place to trail to?

The rule: stops move ONLY to new protected swings (a POI engaged, then closed through —
exactly what a CISD creates, spec §3.8 / §4.2); break-even is the same rule when that
swing sits at entry. Bounds: do not trail beyond 50% of the current higher-timeframe
candle's range; trail only when the draw is distant (not when the target is ~2R).

The harness has fixed stops only, so the stop MOVE is tested as the position it creates:
at the moment a new protected swing forms in the trade's favour, the trade that remains
is "hold from here, stop at the new swing, target the original draw". The concept's claim
("a trail target must be a protected swing"; "how often price returns to the trailed
protected swing") is that this swing is a real invalidation — so the remaining position
should beat a matched random entry with the same stop and target distances.
claim '+'.

Book:
  * base trades: phase-3 1h CISD entries (next M1 open after the confirming close, stop at
    the protected swing) whose draw — the previous trading day's high (long) / low
    (short) — is >= 2R away (the 'distant draw' precondition for trailing at all);
    target = the draw; life = 10h.
  * trail event: the FIRST later 1h CISD in the same direction, confirmed while the base
    trade is still open (neither its stop nor its draw touched on M1 up to that close),
    whose protected swing is beyond the base stop (a genuine trail) and not beyond 50% of
    the current trading day's running range (HTF = 1D for 1h entries, §1.2).
  * scored position: decision = that CISD's close, stop = the new protected swing,
    target = the base draw, max_hold = what is left of the base trade's 10h.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl, np, pd, cisd_raw, utc_ns, first_open_at_or_after, PHASE3_SRC  # noqa: E402

CID = "breakeven-after-new-protected-swing"
LIFE = pd.Timedelta("10h")


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    b, ev = cisd_raw(m1, "1h")
    if ev is None:
        return pd.DataFrame(columns=cols)
    d = pd.DatetimeIndex(ev["decision_time"])
    dn = utc_ns(d).astype(np.int64)
    s = ev["direction"].to_numpy()
    stop = ev["stop_px"].to_numpy()
    close = ev["close_px"].to_numpy()
    ph = cl.prior_hilo(d, "1D", m1=m1, min_coverage=0.5)
    draw = np.where(s > 0, ph["high"].to_numpy(float), ph["low"].to_numpy(float))
    run = cl.running_hilo(d, "1D", m1=m1)
    mid = 0.5 * (run["high"].to_numpy() + run["low"].to_numpy())
    pe, E = first_open_at_or_after(m1, d)
    hi, lo = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    tn = utc_ns(m1.index).astype(np.int64)
    risk = s * (E - stop)
    base_ok = np.isfinite(draw) & np.isfinite(E) & (risk > 0) & (s * (draw - E) >= 2 * risk)
    life = LIFE.value
    rows = []
    for i in np.flatnonzero(base_ok):
        # later same-direction CISDs within the base trade's life
        j0 = np.searchsorted(dn, dn[i], side="right")
        j1 = np.searchsorted(dn, dn[i] + life, side="left")
        for j in range(j0, j1):
            if s[j] != s[i]:
                continue
            if not (s[i] * (stop[j] - stop[i]) > 0):          # must be a genuine trail
                continue
            if not np.isfinite(mid[j]) or s[i] * (stop[j] - mid[j]) > 0:
                continue                                      # beyond 50% of the day's range
            if not (s[i] * (close[j] - stop[j]) > 0):
                continue
            # base trade still open: M1 bars that closed by d_j
            q = np.searchsorted(tn, dn[j], side="left")        # bars starting < d_j
            a = pe[i]
            if q > a:
                if s[i] > 0:
                    dead = (lo[a:q].min() <= stop[i]) or (hi[a:q].max() >= draw[i])
                else:
                    dead = (hi[a:q].max() >= stop[i]) or (lo[a:q].min() <= draw[i])
                if dead:
                    break                                     # closed before any trail
            rows.append((d[j], s[i], stop[j], draw[i], pd.Timedelta(dn[i] + life - dn[j], "ns")))
            break
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px",
                                      "max_hold"])
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"])
    out["available_at"] = out["decision_time"]
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("be_newps_cisd1h_pdh_trail", lambda: detect(cl.load_m1()))
    print("trail events", len(ev), "median hold left", ev["max_hold"].median())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, claim="+")
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde",
                                   "verdict", "verdict_detail", "ties", "exposure_bars",
                                   "ctrl_overlap", "drop")})
    op = {"rules": [
        "base: 1h CISD (series_open, 2/2 swings, max_wait 3), entry next M1 open, stop at "
        "the protected swing, draw = previous trading day's high/low >= 2R away, life 10h",
        "trail: first later same-direction 1h CISD confirmed while the base trade is open "
        "(stop and draw untouched on M1 until that close), new protected swing beyond the "
        "base stop and not beyond 50% of the trading day's running range",
        "scored: decision at that CISD close, stop = new protected swing, target = base "
        "draw, max_hold = remaining base life"],
        "params": {"tf": "1h", "htf_mid_cap": 0.5, "draw": "PDH/PDL", "min_room_R": 2.0,
                   "life": "10h", "min_coverage": 0.5}}
    src = {"tf": PHASE3_SRC, "life": PHASE3_SRC,
           "htf_mid_cap": "method_spec §5.5: do not trail past 50% of the current HTF candle",
           "draw": "method_spec §1.2 rule 1 + §5.2 item 1",
           "min_room_R": "method_spec §5.5: do not trail when the target is ~2R; trail with "
                         "a distant draw (declared: draw >= 2R at entry)",
           "min_coverage": "declared-before-run: skip stub sessions (README trap 6)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="The stop move is tested as the position it leaves (stop at "
                              "the new protected swing, original draw), vs random entries "
                              "with the same geometry; the harness cannot modify a stop "
                              "mid-trade, so a direct trailed-vs-untrailed comparison in "
                              "original-R units is not expressible.")
    print("wrote", p)
