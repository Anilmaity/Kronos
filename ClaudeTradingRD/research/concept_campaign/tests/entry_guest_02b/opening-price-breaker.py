"""opening-price-breaker (guest: DexterLab) -> trade_test.

Reading (declared before the run):
  * PO3 candle = the daily candle; its time-opening price = the NY midnight open (his
    example 'the midnight open for a daily PO3'), the open of the first M1 in 00:00-00:05 NY.
    Working TF for the breaker: 15m (ltf list 15m/5m). Scan 00:00-17:00 NY.
  * Bullish (bearish mirrored): manipulation = price has traded below the midnight open
    since 00:00 (L2 = the lowest low since 00:00 up to and including the crossing bar).
    The breaker is 'in development' when a 15m bar closes back above the midnight open
    (previous 15m close at/below it). The low-high-low: H = the last confirmed 2/2 15m
    swing high of the trading day that formed BEFORE the L2 bar; the crossing close must
    also close above H's high (price trades through the breaker). Breaker zone = the H
    bar's range. Only the FIRST such crossing of the day (either side) is taken.
  * Execution: only breakers whose zone overlaps the midnight open ('the breaker zone
    overlapping the time opening'). Entry on the first retracement: a limit at the zone's
    top (H high), first M1 touch after the crossing bar closes, before 17:00 NY, not taken
    if L2 is traded at or before that minute.
  * Stop (not stated): beyond the manipulation extreme L2. Target: the 2.0 standard
    deviation of the manipulation leg projected from the open, open + 2 x (open - L2)
    (his first target '2 and 2.5 deviation'); dropped if not beyond the entry zone.
  * max_hold: until 17:00 NY, the end of the daily PO3 candle (per-row column).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import swing_points

TF = "15min"
SD = 2.0


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    empty = pd.DataFrame(columns=cols)
    b = cl.build_bars(m1, TF)
    if len(b) < 10:
        return empty
    ny = cl.to_ny(b.index)
    tday = (ny + pd.Timedelta("6h")).normalize()          # 18:00 roll -> calendar date of the midnight
    hr = ny.hour + ny.minute / 60.0
    # midnight open per date, from M1
    mny = cl.to_ny(m1.index)
    sel = (mny.hour == 0) & (mny.minute < 5)
    mo = pd.Series(m1["open"].to_numpy()[sel], index=mny[sel].normalize())
    mid_open = mo.groupby(level=0).first()
    sw = swing_points(b[["open", "high", "low", "close"]], left=2, right=2)
    shigh, slow = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    conf = sw["confirmed_at"].values
    O, H, L, C = (b[k].to_numpy() for k in ("open", "high", "low", "close"))
    starts = b.index.values
    ct = b["close_time"].values
    mt = m1.index.values
    MH, ML = m1["high"].to_numpy(), m1["low"].to_numpy()
    out = []
    td_codes, td_first = np.unique(tday.tz_localize(None).values, return_index=True)
    bounds = list(td_first) + [len(b)]
    for di, D in enumerate(td_codes):
        s, e = bounds[di], bounds[di + 1]
        Dts = pd.Timestamp(D).tz_localize("America/New_York")
        if Dts not in mid_open.index:
            continue
        op = float(mid_open.loc[Dts])
        mid_utc = Dts.tz_convert("UTC").to_datetime64()
        end_utc = (Dts + pd.Timedelta("17h")).tz_convert("UTC").to_datetime64()
        idx = np.arange(s, e)
        post = idx[(starts[idx] >= mid_utc) & (ct[idx] <= end_utc)]
        if len(post) < 2:
            continue
        run_lo, run_hi = np.inf, -np.inf
        lo_pos = hi_pos = -1
        for k in post:
            if L[k] < run_lo:
                run_lo, lo_pos = L[k], k
            if H[k] > run_hi:
                run_hi, hi_pos = H[k], k
            if k == 0:
                continue
            for d in (1, -1):
                if d == 1:
                    cross = C[k] > op and C[k - 1] <= op and run_lo < op
                    ext_pos, ext = lo_pos, run_lo
                    piv = shigh
                else:
                    cross = C[k] < op and C[k - 1] >= op and run_hi > op
                    ext_pos, ext = hi_pos, run_hi
                    piv = slow
                if not cross:
                    continue
                # last confirmed opposite swing of the trading day formed before the extreme bar
                cand = np.flatnonzero(piv[s:ext_pos]) + s
                cand = cand[conf[cand] <= starts[k]]
                ok = False
                if len(cand):
                    h = cand[-1]
                    zlo, zhi = L[h], H[h]
                    ok = (C[k] > zhi) if d == 1 else (C[k] < zlo)
                out_row = None
                if ok and zlo <= op <= zhi:
                    entry_px = zhi if d == 1 else zlo
                    tgt = op + SD * (op - ext)
                    if (tgt - entry_px) * d > 0:
                        a = np.searchsorted(mt, ct[k], side="left")
                        z = np.searchsorted(mt, end_utc, side="left")
                        if a < z:
                            hh, ll = MH[a:z], ML[a:z]
                            touch = (ll <= entry_px) if d == 1 else (hh >= entry_px)
                            beyond = (ll < ext) if d == 1 else (hh > ext)
                            if touch.any():
                                j = int(np.argmax(touch))
                                if not beyond[:j + 1].any():
                                    dt = pd.Timestamp(mt[a + j]).tz_localize("UTC") + pd.Timedelta("1min")
                                    hold = pd.Timestamp(end_utc).tz_localize("UTC") - dt
                                    if hold > pd.Timedelta(0):
                                        out_row = (dt, d, float(ext), float(tgt), hold)
                if out_row is not None:
                    out.append(out_row)
                break
            else:
                continue
            break                       # first crossing of the day decides the day
    if not out:
        return empty
    ev = pd.DataFrame(out, columns=["decision_time", "direction", "stop_px", "target_px", "max_hold"])
    ev["available_at"] = ev["decision_time"]
    return ev.sort_values("decision_time").reset_index(drop=True)[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("opbreaker_15m_midnight_sd2", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, hold_basis="bars")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "daily PO3; opening price = NY midnight open; 15m working bars between 00:00 and 17:00 NY",
        "first 15m close back through the midnight open after price traded beyond it (manipulation extreme L2 since 00:00)",
        "breaker = the day's last confirmed 2/2 opposite swing formed before L2; the crossing close must also clear it; zone = that swing bar's range",
        "trade only zones overlapping the midnight open; limit at the zone edge on the first retracement before 17:00 NY, not if L2 traded first",
        "stop beyond L2; target open + 2.0 x (open - L2); exit at 17:00 NY"],
        "params": {"tf": TF, "anchor": "00:00 NY", "swing": "2/2", "sd": SD,
                   "max_hold": "to 17:00 NY"}}
    src = {"tf": "corpus: wWIHS_dxbEY timeframes ltf 15m/5m -> 15m",
           "anchor": "corpus: wWIHS_dxbEY 'the midnight open for a daily PO3'",
           "swing": "phase3: 2/2 fractal swings (§1.8)",
           "sd": "corpus: wWIHS_dxbEY targets '2 and 2.5 deviation' -> first target 2.0; leg = open to manipulation extreme (declared-before-run)",
           "max_hold": "declared-before-run: the daily PO3 candle ends at the 17:00 NY close",
           "hold_basis": "declared-before-run: README trap 7 - first (clock) run showed exposure_bars real 848 vs control 765 (>10%), so hold in trading bars"}
    p = cl.write_result("opening-price-breaker", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Stop not stated by the guest: beyond the manipulation extreme (declared). First run used hold_basis=clock: UNDERPOWERED, diff +0.080 [-0.068,+0.228], but exposure_bars differed 848 vs 765 (trap 7), so re-run once with hold_basis=bars as the README directs.")
    print(p)
