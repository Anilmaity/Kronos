"""a-plus-entry-checklist — trade_test, two readings (contested: evolution of step 1).

Setup TF 5m, entry refined on M1. Bullish (bearish mirrored by negating prices):
 1. liquidity: reading a (canonical 0xygpCMwxbQ, HARD gate) — the leg's origin low
    runs the most recent confirmed 5m swing low (stop raid);
    reading b (earlier lpam8F-N3EM) — the raid OR the origin low trades into a
    completed 1H bullish FVG (the 'higher time frame reasoning' substitute).
 2. MSS with displacement: first 5m close above the most recent confirmed swing high,
    and the 4 bars ending at the break show displacement vs the 4 before them
    (range ratio >= 1.5 and travel beyond the high >= 0.65 x prior range).
 3. displacement range = origin low -> leg high (to the break bar); EQ = 0.5.
 4. an unmitigated bullish 5m FVG formed in the leg with its near edge below EQ
    (discount); the highest such gap.
 5. entry: first M1 trading into the gap's near edge within 2h of the break;
    stop = the gap's creating candle low (or the gap bottom if lower); target 2R.
All parameters declared before the first run.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, run_and_print  # noqa: E402
from detectors.primitives import swing_points, fair_value_gaps  # noqa: E402

TF = "5min"
HTF = "1h"
DISP_N, DISP_R, DISP_D = 4, 1.5, 0.65
ENTRY_WIN_M1 = 120       # the return must come within 2h of the break bar's close
HTF_FVG_LOOKBACK = pd.Timedelta("5D")
RR = 2.0
MAX_HOLD = "50min"       # 10 setup-TF bars


def _neg(df):
    return pd.DataFrame({"open": -df["open"], "high": -df["low"], "low": -df["high"],
                         "close": -df["close"]}, index=df.index)


def _bull_setups(b5, h1, m_t, m_lo, m_c, ct5):
    """Bullish setups on (possibly negated) 5m bars. Returns list of dicts."""
    o_, h, l, c = (b5[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n = len(b5)
    sw = swing_points(b5, 2, 2)
    shp = np.flatnonzero(sw["swing_high"].to_numpy())
    slp = np.flatnonzero(sw["swing_low"].to_numpy())
    fv = fair_value_gaps(b5)
    bull = fv["bullish_fvg"].to_numpy()
    glo, ghi = fv["gap_low"].to_numpy(float), fv["gap_high"].to_numpy(float)
    # 1H bullish FVGs (completion = 3rd bar close)
    hf = fair_value_gaps(h1)
    hsel = hf["bullish_fvg"].to_numpy()
    h_ct = cl.data.utc_ns(pd.DatetimeIndex(h1["close_time"]))[hsel]
    h_lo, h_hi = hf["gap_low"].to_numpy(float)[hsel], hf["gap_high"].to_numpy(float)[hsel]
    starts = cl.data.utc_ns(pd.DatetimeIndex(b5.index))
    rows = []
    for j in range(8, n):
        k = np.searchsorted(shp + 2, j - 1, side="right") - 1      # swing confirmed by bar j-1
        if k < 0:
            continue
        sp = shp[k]
        H = h[sp]
        if not (c[j] > H) or (j - 1 > sp and c[sp + 1:j].max() > H):
            continue
        # displacement magnitude on the 4 bars ending at the break vs the 4 before
        wlo, whi = l[j - 3:j + 1].min(), h[j - 3:j + 1].max()
        pre = h[j - 7:j - 3].max() - l[j - 7:j - 3].min()
        if pre <= 0 or (whi - wlo) / pre < DISP_R or (whi - H) / pre < DISP_D:
            continue
        seg = l[sp + 1:j + 1]
        if len(seg) == 0:
            continue
        o = sp + 1 + int(np.argmin(seg))
        RL = l[o]
        # (a) raid: most recent swing low confirmed before bar o, taken by bar o
        q = np.searchsorted(slp + 2, o - 1, side="right") - 1
        raid = bool(q >= 0 and RL < l[slp[q]])
        # (b) substitute: origin low trades into a completed 1H bullish FVG
        ts = starts[o]
        a0 = np.searchsorted(h_ct, ts - HTF_FVG_LOOKBACK.value, side="left")
        a1 = np.searchsorted(h_ct, ts, side="right")
        htf = bool(((h_lo[a0:a1] <= RL) & (RL <= h_hi[a0:a1])).any()) if a1 > a0 else False
        if not (raid or htf):
            continue
        LH = h[o:j + 1].max()
        eq = 0.5 * (RL + LH)
        best = None
        for kk in range(o + 2, j + 1):
            if not bull[kk] or ghi[kk] >= eq:
                continue
            if kk < j and l[kk + 1:j + 1].min() <= ghi[kk]:
                continue                                   # already mitigated
            if best is None or ghi[kk] > ghi[best]:
                best = kk
        if best is None:
            continue
        near = ghi[best]
        stop = min(glo[best], l[best - 1])
        # M1 entry scan after the break bar closes
        e0 = np.searchsorted(m_t, ct5[j], side="left")
        e1 = min(e0 + ENTRY_WIN_M1, len(m_t))
        if e0 >= e1:
            continue
        hit = np.flatnonzero(m_lo[e0:e1] <= near)
        if len(hit) == 0:
            continue
        e = e0 + hit[0]
        if m_c[e] <= stop:
            continue
        rows.append({"decision_time": m_t[e] + np.timedelta64(60, "s"), "stop_px": stop,
                     "raid": raid, "htf_fvg": htf, "near_edge": near,
                     "entry_ref": m_c[e], "eq": eq})
    return rows


def detect_all(m1: pd.DataFrame) -> pd.DataFrame:
    b5 = cl.build_bars(m1, TF)
    h1 = cl.build_bars(m1, HTF)
    ct5 = cl.data.utc_ns(pd.DatetimeIndex(b5["close_time"]))
    m_t = cl.data.utc_ns(pd.DatetimeIndex(m1.index))
    out = []
    for sgn in (1, -1):
        bb = b5[["open", "high", "low", "close"]]
        hh = h1[["open", "high", "low", "close"]].assign(close_time=h1["close_time"])
        if sgn == 1:
            m_lo, m_c = m1["low"].to_numpy(float), m1["close"].to_numpy(float)
        else:
            bb = _neg(bb)
            hh = _neg(hh).assign(close_time=h1["close_time"])
            m_lo, m_c = -m1["high"].to_numpy(float), -m1["close"].to_numpy(float)
        rows = _bull_setups(bb, hh, m_t, m_lo, m_c, ct5)
        df = pd.DataFrame(rows, columns=["decision_time", "stop_px", "raid", "htf_fvg",
                                         "near_edge", "entry_ref", "eq"])
        for col in ("stop_px", "near_edge", "entry_ref", "eq"):
            df[col] = sgn * df[col].astype(float)
        df["direction"] = sgn
        out.append(df)
    ev = pd.concat(out, ignore_index=True)
    ev["decision_time"] = cl.data.from_ns(ev["decision_time"].to_numpy())
    ev["available_at"] = ev["decision_time"]
    ev["raid"] = ev["raid"].astype(bool)
    ev["htf_fvg"] = ev["htf_fvg"].astype(bool)
    ev["rr"] = RR
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def detect_a(m1):
    ev = detect_all(m1)
    return ev[ev["raid"]].reset_index(drop=True)


def detect_b(m1):
    return detect_all(m1)


OP = [
    "5m bars (UTC-aligned), swings = 2/2 fractals used only after confirmation; mirrored for shorts",
    "MSS: first 5m close beyond the most recent confirmed swing high; displacement = the 4 bars ending at the break "
    "have range >= 1.5x and travel beyond the broken high >= 0.65x the range of the 4 bars before",
    "origin = the extreme of the leg between that swing high and the break; displacement range origin -> leg extreme",
    "PD array = the unmitigated 5m FVG formed in the leg whose near edge is in the discount (< 0.5 of the range); "
    "highest such gap",
    "entry = first M1 bar trading into the gap's near edge within 120 M1 bars after the break bar closes "
    "(decide at that M1 close, enter next M1 open); stop = min(gap far edge, creating candle's low); target 2R; "
    "time exit 50min"]
PARAMS = {"tf": TF, "disp_n": DISP_N, "disp_r": DISP_R, "disp_d": DISP_D, "entry_win_m1": ENTRY_WIN_M1,
          "rr": RR, "max_hold": MAX_HOLD, "stop": "creating candle / gap far edge"}
SRC = {"tf": "corpus: lpam8F-N3EM/0xygpCMwxbQ htf 15m/5m, ltf 1m -> 5m setup, M1 entry",
       "disp_n": "threshold_fits: displacement magnitude N=4 (grade B)",
       "disp_r": "threshold_fits: displacement range ratio r=1.5",
       "disp_d": "threshold_fits: displacement distance d=0.65",
       "entry_win_m1": "declared-before-run: the return into the gap must come within 2 hours of the break",
       "rr": "method_spec: §5.3 '2R is the floor' ('solid risk to reward' has no number in lpam8F-N3EM)",
       "max_hold": "phase3: 10 setup-TF bars (§1.13 convention)",
       "stop": "corpus: lpam8F-N3EM 'stop above the fair value gap, or on the candle that created it'; "
               "'i don't like using stops all the way to low'"}

if __name__ == "__main__":
    for rd, fn in (("a", detect_a), ("b", detect_b)):
        ev = cl.cache_frame(f"aplus_{rd}_v1", lambda: fn(cl.load_m1()))
        print(rd, len(ev), ev["direction"].value_counts().to_dict(),
              "raid", round(ev["raid"].mean(), 3), "htf", round(ev["htf_fvg"].mean(), 3))
        probe = cl.probe_lookahead(fn, ev, lookback="10D")
        print("probe", probe.get("passed"))
        res = cl.trade_test(ev, max_hold=MAX_HOLD)
        run_and_print(res)
        step1 = ("step 1 (reading a, canonical 0xygpCMwxbQ, hard gate): the origin extreme runs the most recent "
                 "confirmed 5m swing low/high" if rd == "a" else
                 "step 1 (reading b, earlier lpam8F-N3EM): the raid OR the origin extreme trades into a completed "
                 "1H FVG of the trade's direction formed within the prior 5 days")
        params = dict(PARAMS, **({"htf_fvg_lookback": "5D", "htf": HTF} if rd == "b" else {}))
        src = dict(SRC, **({"htf_fvg_lookback": "declared-before-run: a 1H gap from the last trading week",
                            "htf": "corpus: lpam8F-N3EM 'go into a higher time frame imbalance' -> 1H, the TF above the 15m/5m setup"}
                           if rd == "b" else {}))
        p = cl.write_result("a-plus-entry-checklist", rd, res,
                            operationalization={"rules": [step1] + OP, "params": params},
                            params_source=src, script=__file__, probe=probe,
                            notes="Partials ladder and the discretionary choice among FVG/OB/OTE/breaker are not "
                                  "tested; FVG is the first-preference PD array. Direction comes from the "
                                  "displacement leg (no daily bias filter).")
        print("wrote", p)
