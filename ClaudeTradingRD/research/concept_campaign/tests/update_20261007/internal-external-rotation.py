"""internal-external-rotation, update_20261007_edu_03 (TTrades own voice, vMq1l8Zzzjw).

NEW claim only (prior readings a/b, 2026-09-23, guest/Short rotation without a C2 gate,
are untouched): the FVG <-> swing rotation is traded only after a CANDLE 2 CLOSURE at the
level; after a reversal at internal liquidity the external target is "always simply going
to be the swing low that made the swing high" (mirror); and trading "from fair value gaps
inside the higher time frame trend towards external liquidity" is easier than "trading that
retracement or reversal back into the range".

Source definitions (vMq1l8Zzzjw): internal = FVG, "the wick of candle one does not overlap
with the wick of candle three"; external = swing point, "a candle with a lower high on each
side" (3-bar fractal, method_spec §1.1). C2 test = method_spec §3.2 (bearish: high > prior
high AND close < prior high). TF 1h: his example 2, "We now have internal liquidity here on
the hourly chart". Only C2 (the draft notes C3 is mentioned but never shown).

Legs (1h bars, everything known at bar j's close, entry next M1 open):
  leg 1 INTERNAL -> EXTERNAL (with trend). Bar j is a bearish C2 whose high reaches into an
    active bearish FVG (formed by bar <= j-1, not closed through, not already used by a C2)
    and does not close above it. Short; stop = C2 high (the protected swing); target = the
    most recent confirmed 3-bar swing low before C2 (= the swing low that made the swing
    high), still untaken through bar j and below the close, within 72 bars. Mirror bullish.
  leg 2 EXTERNAL -> INTERNAL (retracement). Bar j is a bearish C2 that trades above an
    untaken confirmed swing high (<= 72 bars old). Short; stop = C2 high; target = the top
    (near edge) of the nearest bullish FVG below that no bar has traded into yet. Mirror.

  u1007a  trade_test on leg 1 (C2 gate + 'swing that made the swing' target).
  u1007b  gate_test on legs 1+2 pooled, gate = leg 1 (with-trend preference, claim '+').
Bars that fire both directions, or both legs in one direction, are dropped (ambiguous).
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                   # noqa: E402
from detectors.primitives import swing_points             # noqa: E402

CID = "internal-external-rotation"
READ = sys.argv[1] if len(sys.argv) > 1 else "u1007a"
assert READ in ("u1007a", "u1007b")
TF, LB, MAX_HOLD = "1h", 72, "600min"
OHLC = ["open", "high", "low", "close"]
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "with_trend"]


def detect_legs(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    h, l, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    n = len(b)
    sw = swing_points(b[OHLC], left=1, right=1)
    is_sh, is_sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    rows = []
    sh, sl = [], []                 # untaken swings [i, level]       (leg 2 trigger)
    last_sh = last_sl = -1          # most recent confirmed swing      (leg 1 target)
    bf, rf = [], []                 # active FVGs [k, bottom, top, touched]
    for j in range(1, n):
        i = j - 1                   # 3-bar swing at i is confirmed by the close of i+1 = j
        if i >= 1:
            if is_sh[i]:
                sh.append([i, h[i]]); last_sh = i
            if is_sl[i]:
                sl.append([i, l[i]]); last_sl = i
        k = j - 1                   # FVG whose third bar k closed before bar j
        if k >= 2:
            if l[k] > h[k - 2]:
                bf.append([k, h[k - 2], l[k], False])
            if h[k] < l[k - 2]:
                rf.append([k, h[k], l[k - 2], False])
        sh = [s for s in sh if s[0] >= j - LB]
        sl = [s for s in sl if s[0] >= j - LB]
        bf = [f for f in bf if f[0] >= j - LB]
        rf = [f for f in rf if f[0] >= j - LB]

        bear_c2 = h[j] > h[j - 1] and c[j] < h[j - 1]
        bull_c2 = l[j] < l[j - 1] and c[j] > l[j - 1]
        if bear_c2:
            at = [f for f in rf if h[j] >= f[1] and c[j] <= f[2]]
            if at:
                s = last_sl
                if s >= 0 and j - s <= LB and l[s + 1:j + 1].min() >= l[s] and l[s] < c[j]:
                    rows.append((j, -1, h[j], l[s], True))
                rf = [f for f in rf if all(f is not a for a in at)]       # one C2 per FVG
            if any(h[j] > s[1] for s in sh):
                tg = [f[2] for f in bf if not f[3] and f[2] < l[j]]
                if tg:
                    rows.append((j, -1, h[j], max(tg), False))
        if bull_c2:
            at = [f for f in bf if l[j] <= f[2] and c[j] >= f[1]]
            if at:
                s = last_sh
                if s >= 0 and j - s <= LB and h[s + 1:j + 1].max() <= h[s] and h[s] > c[j]:
                    rows.append((j, 1, l[j], h[s], True))
                bf = [f for f in bf if all(f is not a for a in at)]
            if any(l[j] < s[1] for s in sl):
                tg = [f[1] for f in rf if not f[3] and f[1] > h[j]]
                if tg:
                    rows.append((j, 1, l[j], min(tg), False))
        # bar j updates the pools: taken swings leave, FVGs closed through leave, touches mark
        sh = [s for s in sh if h[j] <= s[1]]
        sl = [s for s in sl if l[j] >= s[1]]
        bf = [f for f in bf if c[j] >= f[1]]
        rf = [f for f in rf if c[j] <= f[2]]
        for f in bf:
            f[3] = f[3] or l[j] <= f[2]
        for f in rf:
            f[3] = f[3] or h[j] >= f[1]
    if not rows:
        return pd.DataFrame({k: pd.Series(dtype="float64") for k in COLS})
    r = pd.DataFrame(rows, columns=["j", "direction", "stop_px", "target_px", "with_trend"])
    r["decision_time"] = pd.DatetimeIndex(b["close_time"].to_numpy()[r["j"].to_numpy()]).tz_convert("UTC")
    r["available_at"] = r["decision_time"]
    # ambiguous bars: both directions, or both legs in one direction -> drop all rows of that bar
    amb = r.groupby("j")["direction"].transform("size") > 1
    r = r[~amb]
    return r[COLS].sort_values("decision_time").reset_index(drop=True)


def detect_a(m1):
    ev = detect_legs(m1)
    return ev[ev["with_trend"].astype(bool)].drop(columns="with_trend").reset_index(drop=True)


def detect_b(m1):
    ev = detect_legs(m1)
    ev["with_trend"] = ev["with_trend"].astype(bool)
    return ev


if __name__ == "__main__":
    det = detect_a if READ == "u1007a" else detect_b
    ev = cl.cache_frame(f"iextrot_{READ}_1h_c2_lb72", lambda: det(cl.load_m1()))
    print(READ, "events", len(ev), ev["direction"].value_counts().to_dict())
    if READ == "u1007b":
        print("with_trend share", ev["with_trend"].mean())
    probe = cl.probe_lookahead(det, ev, lookback="20D")
    print("probe", probe.get("passed"))
    if READ == "u1007a":
        res = cl.trade_test(ev, max_hold=MAX_HOLD, hold_basis="bars")
    else:
        res = cl.gate_test(ev, "with_trend", mask_available_at="decision_time",
                           max_hold=MAX_HOLD, hold_basis="bars")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "halves", "gated", "fire_rate"):
        if k in res:
            print(k, res.get(k))

    rules = [
        "1h bars (18:00 NY day roll). External = 3-bar fractal swing (a high with a lower high "
        "each side, mirror), known at the close of its right-hand bar. Internal = 3-bar wick "
        "FVG known at its third bar's close; active until a close beyond its far edge, until a "
        "C2 has fired at it, or 72 bars old",
        "C2 (method_spec §3.2): bearish high[j] > high[j-1] AND close[j] < high[j-1]; mirror. "
        "C3 closures not used",
        "leg 1 (internal -> external): bearish C2 whose high reaches an active bearish FVG and "
        "closes not above its top -> short at the close (next M1 open), stop = C2 high, target = "
        "the most recent confirmed swing low before C2 (the swing low that made the swing high), "
        "untaken through C2, below the close, <= 72 bars old; mirror",
        "leg 2 (external -> internal): bearish C2 that trades above an untaken confirmed swing "
        "high (<= 72 bars) -> short, stop = C2 high, target = top of the nearest bullish FVG "
        "below that no bar has traded into (bar j included); mirror",
        "bars firing both directions or both legs are dropped; exit at stop/target or after "
        "600 trading M1 bars",
    ]
    rules.append("u1007a: trade_test on leg 1 only" if READ == "u1007a" else
                 "u1007b: gate_test on legs 1+2, gate = leg 1 (with-trend FVG -> external), "
                 "complement = leg 2 (retracement back into the range), claim '+'")
    op = {"rules": rules,
          "params": {"tf": TF, "swing": "1/1 (3-bar fractal)", "fvg": "3-bar wick gap",
                     "c2_test": "high>prior high & close<prior high (mirror)",
                     "closure": "C2 only", "target_leg1": "most recent swing before C2",
                     "target_leg2": "near edge of nearest untouched opposite FVG",
                     "stop": "C2 extreme", "lookback_bars": LB,
                     "fvg_life": "until closed through / used by one C2 / 72 bars",
                     "grid4h": "n/a (1h only)", "max_hold": MAX_HOLD, "hold_basis": "bars"}}
    src = {"tf": "corpus: vMq1l8Zzzjw example 2 'We now have internal liquidity here on the hourly chart'; declared-before-run",
           "swing": "corpus: vMq1l8Zzzjw 'we have a candle with a lower high on each side' (3-bar fractal, method_spec §1.1)",
           "fvg": "corpus: vMq1l8Zzzjw 'the wick of candle one does not overlap with the wick of candle three'",
           "c2_test": "method_spec: §3.2 C2 test (bearish high[i]>high[i-1] AND close[i]<high[i-1]); corpus vMq1l8Zzzjw 'a candle two closure at a fair value gap'",
           "closure": "declared-before-run: draft ambiguity - C3 closure mentioned, only C2 cases shown; claim names C2",
           "target_leg1": "corpus: vMq1l8Zzzjw 'always simply going to be the swing low that made the swing high'",
           "target_leg2": "corpus: vMq1l8Zzzjw 'reach back up into that fair value gap' -> near edge; 'a mitigated FVG is no longer the draw' (library rule)",
           "stop": "method_spec: §5 stop is the protected swing = C2's extreme",
           "lookback_bars": "corpus: relevant-swing-lookback 'hourly chart -> three days' (method_spec §1.1)",
           "fvg_life": "declared-before-run: his example 1 has the C2 one candle AFTER the first reach into the FVG, so a touched FVG stays active until closed through (IFVG test) or used",
           "grid4h": "declared-before-run: no 4h bars read",
           "max_hold": "phase3: 10 entry-TF periods hold convention",
           "hold_basis": "declared-before-run: README trap 7 - 10h holds cross halts"}
    if READ == "u1007b":
        op["params"]["gate"] = "leg 1 vs leg 2"
        src["gate"] = ("corpus: vMq1l8Zzzjw 'easier time trading from fair value gaps inside the higher "
                       "time frame trend' vs 'that retracement or reversal back into the range'")
    p = cl.write_result(CID, READ, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="New-claim reading (update_20261007_edu_03); prior readings a/b untouched. "
                              "Entry/stop at the C2 close/extreme: a stop at a fresh candle extreme is the "
                              "campaign's known stop-placement confound (Concept Campaign lesson 1), and cost "
                              "is the harness default, so read any differential with that in mind.")
    print(p)
