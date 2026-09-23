"""important-level — gate_test.

Concept: an entry pattern (order block / breaker / CISD) only counts if the candles that
form it traded INTO a pre-identified HIGHER-timeframe level before the validating close;
the same geometry at a random location does not qualify. Measurable (the YAML's own):
hit rate of entries WITH an HTF level vs WITHOUT.

Baseline book (stated): phase-3 rung-0 5m CISD (series_open, 2/2, max_wait 3), decide at
the confirming 5m close, enter next M1 open, stop = protected swing, 2R, 50 min. 5m is
paired with the 1H (method_spec §1.2), so the "higher timeframe" is the 1H, plus the
previous day's extreme.

Gate htf_level: between the start of the opposing series and the swing extreme, price
traded into at least one level known before the series began:
  (1) a 1H fair value gap of the trade's polarity (bullish gap for a long), formed (3rd
      bar closed) within the prior 72 h, not yet closed through (no 1H close beyond its
      far edge before the series), lying beyond the series' first open (price came to it),
      and reached: series extreme <= gap top (long) / >= gap bottom (short);
  (2) a 1H 2/2 swing low (long) / high (short), confirmed within the prior 72 h, untaken
      before the series (no 5m low below it between its confirmation and the series), and
      swept by the series extreme;
  (3) the previous trading day's low (long) / high (short), untaken earlier that day, swept
      by the series extreme.
("previous order block" from the continuation list is not implemented.)
claim '+': CISDs whose series traded into an HTF level beat those that did not.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (cl, np, pd, complete_bars, cisd_frame, empty, ns, fvg_arrays, swing_points,  # noqa: E402
                     OHLC, PHASE3_SRC, ONE_MIN)

CID = "important-level"
LTF, HTF = "5min", "1h"
RR = 2.0
HOLD = "50min"
LOOKBACK_H = 72
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "htf_level"]
H_NS = 3_600_000_000_000


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = complete_bars(cl.build_bars(m1, LTF), m1)
    hb = complete_bars(cl.build_bars(m1, HTF), m1)
    if len(b) < 40 or len(hb) < 10:
        return empty(COLS)
    ev = cisd_frame(b)
    if ev.empty:
        return empty(COLS)
    # ── 5m arrays
    bl, bh, bo = b["low"].to_numpy(float), b["high"].to_numpy(float), b["open"].to_numpy(float)
    bst = ns(b.index)
    # ── 1H FVGs: formed at 3rd bar close, invalidated at first later 1H close beyond far edge
    hh, hl, hc = hb["high"].to_numpy(float), hb["low"].to_numpy(float), hb["close"].to_numpy(float)
    hct = ns(hb["close_time"])
    bull, bear, glo, ghi = fvg_arrays(hh, hl)
    fv = []
    for pol, sel in ((1, bull), (-1, bear)):
        for i in np.flatnonzero(sel):
            fv.append((hct[i], i, glo[i], ghi[i], pol))
    fv = np.array(fv, dtype=float).reshape(-1, 5) if fv else np.zeros((0, 5))
    # ── 1H swings (confirmed at i+2 close)
    sw = swing_points(hb[OHLC], left=2, right=2)
    shp = np.flatnonzero(sw["swing_high"].to_numpy(bool))
    slp = np.flatnonzero(sw["swing_low"].to_numpy(bool))
    shp = shp[shp + 2 < len(hb)]
    slp = slp[slp + 2 < len(hb)]
    sh_t, sh_v = hct[shp + 2], hh[shp]
    sl_t, sl_v = hct[slp + 2], hl[slp]
    # ── previous day extreme and today's running extreme before the series
    s_start = pd.DatetimeIndex(ev["series_start"])
    pdx = cl.prior_hilo(s_start, "1D", m1=m1)
    run = cl.running_hilo(s_start, "1D", m1=m1)
    pdl, pdh = pdx["low"].to_numpy(float), pdx["high"].to_numpy(float)
    rlo, rhi = run["low"].to_numpy(float), run["high"].to_numpy(float)

    s0 = ns(s_start)
    gate = np.zeros(len(ev), bool)
    for r, (d, sp, ep, ext) in enumerate(zip(ev["sgn"].to_numpy(int), ev["s_pos"].to_numpy(int),
                                              ev["ext_pos"].to_numpy(int), ev["extreme_price"].to_numpy(float))):
        t0 = s0[r]
        first_open = bo[sp]
        hit = False
        # (1) 1H FVG of trade polarity
        if len(fv):
            m_ = (fv[:, 4] == d) & (fv[:, 0] <= t0) & (fv[:, 0] >= t0 - LOOKBACK_H * H_NS)
            if m_.any():
                kk = int(np.searchsorted(hct, t0, side="right")) - 1      # last 1H bar closed by t0
                for _, fi, lo_, hi_, _p in fv[m_]:
                    fi = int(fi)
                    closes = hc[fi + 1:kk + 1]
                    if (d > 0 and (closes < lo_).any()) or (d < 0 and (closes > hi_).any()):
                        continue                                           # closed through: no longer a gap
                    if (d > 0 and hi_ < first_open and ext <= hi_) or (d < 0 and lo_ > first_open and ext >= lo_):
                        hit = True
                        break
        # (2) 1H swing swept, untaken before the series
        if not hit:
            st_, sv_ = (sl_t, sl_v) if d > 0 else (sh_t, sh_v)
            m_ = (st_ <= t0) & (st_ >= t0 - LOOKBACK_H * H_NS)
            for tt, vv in zip(st_[m_], sv_[m_]):
                if (d > 0 and ext >= vv) or (d < 0 and ext <= vv):
                    continue
                a = np.searchsorted(bst, tt, side="left")
                seg = slice(a, sp)
                if a >= sp or (d > 0 and bl[seg].min() > vv) or (d < 0 and bh[seg].max() < vv):
                    hit = True
                    break
        # (3) previous day extreme swept, untaken earlier today
        if not hit:
            if d > 0 and np.isfinite(pdl[r]) and ext < pdl[r] and (not np.isfinite(rlo[r]) or rlo[r] > pdl[r]):
                hit = True
            if d < 0 and np.isfinite(pdh[r]) and ext > pdh[r] and (not np.isfinite(rhi[r]) or rhi[r] < pdh[r]):
                hit = True
        gate[r] = hit
    t = pd.DatetimeIndex(ev["conf_close_time"])
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": ev["sgn"].to_numpy(int),
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": RR, "htf_level": gate})
    return out[COLS]


OP = {"rules": [
    "baseline: 5m CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming close, enter next M1 open, "
    "stop = protected swing, 2R, 50 min",
    "gate htf_level = the series extreme traded into a level known when the series began: (1) a trade-polarity 1H FVG "
    "formed within 72h, not closed through, lying beyond the series' first open, reached (low <= gap top for longs); "
    "(2) a 1H 2/2 swing low/high confirmed within 72h, untaken on 5m bars until the series, swept by the extreme; "
    "(3) the previous trading day's low/high, untaken earlier in the day, swept by the extreme",
    "'previous order block' level type not implemented"],
    "params": {"ltf": LTF, "htf": HTF, "level_rule": "series_open", "swing": "2/2", "max_wait": 3, "rr": RR,
               "max_hold": HOLD, "lookback_h": LOOKBACK_H, "day_roll": "18:00 NY"}}
SRC = {"ltf": "method_spec §1.2: 1-hour structure pairs with the 5-minute entry",
       "htf": "method_spec §1.2 pairing; corpus: important-level.yaml examples use 'an hourly fair value gap'",
       "level_rule": PHASE3_SRC, "swing": PHASE3_SRC, "max_wait": PHASE3_SRC, "rr": PHASE3_SRC, "max_hold": PHASE3_SRC,
       "lookback_h": "method_spec §1.1: relevant-swing look-back = three higher-timeframe candles; hourly chart -> three days",
       "day_roll": "method_spec §1.4: daily open 18:00 NY (canon)"}


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_5m_1h", lambda: detect(cl.load_m1()))
    print(len(ev), ev["htf_level"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="15D")
    print("probe", probe["passed"])
    res = cl.gate_test(ev, "htf_level", mask_available_at="decision_time", max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "exposure_bars", "ties", "ctrl_overlap")})
    print(cl.write_result(CID, None, res, operationalization=OP, params_source=SRC, script=__file__, probe=probe,
                          notes=f"gate firing rate {ev['htf_level'].mean():.3f}"))
