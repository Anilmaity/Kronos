"""unicorn-model — trade_test (batch model_own_04a). Contested; two readings.

Unicorn = a breaker block overlapped by a same-polarity fair value gap left by the
displacement through the breaker; entry in the overlap, stop on the swept extreme.

Declared operationalisation (before run), 5-minute execution:
  * swings: three-candle fractal (method_spec §1.1), confirmed one bar later
  * bullish breaker (mirror for bearish): swing low L1 -> swing high H1 -> a lower
    swing low L2 (< L1: the stop hunt) -> the first 5m CLOSE above H1 (displacement
    through the breaker). H1 must be at most 48 bars (4h) old at the break,
    and L1 at most 48 bars before H1 (bounded search; set before any result was seen).
    Breaker candle = the last up-close candle between L1 and H1 (the last opposing-
    close candle before the sweeping leg); zone = its high-low range.
  * FVG: the first bullish 3-bar FVG whose third bar lies after L2 and no later than
    one bar after the break, overlapping the breaker zone in price (any overlap).
  * setup known at the close of the later of the break bar and the FVG's third bar;
    limit = the top of the overlap (the first price a retrace meets); filled by the
    first M1 bar trading to it within 60 min; decide at that bar's close, enter the
    next M1 open (the harness has no limit fills).
  * stop on the swept extreme L2; target 2R; max hold 50 min (10 entry bars).
reading a: the pattern alone (variant 2 definition), any time of day.
reading b: the Ash/TTrades entry function — setup confirmed at a session open,
  London 02:00-05:00 NY or New York 09:30-11:00 NY (daily bias / hourly area of
  interest omitted: the bias rule only covers price sitting at a daily FVG).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

MAX_AGE = 48
FILL_WAIT = pd.Timedelta(minutes=60)
MAX_HOLD = "50min"


def fractal(h, l):
    n = len(h)
    sh = np.zeros(n, bool)
    sl = np.zeros(n, bool)
    sh[1:-1] = (h[1:-1] > h[:-2]) & (h[1:-1] > h[2:])
    sl[1:-1] = (l[1:-1] < l[:-2]) & (l[1:-1] < l[2:])
    return sh, sl


def setups(O, H, L, C, d):
    """Return list of (break_idx, fvg_idx, zlo, zhi, gap_lo, gap_hi, stop) for one side.
    d=+1 bullish, d=-1 bearish (handled by mirroring prices)."""
    if d == -1:
        O, H, L, C = -O, -L, -H, -C
    sh, sl = fractal(H, L)
    n = len(H)
    out = []
    unbroken = []                                 # swing-high indices not yet closed above
    lows = []                                     # confirmed swing-low indices
    for j in range(2, n):
        i = j - 1                                  # swing at j-1 confirmed by bar j
        # bar j confirms swings at j-1; they may be used at j's close
        if sl[i]:
            lows.append(i)
        if sh[i]:
            unbroken.append(i)
        unbroken = [b for b in unbroken if j - b <= MAX_AGE]
        lows = [x for x in lows if j - x <= 2 * MAX_AGE]   # L1 within 48 bars of H1
        brk = [b for b in unbroken if C[j] > H[b]]
        if not brk:
            continue
        unbroken = [b for b in unbroken if b not in brk]
        b = max(brk)
        l1 = [x for x in lows if x < b]
        l2 = [x for x in lows if b < x < j]
        if not l1 or not l2:
            continue
        i1 = l1[-1]
        i2 = min(l2, key=lambda x: L[x])
        if not (L[i2] < L[i1]):
            continue
        up = [x for x in range(b, i1 - 1, -1) if C[x] > O[x]]
        if not up:
            continue
        k = up[0]
        zlo, zhi = L[k], H[k]
        for f in range(i2 + 2, min(j + 2, n)):
            if L[f] > H[f - 2]:
                glo, ghi = H[f - 2], L[f]
                if glo < zhi and ghi > zlo:
                    out.append((j, f, zlo, zhi, glo, ghi, L[i2]))
                    break
    if d == -1:
        out = [(j, f, -zhi, -zlo, -ghi, -glo, -st) for (j, f, zlo, zhi, glo, ghi, st) in out]
    return out


def detect(m1: pd.DataFrame, session_only: bool = False) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "setup_time",
            "in_session"]
    b = cl.build_bars(m1, "5min")
    if len(b) < 10:
        return pd.DataFrame(columns=cols)
    O, H, L, C = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"]).as_unit("ns").asi8
    mt = m1.index.as_unit("ns").asi8
    mh, ml = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    ONE = pd.Timedelta(minutes=1).value
    rows = []
    for d in (1, -1):
        for (j, f, zlo, zhi, glo, ghi, stop) in setups(O, H, L, C, d):
            last = max(j, f)
            if last >= len(ct):
                continue
            T = ct[last]
            lvl = min(ghi, zhi) if d == 1 else max(glo, zlo)
            a = np.searchsorted(mt, T, side="left")
            z = np.searchsorted(mt, T + FILL_WAIT.value, side="left")
            for u in range(a, min(z, len(mt))):
                if (d == 1 and ml[u] <= stop) or (d == -1 and mh[u] >= stop):
                    break
                if (d == 1 and ml[u] <= lvl) or (d == -1 and mh[u] >= lvl):
                    rows.append((mt[u] + ONE, d, stop, T))
                    break
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "setup_time"])
    out["decision_time"] = pd.to_datetime(out["decision_time"], utc=True)
    out["setup_time"] = pd.to_datetime(out["setup_time"], utc=True)
    out["available_at"] = out["decision_time"]
    out["rr"] = 2.0
    st = out["setup_time"]
    out["in_session"] = (cl.in_window(st, "02:00", "05:00") | cl.in_window(st, "09:30", "11:00"))
    out = (out.sort_values(["decision_time", "setup_time", "direction"], kind="stable")
              .drop_duplicates(["decision_time", "direction"], keep="first"))
    if session_only:
        out = out[out["in_session"]]
    return out[cols].reset_index(drop=True)


def detect_b(m1):
    return detect(m1, session_only=True)


PARAMS = {"entry_tf": "5min", "swing": "1/1 fractal", "max_h1_age_bars": MAX_AGE,
          "max_l1_before_h1_bars": MAX_AGE,
          "breaker_zone": "last up-close candle between L1 and H1, full range",
          "fvg_window": "after L2 to one bar after the break", "overlap": "any",
          "limit": "top of overlap", "fill_wait": "60min", "stop": "swept extreme L2",
          "rr": 2.0, "max_hold": MAX_HOLD}
SRC = {"entry_tf": "corpus: unicorn-model 'the entry function is read on the 5-minute at a session open'",
       "swing": "method_spec: §1.1 three-candle fractal",
       "max_h1_age_bars": "declared-before-run: four hours of 5m bars between H1 and the break",
       "max_l1_before_h1_bars": "declared-before-run: four hours of 5m bars between L1 and H1",
       "breaker_zone": ("corpus: rXMVPUZPw4A 'it is a high low higher high lower low'; unicorn-model "
                        "'Mark the last opposing-close candle before the sweeping leg'"),
       "fvg_window": "corpus: unicorn-model 'the displacement leg through the breaker leaves the gap'",
       "overlap": "corpus: unicorn-model ambiguity ''Overlapping'' is not quantified - any overlap",
       "limit": "declared-before-run: the first price inside the overlap a retrace meets",
       "fill_wait": "declared-before-run: twelve 5m bars",
       "stop": "corpus: unicorn-model execution 'On the swept extreme (2.3R in his example)'",
       "rr": "corpus: unicorn-model measurable 'hit rate of the fixed 2R target versus the breaker stop'",
       "max_hold": "phase3: 10 entry-TF bars (§1.13)"}


def run(reading):
    fn = detect if reading == "a" else detect_b
    ev = cl.cache_frame(f"unicorn_5m_{reading}", lambda: fn(cl.load_m1()))
    print(reading, "events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(fn, ev, lookback="10D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    params = dict(PARAMS)
    src = dict(SRC)
    rules = ["5m 3-candle swings; bullish: L1 -> H1 -> L2 < L1 (stop hunt) -> first close above H1",
             "breaker = last up-close candle from H1 back to L1 (full range); unicorn = first "
             "bullish FVG formed after L2 (to one bar past the break) overlapping it",
             "limit at the top of the overlap, filled by the first M1 bar reaching it within 60 "
             "min; decide at that bar's close, enter next M1 open; stop at L2; 2R; 50 min hold",
             "mirror for bearish"]
    if reading == "b":
        params["session_windows"] = "02:00-05:00, 09:30-11:00 NY (setup confirmation time)"
        src["session_windows"] = ("corpus: unicorn-model precondition 'It is a session open - London "
                                  "02:00 EST or New York 09:30'; window ends from KILLZONES "
                                  "fx_london end 05:00 and ix_ny_am end 11:00")
        rules.append("only setups confirmed 02:00-05:00 or 09:30-11:00 New York")
    p = cl.write_result("unicorn-model", reading, res,
                        operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes=("Daily bias and the hourly area of interest are not applied (the "
                               "concept's bias rule only covers price at a daily FVG)."))
    print(p)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print("  ", k, res.get(k))


if __name__ == "__main__":
    for r in sys.argv[1:] or ["a", "b"]:
        run(r)
