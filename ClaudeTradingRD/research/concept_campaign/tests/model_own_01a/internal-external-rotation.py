"""internal-external-rotation — Internal to External Range Liquidity Rotation (contested, mixed voice).

Claim ('+'): "when price sweeps external liquidity and CANNOT displace through it, it is
likely to reach back for internal liquidity; once it respects that fair value gap and
closes away, the expectation is a move back to external liquidity."
External = swing highs/lows (2/2 fractal); internal = unmitigated fair value gaps
(3-bar, wicks). Both legs are traded as stated (execution: 'at the internal array once
external has been taken' / 'toward whichever pool has not been delivered to'):

  a  EXTERNAL -> INTERNAL. A 1h bar trades above an untaken, confirmed swing high and
     CLOSES back below it (fails to displace; displacement = a close beyond the level,
     threshold_fits §2 grade A). Short at that close; stop = the sweep bar's high
     (beyond the array); target = the near edge (top) of the NEAREST unmitigated bullish
     FVG below the close. Mirror for swing lows. No FVG -> no trade (State A 'if none
     exists, hold and wait').
  b  INTERNAL -> EXTERNAL. A 1h bar trades into an unmitigated bullish FVG and CLOSES back
     above its top (respects it, closes away, no close through = no inversion). Long at
     that close; stop = the FVG's far edge (beyond the array); target = the NEAREST
     untaken confirmed swing high above. Mirror for bearish FVGs. No swing -> no trade.

Timeframe 1h (a working timeframe in the concept's ltf list). Swings and FVGs are
considered for 72 bars (relevant-swing-lookback: 'hourly chart -> three days'). A swing
is usable only after its right-hand bar closed; an FVG after its third bar closed.
Time exit after 10 bars (phase3 hold convention).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01a")
from _common import cl, np, pd, OHLC, swing_points  # noqa: E402

READ = sys.argv[1] if len(sys.argv) > 1 else "a"
LB = 72
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px"]


def detect(m1):
    h = cl.build_bars(m1, "1h")
    o, hi, lo, c = (h[k].to_numpy(float) for k in OHLC)
    n = len(h)
    sw = swing_points(h[OHLC], left=2, right=2)
    is_sh, is_sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    rows = []
    sh, sl = [], []            # active swings: [i, level]
    bf, rf = [], []            # active FVGs: [k, gap_low, gap_high]  (bullish / bearish)
    for j in range(n):
        # admit swings confirmed by the close of bar j-1 (swing at i known at close of i+2)
        i = j - 3
        if i >= 2:
            if is_sh[i]:
                sh.append([i, hi[i]])
            if is_sl[i]:
                sl.append([i, lo[i]])
        # admit FVGs whose third bar is j-1 (known at its close)
        k = j - 1
        if k >= 2:
            if lo[k] > hi[k - 2]:
                bf.append([k, hi[k - 2], lo[k]])
            if hi[k] < lo[k - 2]:
                rf.append([k, hi[k], lo[k - 2]])
        # expire by lookback
        sh = [s for s in sh if s[0] >= j - LB]
        sl = [s for s in sl if s[0] >= j - LB]
        bf = [f for f in bf if f[0] >= j - LB]
        rf = [f for f in rf if f[0] >= j - LB]

        if READ == "a":
            up = [s[1] for s in sh if hi[j] > s[1]]
            if up and c[j] < max(up):
                below = [f[2] for f in bf if f[2] < c[j]]
                if below:
                    rows.append((j, -1, hi[j], max(below)))
            dn = [s[1] for s in sl if lo[j] < s[1]]
            if dn and c[j] > min(dn):
                above = [f[1] for f in rf if f[1] > c[j]]
                if above:
                    rows.append((j, 1, lo[j], min(above)))
        else:
            tag_b = [f for f in bf if lo[j] <= f[2] and c[j] > f[2]]
            if tag_b:
                f = max(tag_b, key=lambda z: z[2])
                tg = [s[1] for s in sh if s[1] > c[j]]
                if tg:
                    rows.append((j, 1, f[1], min(tg)))
            tag_r = [f for f in rf if hi[j] >= f[1] and c[j] < f[1]]
            if tag_r:
                f = min(tag_r, key=lambda z: z[1])
                tg = [s[1] for s in sl if s[1] < c[j]]
                if tg:
                    rows.append((j, -1, f[2], max(tg)))
        # update state with bar j: taken swings and mitigated FVGs leave the pool
        sh = [s for s in sh if hi[j] <= s[1]]
        sl = [s for s in sl if lo[j] >= s[1]]
        bf = [f for f in bf if lo[j] > f[2]]
        rf = [f for f in rf if hi[j] < f[1]]
    if not rows:
        return pd.DataFrame(columns=COLS)
    r = np.array(rows, dtype=float)
    jj = r[:, 0].astype(int)
    ct = pd.DatetimeIndex(h["close_time"].iloc[jj])
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": r[:, 1].astype(int), "stop_px": r[:, 2],
                         "target_px": r[:, 3]})


ev = cl.cache_frame(f"iextrot_{READ}_1h", lambda: detect(cl.load_m1()))
print(READ, "events", len(ev), ev["direction"].value_counts().to_dict())
probe = cl.probe_lookahead(detect, ev, lookback="10D")
print("probe", probe.get("passed"))
res = cl.trade_test(ev, max_hold="600min", hold_basis="bars")
for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
          "ties", "exposure_bars", "ctrl_overlap", "halves"):
    print(k, res.get(k))

if READ == "a":
    rules = ["1h bars; external = 2/2 fractal swing high/low, usable after its right bar "
             "closed, untaken, swing bar within the last 72 bars",
             "event: bar trades beyond one or more such swing highs and closes back below the "
             "highest swept one (mirror lows)",
             "internal = bullish FVG (low[k] > high[k-2]) known at bar k's close, no later bar "
             "has traded into its top, within 72 bars; target = top of the nearest one below "
             "the close (mirror: bottom of nearest bearish FVG above)",
             "short at the close (next M1 open); stop = sweep bar high; exit after 600 trading M1 bars"]
else:
    rules = ["1h bars; internal = unmitigated FVG within 72 bars, known after its third bar closed",
             "event: bar trades into a bullish FVG (low <= its top) and closes above its top "
             "(respected, closed away); mirror bearish",
             "external = 2/2 fractal swing, untaken, within 72 bars; target = nearest one beyond "
             "the close in the trade direction",
             "long at the close (next M1 open); stop = FVG far edge; exit after 600 trading M1 bars"]
op = {"rules": rules,
      "params": {"tf": "1h", "swing": "2/2", "lookback_bars": LB, "fvg": "3-bar wick gap",
                 "displacement_test": "close beyond the level", "max_hold": "600min",
                 "hold_basis": "bars"}}
src = {"tf": "corpus: internal-external-rotation timeframes ltf [1H, 15m, 5m]; 1H declared-before-run",
       "swing": "corpus: internal-external-rotation 'swing highs (high with a lower high each side)' / phase3 2/2",
       "lookback_bars": "corpus: relevant-swing-lookback 'hourly chart -> three days' (method_spec §1.1)",
       "fvg": "method_spec: §3.9 FVG measured on the wicks",
       "displacement_test": "threshold_fits: §2 displacement structural gate = a close beyond the level (grade A)",
       "max_hold": "phase3: 10 entry-TF periods hold convention",
       "hold_basis": "declared-before-run: README trap 7 — 10h holds cross halts"}
p = cl.write_result("internal-external-rotation", READ, res, operationalization=op,
                    params_source=src, script=__file__, probe=probe,
                    notes="The two readings are the two legs of the rotation, each traded as a "
                          "standalone entry; the premium/discount 'dealing range' refinement (no "
                          "selection rule in the corpus) is not applied.")
print(p)
