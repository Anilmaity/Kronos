"""opposing-run -- update 2026-10-07 (TTrades live_06 draft, uW55Tuk-ngY).

New claim vs the library entry (prior reading = shallow-vs-large live 4h opposing run,
structure_own_04a/opposing-run.py): "Usually, when price has a deep opposing run like
this ... it's less likely to expand, but also you want to see another SMT, right? because
it's kind of hard to trust it when it runs deep like that."

The 'less likely to expand' half is the prior reading's complement (same partition) and
is not re-run. Only the NEW part is tested here:

u1007a (gate_test, claim '+'): among DEEP live opposing-run 4h candles (the prior
  reading's events with opposing_run / range-so-far > 0.30, i.e. NOT shallow), the ones
  that also show a gold/silver SMT at the opposing extreme do better, control-adjusted,
  than the deep ones without. SMT (classic two-asset divergence, candle level): within the
  candle's first 120 min exactly ONE of gold / silver (XAG H1) traded beyond its own
  previous-4h-candle extreme on the opposing side (low for a bullish-so-far candle, high
  for a bearish one).
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04a")
from _common import cl, np, pd, empty, to_ts, M1, LiveCandle, ONE_MIN, GRID_SRC  # noqa: E402

CID = "opposing-run"
TF = "4h"
GRID = "forex"
MID_MIN = 120
HOLD = "120min"
MIN_M1_FIRST_HALF = 60
CUT_RANGE = 0.30
XAG_PATH = "/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xag_h1_full.parquet"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "smt"]
ONE_H = 60 * ONE_MIN
_XAG = None


def xag_for(m1):
    global _XAG
    if _XAG is None:
        x = pd.read_parquet(XAG_PATH)
        x.index = pd.to_datetime(x.index, utc=True)
        x = x[["high", "low"]].astype(float).sort_index()
        _XAG = x[~x.index.duplicated(keep="first")]
    end = pd.DatetimeIndex(m1.index).max() + pd.Timedelta(minutes=1)
    start = pd.DatetimeIndex(m1.index).min().floor("1h")
    return _XAG[(_XAG.index >= start) & (_XAG.index + pd.Timedelta(hours=1) <= end)]


def win_ext(t, h, l, a, b):
    """max high / min low of rows with a <= t < b (per window); NaN if empty."""
    i0 = np.searchsorted(t, a, side="left")
    i1 = np.searchsorted(t, b, side="left")
    hi = np.full(len(a), np.nan)
    lo = np.full(len(a), np.nan)
    for k in np.flatnonzero(i1 > i0):  # ponytail: python loop, ~5k windows
        hi[k] = h[i0[k]:i1[k]].max()
        lo[k] = l[i0[k]:i1[k]].min()
    return hi, lo


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    if len(m1) < 300:
        return empty(COLS)
    m = M1(m1)
    lc = LiveCandle(m1, m, TF, GRID)
    st, ct = lc.bstart, lc.bclose
    tdec = st + MID_MIN * ONE_MIN
    keep = (tdec < ct) & (tdec <= m.t[-1] + ONE_MIN)
    keep[0] = False                                   # needs a previous candle in the slice
    tdec = tdec[keep]
    bidx = np.flatnonzero(keep)
    s = lc.at(tdec)
    n_first = (np.searchsorted(m.t + ONE_MIN, tdec, side="right")
               - np.searchsorted(m.t, st[bidx], side="left"))
    ok = s["ok"] & (s["bucket"] == bidx) & (n_first >= MIN_M1_FIRST_HALF)
    d = np.sign(s["price"] - s["open"])
    ok &= d != 0
    rng = s["hi"] - s["lo"]
    ok &= rng > 0
    opp = np.where(d > 0, s["open"] - s["lo"], s["hi"] - s["open"])
    deep = opp / np.where(rng > 0, rng, np.nan) > CUT_RANGE
    ok &= deep
    stop = np.where(d > 0, s["lo"], s["hi"])
    # previous 4h candle present in the data (gold from M1, silver from H1)
    pst, pct = st[bidx - 1], ct[bidx - 1]
    pgh, pgl = win_ext(m.t, m.h, m.l, pst, pct)
    x = xag_for(m1)
    xt = x.index.as_unit("ns").asi8 if hasattr(x.index, "as_unit") else x.index.asi8
    xh, xl = x["high"].to_numpy(float), x["low"].to_numpy(float)
    psh, psl = win_ext(xt, xh, xl, pst, pct)
    fsh, fsl = win_ext(xt, xh, xl, st[bidx], tdec - ONE_H + 1)  # H1 bars closed by tdec
    ok &= np.isfinite(pgh) & np.isfinite(psh) & np.isfinite(fsh)
    with np.errstate(invalid="ignore"):
        g_take = np.where(d > 0, s["lo"] < pgl, s["hi"] > pgh)
        x_take = np.where(d > 0, fsl < psl, fsh > psh)
    smt = g_take != x_take
    t = to_ts(tdec)
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": stop, "rr": np.nan, "smt": smt})[ok]
    out["direction"] = out["direction"].astype(int)
    out["smt"] = out["smt"].astype(bool)
    return out.reset_index(drop=True)[COLS]


RULES = [
    "every 4h candle (forex grid 17/21/01/05/09/13 NY); measure at candle open + 120 min from M1 bars closed by "
    "then (>= 60 of them); intended direction = sign(price - candle open); opposing run = open -> extreme against it",
    "keep only DEEP opposing runs: opposing_run / (high - low so far) > 0.30 (complement of the prior reading's "
    "shallow gate)",
    "baseline: enter next M1 open in that direction, stop = the opposing extreme so far, no target, exit at the "
    "candle's scheduled close (120 min clock)",
    "gate smt: within the candle's first 120 min exactly one of gold (M1) / silver (XAG_USD H1, the two H1 bars "
    "closed by the decision) traded beyond its own previous-4h-candle extreme on the opposing side (low if "
    "bullish-so-far, high if bearish-so-far); previous candle = the previous 4h bucket present in the data",
    "rows without silver H1 coverage in either window are dropped",
]
PARAMS = {"tf": TF, "grid4h": GRID, "mid_min": MID_MIN, "max_hold": HOLD, "hold_basis": "clock",
          "min_m1_first_half": MIN_M1_FIRST_HALF, "deep_cut_range": CUT_RANGE,
          "target": "none (time exit at candle close)", "correlate": "XAG_USD H1",
          "smt_level": "previous 4h candle opposing extreme", "smt_form": "symmetric (exactly one asset takes it)"}
SRC = {"tf": "corpus: prior reading opposing-run (structure_own_04a): YAML timeframes htf [1D, 4H, 1H]; same frame so only the SMT requirement differs",
       "grid4h": GRID_SRC,
       "mid_min": "declared-before-run: prior reading: measure live at half the candle's period (SlWxhzhLo3A 'we use almost half the time')",
       "max_hold": "declared-before-run: prior reading: to the candle's scheduled close - the expansion in question ('less likely to expand')",
       "hold_basis": "declared-before-run: prior reading: clock, the exit is the candle's own close time",
       "min_m1_first_half": "declared-before-run: prior reading: stub guard (README trap 6)",
       "deep_cut_range": "threshold_fits: prior reading cut_range 0.30 (threshold_fits small wick, grade C); draft ambiguity: '\"Deep\" is not quantified' -> deep := not shallow",
       "target": "corpus: prior reading: no target given for the expansion; time exit",
       "correlate": "corpus: uW55Tuk-ngY compares ES/YM (indices); for gold the campaign's correlate is silver (rVRk4MLTJSs 'I was using silver for this'), held at H1 only",
       "smt_level": "declared-before-run: uW55Tuk-ngY 'Do we have it as another SMT? Perfectly equalized' - SMT at the swing the opposing run made; the candle-level reference is the previous candle's extreme",
       "smt_form": "declared-before-run: classic SMT = one asset makes the new extreme, the other fails (uW55Tuk-ngY 'We have no sort of SMT off this high')"}


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_u1007a_deep_smt_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["smt"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe["passed"])
    res = cl.gate_test(ev, "smt", mask_available_at="decision_time", max_hold=HOLD, claim="+")
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "exposure_bars", "ties", "ctrl_overlap")})
    p = cl.write_result(CID, "u1007a", res, operationalization={"rules": RULES, "params": PARAMS},
                        params_source=SRC, script=__file__, probe=probe,
                        notes=f"gate firing rate {ev['smt'].mean():.3f} among deep-run candles. Tests only the "
                              "new 'deep run needs another SMT' requirement; 'less likely to expand' is the prior "
                              "reading's complement. Source SMT was ES/YM; silver H1 used as gold's correlate.")
    print(p)
