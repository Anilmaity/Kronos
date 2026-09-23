"""important-time-levels (TTrades own voice, contested) — two readings.

Six NY clock levels (18:00, 00:00, 08:30, 09:30, 10:00, 14:00) with three stated uses. The
two uses that make a trading claim are tested (declared before any run); the OHLC-framing
use (18:00/midnight frame the daily candle, 10:00/14:00 the 4h candle) is a charting
frame with no stated signal.

 a  trade_test — Judas swing / order block at the time level (EYzP7c24AwM "I also look for
    a Judas swing or an order block formation at midnight"; JZDI--Jm0bA "I'll use midnight,
    8:30, and 9:30"; shorts_02: "the opposing run at that time, once closed over, is the
    order block, and he then does not expect its low to be taken"). Levels: 00:00 and 08:30
    NY; 09:30 is dropped because the concept itself says gold/forex has no 09:30 open.
    On 5m bars starting in [L, L+60min), with O = open of the first M1 bar at L:
      bullish: the most recent down-close 5m bar whose low traded below O is the order
      block (the opposing run); the first later bar that CLOSES above that bar's high
      triggers a long. Bearish mirrored (up-close bar above O, close below its low).
      First trigger of either side wins, one trade per level per day.
    Entry next M1 open after the trigger close; stop = the extreme of the opposing run
    (lowest low / highest high since L, through the trigger bar) — "do not expect its low
    to be taken"; target 2R; exit after 50 min. Control = default matched random entries
    (timing is the claim, so time of day is NOT held fixed).

 b  gate_test — premium/discount markers (JZDI--Jm0bA "With the 8:30 and midnight open, I
    will consider premium or discount"; "bearish and above both = a deep premium; bullish
    and below both = the mirror"). Baseline: the batch 5m bare CISD book restricted to
    entries in [08:35, 17:00) NY (both opens known). Gate = short with the confirming close
    above BOTH the midnight and the 08:30 open, or long with it below both; complement =
    the other baseline entries in that span.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402

CID = "important-time-levels"
PA = {"levels": ["00:00", "08:30"], "tf": "5min", "search_min": 60, "rr": 2.0,
      "max_hold": "50min", "open_delay_max_min": 5, "day_open_hour": 18}
PB = {"span": ("08:35", "17:00"), "levels": ["00:00", "08:30"], "open_delay_max_min": 5}


# ── reading a ────────────────────────────────────────────────────────────────
def detect_a(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "level_min",
            "level_open"]
    b = cl.build_bars(m1, PA["tf"])
    if len(b) < 20:
        return pd.DataFrame(columns=cols)
    st = pd.DatetimeIndex(b.index)
    ct = pd.DatetimeIndex(b["close_time"])
    mod_b = cl.ny_minute_of_day(st)
    td_b = cl.trading_day(st, PA["day_open_hour"]).asi8
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    # the level's opening price = open of the first M1 bar in [L, L+5min)
    mod_m = cl.ny_minute_of_day(m1.index)
    td_m = cl.trading_day(m1.index, PA["day_open_hour"]).asi8
    rows = []
    for lv in PA["levels"]:
        L = int(lv[:2]) * 60 + int(lv[3:])
        sel = (mod_m >= L) & (mod_m < L + PA["open_delay_max_min"])
        op = pd.Series(m1["open"].to_numpy()[sel]).groupby(td_m[sel]).first()
        op_t = pd.Series(m1.index.asi8[sel]).groupby(td_m[sel]).first()
        inwin = (mod_b >= L) & (mod_b < L + PA["search_min"])
        idx = np.flatnonzero(inwin)
        if len(idx) == 0:
            continue
        # group consecutive in-window bars by trading day
        days = td_b[idx]
        for d in np.unique(days):
            if d not in op.index:
                continue
            O = float(op.loc[d])
            t_open = int(op_t.loc[d])
            ii = idx[days == d]
            ii = ii[st.asi8[ii] >= t_open - 0]          # bars at/after the level's open bar
            if len(ii) == 0:
                continue
            run_lo, run_hi = np.inf, -np.inf
            ob_bull, ob_bear = None, None             # (high) / (low) of the order block bar
            for j in ii:
                run_lo = min(run_lo, l[j])
                run_hi = max(run_hi, h[j])
                trig = 0
                if ob_bull is not None and c[j] > ob_bull:
                    trig = 1
                elif ob_bear is not None and c[j] < ob_bear:
                    trig = -1
                if trig:
                    stop = run_lo if trig == 1 else run_hi
                    if (trig == 1 and stop < c[j]) or (trig == -1 and stop > c[j]):
                        rows.append((ct[j], trig, stop, L, O))
                    break
                if c[j] < o[j] and l[j] < O:
                    ob_bull = h[j]
                if c[j] > o[j] and h[j] > O:
                    ob_bear = l[j]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "level_min",
                                     "level_open"])
    df["decision_time"] = pd.DatetimeIndex(df["decision_time"])
    df["available_at"] = df["decision_time"]
    df["rr"] = PA["rr"]
    return df[cols].sort_values(["decision_time", "direction"]).reset_index(drop=True)


# ── reading b ────────────────────────────────────────────────────────────────
def detect_b(m1):
    ev = C.cisd5(m1)
    cols = list(ev.columns) + ["px", "mid_open", "open_830", "pd_gate"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    t = pd.DatetimeIndex(ev["decision_time"])
    ev = ev[cl.in_window(t, *PB["span"])].reset_index(drop=True)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    t = pd.DatetimeIndex(ev["decision_time"])
    # confirming 5m close = close of the M1 bar that ends at decision_time
    pos = m1.index.get_indexer(t - pd.Timedelta(minutes=1))
    px = np.where(pos >= 0, m1["close"].to_numpy(float)[np.clip(pos, 0, None)], np.nan)
    mid = cl.open_at(t, "00:00", m1=m1, max_delay_min=PB["open_delay_max_min"])
    o83 = cl.open_at(t, "08:30", m1=m1, max_delay_min=PB["open_delay_max_min"])
    ev["px"] = px
    ev["mid_open"] = mid["price"].to_numpy(float)
    ev["open_830"] = o83["price"].to_numpy(float)
    ev = ev[np.isfinite(ev["px"]) & np.isfinite(ev["mid_open"]) &
            np.isfinite(ev["open_830"])].reset_index(drop=True)
    d = ev["direction"].to_numpy()
    above = (ev["px"] > ev["mid_open"]) & (ev["px"] > ev["open_830"])
    below = (ev["px"] < ev["mid_open"]) & (ev["px"] < ev["open_830"])
    ev["pd_gate"] = ((d == -1) & above) | ((d == 1) & below)
    return ev[cols]


def run_a():
    ev = cl.cache_frame(f"{CID}_a_{PA}", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev), ev["level_min"].value_counts().to_dict(),
          ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
    res = cl.trade_test(ev, max_hold=PA["max_hold"])
    op = {"rules": [
        "levels 00:00 and 08:30 NY (09:30 dropped for forex-class gold, per the concept); "
        "O = open of the first M1 bar in [L, L+5min)",
        "5m bars starting in [L, L+60min): bullish order block = most recent down-close bar "
        "whose low traded below O; trigger = first later 5m close above that bar's high; "
        "bearish mirrored; first trigger wins, one per level per day",
        "entry next M1 open after the trigger close; stop = lowest low (highest high) since L "
        "through the trigger bar; target 2R; time exit 50 min; default matched control"],
        "params": PA}
    src = {"levels": "corpus: EYzP7c24AwM 'I also look for a Judas swing or an order block "
                     "formation at midnight' / 'we don't really have the 930 open with Forex'; "
                     "JZDI--Jm0bA 'I'll use midnight, 8:30, and 9:30'",
           "tf": "declared-before-run: 5m bars (concept LTF list 15m/5m/1m; phase-3 5m stack)",
           "search_min": "declared-before-run: the Judas swing must resolve within 60 min of "
                         "the level",
           "rr": "phase3: 2R target (locked config)",
           "max_hold": "phase3: 10 entry-TF bars = 50 min on 5m",
           "open_delay_max_min": "declared-before-run: open_at default 5-minute tolerance",
           "day_open_hour": "session_window_fit: 18:00 NY daily roll"}
    notes = ("Order block = the opposing-run candle closed over (shorts_02 wording); the stop "
             "at the run extreme encodes 'do not expect its low to be taken'. No daily-bias "
             "filter (the bias source is a separate concept).")
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print("a", p)
    for k in ("n", "verdict", "verdict_detail", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi",
              "p", "mde", "ties", "exposure_bars", "halves", "sanity_flags"):
        print("  ", k, res.get(k))


def run_b():
    def build():
        m1 = cl.load_m1()
        base = C.base_cached()
        # reuse the cached baseline; apply the same pure gate logic as detect_b
        return _gate_from_base(base, m1)
    ev = cl.cache_frame(f"{CID}_b_{PB}", build)
    print("b events", len(ev), "gated", int(ev["pd_gate"].sum()))
    probe = cl.probe_lookahead(detect_b, ev, lookback="10D")
    res = cl.gate_test(ev, "pd_gate", mask_available_at="decision_time",
                       max_hold=C.BASE_MAX_HOLD, claim="+")
    op = {"rules": [
        "baseline: 5m bare CISD (series_open, 2/2, max_wait 3), stop = protected swing, 2R, "
        "50 min, restricted to entries in [08:35, 17:00) NY",
        "gate: short with the confirming 5m close above both the midnight (00:00) and the "
        "08:30 NY opens (deep premium), or long with it below both (deep discount); "
        "complement = the rest of that baseline"],
        "params": dict(C.BASE_PARAMS, **{k: (list(v) if isinstance(v, tuple) else v)
                                          for k, v in PB.items()})}
    src = dict(C.BASE_SRC,
               span="declared-before-run: from the first 5m close after the 08:30 open to the "
                    "17:00 NY daily break (both reference opens known)",
               levels="corpus: JZDI--Jm0bA 'With the 8:30 and midnight open, I will consider "
                      "premium or discount'",
               open_delay_max_min="declared-before-run: open_at default 5-minute tolerance")
    notes = "Premium/discount against both opens, used as an entry filter on 5m CISD."
    p = cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print("b", p)
    for k in ("n", "verdict", "verdict_detail", "diff", "ci_lo", "ci_hi", "p", "mde",
              "ties", "halves"):
        print("  ", k, res.get(k))


def _gate_from_base(base, m1):
    """Same as detect_b but starting from the cached full-data CISD frame."""
    orig = C.cisd5
    try:
        C.cisd5 = lambda _m: base.copy()
        return detect_b(m1)
    finally:
        C.cisd5 = orig


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    if "a" in which:
        run_a()
    if "b" in which:
        run_b()
