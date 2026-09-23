"""breaker-block (contested) — batch entry_own_02b.

Canonical four-point reading (EcnwfvAOo0s / rXMVPUZPw4A / jSIFb06gawQ), 15m:
bearish = swing high H1, low L1, HIGHER swing high H2, then a CLOSE below L1 (the
lower low prints). Block = the contiguous run of down-close candles that made L1
(bodies). Entry on the first retest of the block's near edge, stop beyond the
block's extreme, fixed 2R. Bullish mirrors.

Reading a: trade_test of the bare pattern.
Reading b: gate_test — the host's hard requirement "must be used with a
higher-timeframe bias, don't pattern trade it": gate = trade direction agrees with
the daily previous-candle bias (method spec §2.3) of the last COMPLETED day.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                    # noqa: E402
from _common import M1, bars_with_swings, first_touch, to_ts, ONE_MIN, ns  # noqa: E402

TF = "15min"
LL_WAIT = 40
RETEST_WAIT = 20
RR = 2.0
MAX_HOLD = "5h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "bias_ok"]


def _run(o, c, i, bull_run_down: bool, max_len=10):
    """Contiguous opposing-close run producing the extreme at i (down-closes at a low)."""
    q = (lambda k: c[k] < o[k]) if bull_run_down else (lambda k: c[k] > o[k])
    end = i
    while end > 0 and not q(end):
        end -= 1
        if i - end > 2:
            return -1, -1
    if not q(end):
        return -1, -1
    s = end
    while s > 0 and q(s - 1) and end - s + 1 < max_len:
        s -= 1
    return s, end


def daily_bias(m1: pd.DataFrame) -> pd.DataFrame:
    """Previous-candle engine on NY-18:00 daily bars: +1/-1/0 known at each day's close."""
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] > 300]
    h, l, c = d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
    b = np.zeros(len(d), int)
    for i in range(1, len(d)):
        up, dn = h[i] > h[i - 1], l[i] < l[i - 1]
        if up and dn:
            continue
        if up:
            b[i] = 1 if c[i] > h[i - 1] else -1        # continuation vs reversal closure
        elif dn:
            b[i] = -1 if c[i] < l[i - 1] else 1
    return pd.DataFrame({"bias": b, "close_time": d["close_time"].to_numpy()}, index=d.index)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    if len(m1) < 500:
        return pd.DataFrame(columns=COLS)
    b, d = bars_with_swings(m1, TF, 2, 2)
    o, h, l, c, ct = d["o"], d["h"], d["l"], d["c"], d["ct"]
    n = len(h)
    m = M1(m1)
    bar_ns = np.int64(15) * ONE_MIN
    rows = []
    for bear in (True, False):
        piv = np.flatnonzero(d["sh"] if bear else d["sl"])
        for p1, p2 in zip(piv[:-1], piv[1:]):
            if p2 - p1 < 2:
                continue
            if bear and not h[p2] > h[p1]:
                continue
            if (not bear) and not l[p2] < l[p1]:
                continue
            seg = l[p1 + 1:p2] if bear else h[p1 + 1:p2]
            e = p1 + 1 + int(np.argmin(seg) if bear else np.argmax(seg))
            lvl1 = l[e] if bear else h[e]
            s, en = _run(o, c, e, bull_run_down=bear)
            if s < 0 or s <= p1:
                continue
            # 4th point: first close through L1 (H1) after H2, before H2 is exceeded
            k = -1
            for j in range(p2 + 1, min(n, p2 + 1 + LL_WAIT)):
                if (h[j] > h[p2]) if bear else (l[j] < l[p2]):
                    break
                if (c[j] < lvl1) if bear else (c[j] > lvl1):
                    k = j
                    break
            if k < 0:
                continue
            arm = max(k, p2 + 2)
            if arm >= n:
                continue
            if bear:
                edge = float(np.minimum(o[s:en + 1], c[s:en + 1]).min())   # body bottom
                stop = float(h[s:en + 1].max())
                if h[k + 1:arm + 1].max(initial=-np.inf) >= edge:
                    continue
            else:
                edge = float(np.maximum(o[s:en + 1], c[s:en + 1]).max())   # body top
                stop = float(l[s:en + 1].min())
                if l[k + 1:arm + 1].min(initial=np.inf) <= edge:
                    continue
            if (h[p2 + 1:arm + 1].max() > h[p2]) if bear else (l[p2 + 1:arm + 1].min() < l[p2]):
                continue
            a_ns = ct[arm]
            jj = first_touch(m, a_ns, a_ns + RETEST_WAIT * bar_ns, edge, not bear, cancel=None)
            if jj < 0:
                continue
            if (m.h[jj] >= stop) if bear else (m.l[jj] <= stop):
                continue
            rows.append((m.t[jj] + ONE_MIN, -1 if bear else 1, stop))
    if not rows:
        return pd.DataFrame(columns=COLS)
    out = pd.DataFrame(rows, columns=["t", "direction", "stop_px"])
    out = out.drop_duplicates(["t", "direction"]).sort_values("t").reset_index(drop=True)
    dec = to_ts(out["t"])
    db = daily_bias(m1)
    bz = cl.asof(db, dec)
    bias = bz["bias"].fillna(0).to_numpy()
    return pd.DataFrame({"decision_time": dec, "available_at": dec,
                         "direction": out["direction"].to_numpy(),
                         "stop_px": out["stop_px"].to_numpy(), "rr": RR,
                         "bias_ok": bias == out["direction"].to_numpy()})


OP = {"rules": [
    "15m bars; fractal swings 2/2",
    "bearish: consecutive swing highs H1 < H2; L1 = lowest low between them; then within 40 bars of H2 (and before "
    "H2 is exceeded) a 15m CLOSE below L1 = the lower low prints (bullish mirrors)",
    "block = contiguous run (<=10) of down-close candles that made L1 (up-close at H1 for bullish); zone near edge = "
    "body bottom (bearish) / body top (bullish); stop = the run's wick extreme",
    "armed at max(lower-low close, H2 confirmation); skip if the edge was retested before arming",
    "entry: first M1 trade into the edge within 20 x 15m bars; decide at that M1 close, enter next open; 2R; hold 5h",
    "reading b gate: trade direction == daily previous-candle bias of the last completed NY-18:00 day "
    "(took prior high & closed above / took prior low & closed back above = bull; mirrors = bear; both/inside = none)"],
    "params": {"tf": TF, "swing": "2/2", "ll_wait": LL_WAIT, "retest_wait": RETEST_WAIT, "rr": RR,
               "max_hold": MAX_HOLD, "zone": "body near edge, stop at wick extreme", "ctrl_tod_tol_min": 30,
               "daily_bias": "previous-candle engine, 18:00 NY day"}}
SRC = {"tf": "corpus: YAML timeframes ltf [15m, 5m] (xP-o11jRCyg / DUIhKL5v1uQ shown on intraday charts)",
       "swing": "phase3: locked fractal 2/2",
       "ll_wait": "declared-before-run: the lower low must print within 40 structure bars of H2",
       "retest_wait": "declared-before-run: first retest within 20 structure bars",
       "rr": "corpus: YAML measurable 'hit rate of a fixed 2R trade on first retest of the zone'",
       "max_hold": "declared-before-run: 20 structure bars",
       "zone": "corpus: EcnwfvAOo0s 'using the down close candles from the first high to the first low'; "
               "rXMVPUZPw4A 'lowest down close candle prior to the move'; stop 'beyond the block's extreme' (execution)",
       "ctrl_tod_tol_min": "declared-before-run: README trap 9",
       "daily_bias": "method_spec: §2.3 previous-candle engine; corpus EcnwfvAOo0s 'used with a higher timeframe bias, so don't pattern trade it'"}

if __name__ == "__main__":
    ev = cl.cache_frame("breaker_15m_ll40_rt20", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict(), ev["bias_ok"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD, ctrl_tod_tol_min=30)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail",
                                   "exposure_bars", "ties", "ctrl_overlap")})
    cl.write_result("breaker-block", "a", res, operationalization=OP, params_source=SRC,
                    script=__file__, probe=probe,
                    notes="Reading a: bare canonical 4-point breaker (H,L,HH,LL), first retest of body edge, 2R.")
    resb = cl.gate_test(ev, "bias_ok", mask_available_at="decision_time", max_hold=MAX_HOLD,
                        ctrl_tod_tol_min=30)
    print({k: resb.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail")})
    cl.write_result("breaker-block", "b", resb, operationalization=OP, params_source=SRC,
                    script=__file__, probe=probe,
                    notes="Reading b: gate = breaker direction agrees with the daily previous-candle bias (host's "
                          "'must be used with a HTF bias'); bias read from the last completed daily bar via cl.asof.")
