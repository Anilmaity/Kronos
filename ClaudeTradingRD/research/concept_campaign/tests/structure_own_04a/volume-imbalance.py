"""volume-imbalance — trade_test (a reactive level).

Concept: a volume imbalance between candle i and i+1 = close[i] != open[i+1] while the two
candles' high/low ranges overlap (price traded through the area); a GAP is the same with
no overlap. Zone = [close[i], open[i+1]]. He shows price returning to a VI and reacting
from it, so it is a reactive level (support below price / resistance above).

Operationalisation (15m):
  * VI at the i/i+1 boundary with ranges overlapping and |open[i+1] - close[i]| >=
    0.10 x ATR(20) (a size floor is required: "no minimum size, so ... nearly every
    candle boundary produces a volume imbalance");
  * polarity by the side price is on at candle i+1's close: close[i+1] above the zone ->
    the zone is support (long on return); below -> resistance (short); inside -> dropped;
  * entry: first M1 bar within 16 bars (4h) after i+1's close that trades back to the
    zone's near edge; decide at that M1 close, fill at the next M1 open;
  * stop = the zone's far edge -/+ 0.25 x ATR(20); skipped if the touching minute already
    reached the stop; target 2R; 150 min.
claim '+': the reaction off a VI beats a matched random entry.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, atr, complete_bars, empty, ns, to_ts, M1, ONE_MIN, PHASE3_SRC  # noqa: E402

CID = "volume-imbalance"
TF = "15min"
ATR_N = 20
MIN_SIZE_ATR = 0.10
RETEST = 16
STOP_BUF_ATR = 0.25
RR = 2.0
HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    if len(b) < ATR_N + 5:
        return empty(COLS)
    b = b.copy()
    b["atr"] = atr(b, ATR_N)
    b = complete_bars(b, m1)
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    a = b["atr"].to_numpy(float)
    ct = ns(b["close_time"])
    nb = len(b)
    gap = o[1:] - c[:-1]
    overlap = (l[1:] <= h[:-1]) & (h[1:] >= l[:-1])
    zlo = np.minimum(o[1:], c[:-1])
    zhi = np.maximum(o[1:], c[:-1])
    a1 = a[1:]                                   # ATR known at candle i+1's close
    c1 = c[1:]
    d = np.where(c1 > zhi, 1, np.where(c1 < zlo, -1, 0))
    sel = overlap & np.isfinite(a1) & (np.abs(gap) >= MIN_SIZE_ATR * a1) & (d != 0)
    m = M1(m1)
    rows = []
    for k in np.flatnonzero(sel):
        j = k + 1                                 # candle i+1, index in b
        s0 = ct[j]
        s1 = ct[j + RETEST] if j + RETEST < nb else m.t[-1] + ONE_MIN
        i0 = int(np.searchsorted(m.t, s0, side="left"))
        i1 = int(np.searchsorted(m.t, s1, side="left"))
        if i1 <= i0:
            continue
        dd = d[k]
        near = zhi[k] if dd > 0 else zlo[k]
        stop = zlo[k] - STOP_BUF_ATR * a1[k] if dd > 0 else zhi[k] + STOP_BUF_ATR * a1[k]
        seg = (m.l[i0:i1] <= near) if dd > 0 else (m.h[i0:i1] >= near)
        kk = np.flatnonzero(seg)
        if not len(kk):
            continue
        q = i0 + int(kk[0])
        if (dd > 0 and m.l[q] <= stop) or (dd < 0 and m.h[q] >= stop):
            continue
        rows.append((m.t[q] + ONE_MIN, dd, stop))
    if not rows:
        return empty(COLS)
    arr = np.array(rows, dtype=object)
    out = pd.DataFrame({"decision_time": to_ts(arr[:, 0].astype(np.int64)),
                        "direction": arr[:, 1].astype(int), "stop_px": arr[:, 2].astype(float), "rr": RR})
    out["available_at"] = out["decision_time"]
    out = out.drop_duplicates(subset=["decision_time", "direction"], keep="first")
    return out.sort_values("decision_time").reset_index(drop=True)[COLS]


OP = {"rules": [
    "15m bars; VI at boundary i/i+1: |open[i+1] - close[i]| >= 0.10 x ATR(20) (known at i+1 close) AND the two candles' "
    "high/low ranges overlap (a no-overlap boundary is a GAP, excluded); zone = [min, max] of close[i], open[i+1]",
    "polarity: close[i+1] above the zone -> support (long); below -> resistance (short); inside -> dropped",
    "entry: first M1 bar within 16 bars after i+1's close touching the zone's near edge; decide at that M1 close, "
    "enter next M1 open; skip if that minute already reached the stop",
    "stop = far edge -/+ 0.25 x ATR(20); target 2R; max hold 150 min; one trade per decision minute and direction"],
    "params": {"tf": TF, "atr_n": ATR_N, "min_size_atr": MIN_SIZE_ATR, "retest_bars": RETEST,
               "stop_buf_atr": STOP_BUF_ATR, "rr": RR, "max_hold": HOLD}}
SRC = {"tf": "corpus: volume-imbalance.yaml timeframes ltf [15m, 5m, 1m] (fractal)",
       "atr_n": "threshold_fits: ATR(20) is the campaign's scale unit (§1 barrier test)",
       "min_size_atr": "declared-before-run: corpus gives no minimum size; 0.10 ATR floor so tick-level boundary noise is excluded",
       "retest_bars": "declared-before-run: no expiry given; 16 bars (4h) for the first return",
       "stop_buf_atr": "declared-before-run: stop beyond the far edge by 0.25 ATR (no stop rule given for a VI)",
       "rr": PHASE3_SRC, "max_hold": PHASE3_SRC}


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_15m", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="15D")
    print("probe", probe["passed"])
    res = cl.trade_test(ev, max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "exposure_bars", "ties", "ctrl_overlap")})
    NOTE = ("CAVEAT (found after the first locked run; this identical re-run only attaches this note): events are "
            "concentrated in 2016-2018 (1,567/5,807/5,638 vs ~150-250 a year after 2020; H2 n=943). The M1 feed's "
            "15m open-vs-previous-close discontinuity has a median of ~0.10 in 2016-2018 against 0.02-0.05 later "
            "while the 15m range was ~1.0, so in that era most VIs are a FEED property, not market-made. The EDGE "
            "label is the locked rule's output; read it as feed-regime-dependent until reproduced post-2019 "
            "(H2 +0.036 with CI spanning 0).")
    print(cl.write_result(CID, None, res, operationalization=OP, params_source=SRC, script=__file__, probe=probe,
                          notes=NOTE))
