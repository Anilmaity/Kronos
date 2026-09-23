"""mitigation-block — contested; two TTrades-voice readings, both as trade_test.

reading a (NgFIza9qsGQ, older 'Education - ICT' candle-level definition, used as a
  trend-continuation entry): in an aggressive bearish trend an UP-close candle prints;
  when a later candle trades below its LOW it becomes a mitigation block and its HIGH
  must not be invalidated. Entry option B: limit at the block's OPENING price on the
  retest; stop just beyond the block high; target the trend objective (2R). Claim '+'.
  (Option A, a limit at the block HIGH with the stop 'just beyond the high', has no
  stop distance and cannot be scored; option C needs 15s/30s data we do not have.)

reading b (bbWPoajy2MY 'Mitigation Blocks Simplified' + yRmKkR4CojU): the four-point
  failure-swing sequence with NO sweep. Bullish: L1, H1, L2 > L1, then a close above
  H1. Zone = the up-close candle at the failure swing H1 (bearish mirror: down-close
  candle at L1). He states he generally does NOT trade these because the unswept
  failure swings are liquidity and price tends to run through the block, so the
  concept's own claim about a plain retest entry is that it underperforms: claim '-'.
  Entry: limit at the zone body edge nearest price (the up-close candle's close for a
  bullish block) on the retest; stop beyond the candle's far extreme; 2R target.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402

import _batch_common as bc    # noqa: E402
from _batch_common import cl  # noqa: E402

CID = "mitigation-block"
RR = 2.0
MAX_HOLD = "150min"
BREAK_BARS = 16        # a later candle must trade through the candle's extreme within 16 bars
LIVE_BARS = 16         # the retest limit stays live 16 bars (4h) after the block forms
B_BREAK_WAIT = 20      # reading b: close beyond H1 within 20 bars of L2's confirmation
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]
TD = pd.Timedelta(minutes=bc.TF_MIN)


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    b = bc.bars(m1)
    if len(b) < 50:
        return bc.empty(COLS)
    legs = bc.displacement_legs(b)
    tdir, _, _ = bc.trend_state(b, legs)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    n = len(b)
    rows = []
    for j in np.flatnonzero(((tdir == -1) & (c > o)) | ((tdir == 1) & (c < o))):
        d = tdir[j]
        end = min(n, j + 1 + BREAK_BARS)
        if d == -1:
            brk = np.flatnonzero(l[j + 1:end] < l[j])
        else:
            brk = np.flatnonzero(h[j + 1:end] > h[j])
        if len(brk) == 0:
            continue
        k = j + 1 + int(brk[0])
        # the block's far extreme must not have been invalidated by a CLOSE before it formed
        seg = c[j + 1:k + 1]
        if (d == -1 and (seg > h[j]).any()) or (d == 1 and (seg < l[j]).any()):
            continue
        rows.append((j, k, d, o[j], h[j] if d == -1 else l[j]))
    if not rows:
        return bc.empty(COLS)
    r = pd.DataFrame(rows, columns=["j", "k", "d", "lvl", "stop"])
    start = ct[r["k"].to_numpy()]
    until = start + LIVE_BARS * TD
    hit, dt = bc.touch_sided(m1, start, r["lvl"].to_numpy(), r["d"].to_numpy(), until)
    r = r[hit].assign(dt=dt[hit])
    ev = pd.DataFrame({"decision_time": pd.DatetimeIndex(r["dt"]),
                       "available_at": pd.DatetimeIndex(r["dt"]),
                       "direction": r["d"].to_numpy(), "stop_px": r["stop"].to_numpy(),
                       "rr": RR})
    # several blocks can fill on the same minute: keep the most recent block (last j)
    ev = ev.iloc[::-1]
    return bc.finish(ev)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    b = bc.bars(m1)
    if len(b) < 50:
        return bc.empty(COLS)
    is_sh, is_sl = bc.swing_arrays(b)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    n = len(b)
    R = bc.SW_R
    sh_pos = np.flatnonzero(is_sh)
    sl_pos = np.flatnonzero(is_sl)
    rows = []
    for d, second, first_opp, ext_hi in ((1, sl_pos, sh_pos, True), (-1, sh_pos, sl_pos, False)):
        # bullish: second = L2 (swing low), first_opp = H1 (swing high) before it, L1 before H1
        for p2 in second:
            ih = np.searchsorted(first_opp, p2) - 1
            if ih < 0:
                continue
            p_h1 = first_opp[ih]
            i1 = np.searchsorted(second, p_h1) - 1
            if i1 < 0:
                continue
            p1 = second[i1]
            if d == 1:
                if not (l[p2] > l[p1]):          # higher low: NO sweep of L1
                    continue
                lvl1 = h[p_h1]
            else:
                if not (h[p2] < h[p1]):          # lower high: NO sweep
                    continue
                lvl1 = l[p_h1]
            begin = p2 + R + 1                    # after L2 is confirmed
            end = min(n, begin + B_BREAK_WAIT)
            if begin >= n:
                continue
            seg = c[begin:end]
            q = np.flatnonzero(seg > lvl1) if d == 1 else np.flatnonzero(seg < lvl1)
            if len(q) == 0:
                continue
            kq = begin + int(q[0])
            # structural break must not have happened already between H1 and L2's confirmation
            mid = c[p_h1 + 1:begin]
            if (d == 1 and (mid > lvl1).any()) or (d == -1 and (mid < lvl1).any()):
                continue
            # zone: the opposing... the up-close (bullish) / down-close (bearish) candle at
            # the failure swing, searched from the swing bar back two bars
            zc = -1
            for z in range(p_h1, max(-1, p_h1 - 3), -1):
                if (d == 1 and c[z] > o[z]) or (d == -1 and c[z] < o[z]):
                    zc = z
                    break
            if zc < 0:
                continue
            lvl = c[zc]                           # body edge facing the retest
            stop = l[zc] if d == 1 else h[zc]
            if (d == 1 and not lvl > stop) or (d == -1 and not lvl < stop):
                continue
            rows.append((kq, d, lvl, stop))
    if not rows:
        return bc.empty(COLS)
    r = pd.DataFrame(rows, columns=["k", "d", "lvl", "stop"]).sort_values("k", kind="stable")
    start = ct[r["k"].to_numpy()]
    until = start + LIVE_BARS * TD
    hit, dt = bc.touch_sided(m1, start, r["lvl"].to_numpy(), r["d"].to_numpy(), until)
    r = r[hit].assign(dt=dt[hit])
    ev = pd.DataFrame({"decision_time": pd.DatetimeIndex(r["dt"]),
                       "available_at": pd.DatetimeIndex(r["dt"]),
                       "direction": r["d"].to_numpy(), "stop_px": r["stop"].to_numpy(),
                       "rr": RR})
    return bc.finish(ev)


COMMON_SRC = {
    "tf": "corpus: mitigation-block.yaml timeframes htf 15m/5m; phase3 primary entry TF",
    "swing": "phase3: locked 2/2 fractal",
    "rr": "method_spec: §5.3 2R floor/fixed target stands in for 'the trend's objective'",
    "max_hold": "phase3: 10 entry-TF bars (§1.13)",
    "live_bars": "declared-before-run: the retest limit is live 16 bars (4h) after the block forms",
}


def run_a():
    ev = cl.cache_frame("mitblock_a_15m_open_retest", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev))
    probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    show(res)
    op = {"rules": [
        "15m bars; aggressive trend exactly as cheat-code-entry (fired displacement: close "
        "beyond latest 2/2 swing + threshold_fits 4-bar magnitude gate; 24-bar life; dies on "
        "a close beyond the leg origin)",
        "candidate: an opposing-close candle inside the live trend (up-close in a bearish trend)",
        "block forms when a later candle (within 16 bars) trades beyond the candidate's "
        "near extreme (its LOW for bearish), with no close beyond its far extreme before that",
        "entry: first M1 touch of the block's OPENING price after the forming bar closes "
        "(limit emulated: decide at that M1 close, fill at next M1 open), live 16 bars",
        "stop at the block's far extreme (high for shorts), no buffer; target 2R; exit 150 min",
        "same-minute fills from several blocks: keep the most recent block"],
        "params": {"tf": bc.TF, "swing": "2/2", "disp_N": bc.DISP_N, "disp_r": bc.DISP_R,
                   "disp_d": bc.DISP_D, "trend_bars": bc.TREND_BARS,
                   "break_bars": BREAK_BARS, "live_bars": LIVE_BARS, "entry_level": "block open",
                   "stop_buffer": 0.0, "rr": RR, "max_hold": MAX_HOLD}}
    src = dict(COMMON_SRC)
    src.update({
        "disp_N": "threshold_fits: displacement magnitude gate default N=4",
        "disp_r": "threshold_fits: displacement magnitude gate default r=1.5",
        "disp_d": "threshold_fits: displacement magnitude gate default d=0.65",
        "trend_bars": "declared-before-run: aggressive trend lifetime 24 bars",
        "break_bars": "declared-before-run: the break of the candle's low must come within 16 bars",
        "entry_level": "corpus: NgFIza9qsGQ 'When price is more clustered together here, I will use the opening price.' (option B)",
        "stop_buffer": "declared-before-run: 'just beyond the high' = the high itself"})
    return cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                           script=__file__, probe=probe,
                           notes="Reading a = older candle-level TTrades definition, option B "
                                 "(opening-price retest). Option A (limit AT the high with the stop "
                                 "just beyond it) has ~zero risk and cannot be scored; option C "
                                 "(15s/30s model) needs sub-minute data. " + "CAVEAT (post-verdict diagnostic, verdict NOT changed): the differential is concentrated in the smallest stops. By stop/ATR96(15m range) quintile the diff was Q1..Q5 +0.051/+0.013/+0.036/+0.009/+0.001R (weaker concentration than cheat-code-entry; p=0.03 is marginal). A pure-noise book (random direction at random 15m closes, stop at the just-closed candle's extreme, 2R, 150 min; n=58,539, n_boot=500, not written) also came back EDGE (+0.026R [+0.013,+0.039]), +0.14R in its smallest-stop quintile: the matched control places the same stop DISTANCE at an arbitrary level, while these books put it at a recent candle extreme, which M1 noise reaches less often. Treat this EDGE as a stop-geometry artefact candidate, not a trend-entry edge.")


def run_b():
    ev = cl.cache_frame("mitblock_b_15m_failswing_retest", lambda: detect_b(cl.load_m1()))
    print("b events", len(ev))
    probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, claim="-")
    show(res)
    op = {"rules": [
        "15m bars, 2/2 swings. Bullish: swing low L1, swing high H1 after it, swing low L2 "
        "after H1 with L2 > L1 (no sweep); after L2 is confirmed, a close above H1 within 20 "
        "bars (no close above H1 between H1 and L2's confirmation). Bearish mirrors.",
        "zone: the up-close candle at the failure swing H1 (the swing bar or up to 2 bars "
        "before it); bearish: the down-close candle at L1",
        "entry: first M1 touch back to the zone candle's close (the body edge facing the "
        "retest) within 16 bars after the breaking close; decide at that M1 close",
        "stop at the zone candle's far extreme; target 2R; exit 150 min",
        "claim '-': the speaker does not trade these because price runs through them"],
        "params": {"tf": bc.TF, "swing": "2/2", "break_wait": B_BREAK_WAIT,
                   "live_bars": LIVE_BARS, "entry_level": "zone candle close",
                   "rr": RR, "max_hold": MAX_HOLD}}
    src = dict(COMMON_SRC)
    src.update({
        "break_wait": "declared-before-run: the H1 close-through must come within 20 bars of L2's confirmation",
        "entry_level": "declared-before-run: wick-vs-body marking is 'explicitly left to the user' (bbWPoajy2MY); body edge chosen"})
    return cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                           script=__file__, probe=probe,
                           notes="Reading b = four-point failure swing with no sweep "
                                 "(bbWPoajy2MY / yRmKkR4CojU). No SMT filter: the endorsed SMT "
                                 "variant needs a correlated instrument the harness does not carry, "
                                 "so this is the plain block he says he does not trade (claim '-').")


def show(res):
    for k in ["n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "verdict",
              "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "dropped"]:
        print(" ", k, res.get(k))


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        print(run_a())
    if "b" in which:
        print(run_b())
