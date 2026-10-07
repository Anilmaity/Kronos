"""upper-half-eq-expansion-filter (TTrades update 2026-10-07, live Q&A 9H15ZZvaKPQ) — gate_test, 2 readings.

New claim only (prior readings __a/__b tested 'next candle's low/close holds the daily EQ'):
  u1007a  1m-swing evidence: the upper half of the HTF candle "holds" only if a 1-minute swing
          forms inside that half ("Needs to form a one minute swing in this area ... Otherwise,
          this fails").
          Book: 15m candle P closes in direction d (+1 bullish / -1 bearish); next 15m candle N
          closes in direction d too. Decide at N's close, trade d, stop = N's low (bull) / high
          (bear), 2R, hold 10 x 15m = 150min.
          Gate: inside N, an M1 strict 3-bar swing low (bull) whose low lies in P's upper half
          [EQ_P, P.high] (bear mirror: swing high in [P.low, EQ_P]); both fractal neighbours are
          at/before N's last minute, so known at N's close.
  u1007b  candle-order tell: after a bearish expansion 5m candle A that closes in its low, the
          next candle B should "go lower first, take out the previous candle's low, and then"
          react bullishly; "pointed its upper wick first which is more bearish".
          Book: A = 5m candle with body >= 50% of range and close in its bottom 25% (bear mirror:
          top 25%); B = next 5m candle closing opposite to A (bullish reaction). Decide at B's
          close, trade against A, stop = B's low (high), 2R, hold 10 x 5m = 50min.
          Gate: B.low < A.low AND B's M1 low minute precedes its M1 high minute (low first).
claim '+': gated beats complement.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import concept_lab as cl  # noqa: E402

CID = "upper-half-eq-expansion-filter"
RR = 2.0
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "gate"]


def _ns(x):
    return pd.DatetimeIndex(x).tz_convert("UTC").as_unit("ns").asi8


def _bars(m1, tf, nmin):
    b = cl.build_bars(m1, tf)
    end = _ns(m1.index[-1:])[0] + 60_000_000_000
    b = b[_ns(b["close_time"]) <= end]                       # complete bars only
    st, ct = _ns(b.index), _ns(b["close_time"])
    pos = np.searchsorted(st, _ns(m1.index), "right") - 1    # M1 row -> bar position
    t = _ns(m1.index)
    ok = (pos >= 0) & (t < ct[np.maximum(pos, 0)])
    pos = np.where(ok, pos, -1)
    full = b["n_m1"].to_numpy() == nmin                      # no missing minutes
    prev_ok = np.zeros(len(b), bool)
    prev_ok[1:] = (ct[:-1] == st[1:]) & full[1:] & full[:-1]  # P immediately precedes N
    return b, st, ct, pos, prev_ok


def _out(ct, k, d, stop, gate):
    t = pd.DatetimeIndex(pd.to_datetime(ct[k], utc=True))
    return pd.DataFrame({"decision_time": t, "available_at": t, "direction": d.astype(int),
                         "stop_px": stop, "rr": RR, "gate": gate.astype(bool)})[COLS]


def detect_a(m1):
    b, st, ct, pos, prev_ok = _bars(m1, "15min", 15)
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ml, mh = m1["low"].to_numpy(float), m1["high"].to_numpy(float)
    n = len(ml)
    swl = np.zeros(n, bool); swh = np.zeros(n, bool)
    if n >= 3:
        same_next = (pos[1:-1] >= 0) & (pos[2:] == pos[1:-1])   # right neighbour inside the same bar
        swl[1:-1] = (ml[1:-1] < ml[:-2]) & (ml[1:-1] < ml[2:]) & same_next
        swh[1:-1] = (mh[1:-1] > mh[:-2]) & (mh[1:-1] > mh[2:]) & same_next
    k = pos.copy()
    kp = np.maximum(k - 1, 0)
    eq = 0.5 * (h + l)
    in_up = swl & (k >= 1) & (ml >= eq[kp]) & (ml <= h[kp])
    in_dn = swh & (k >= 1) & (mh <= eq[kp]) & (mh >= l[kp])
    g_up = np.zeros(len(b), bool); g_dn = np.zeros(len(b), bool)
    g_up[k[in_up]] = True; g_dn[k[in_dn]] = True
    sp = np.sign(np.r_[np.nan, (c - o)[:-1]]); sn = np.sign(c - o)
    keep = prev_ok & (sp == sn) & (sn != 0) & (h > l)
    idx = np.flatnonzero(keep)
    d = sn[idx]
    stop = np.where(d > 0, l[idx], h[idx])
    gate = np.where(d > 0, g_up[idx], g_dn[idx])
    return _out(ct, idx, d, stop, gate)


def detect_b(m1):
    b, st, ct, pos, prev_ok = _bars(m1, "5min", 5)
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    rng = h - l
    with np.errstate(divide="ignore", invalid="ignore"):
        body = np.abs(c - o) / rng
        cpos = (c - l) / rng
    bear_exp = (rng > 0) & (body >= 0.5) & (c < o) & (cpos <= 0.25)
    bull_exp = (rng > 0) & (body >= 0.5) & (c > o) & (cpos >= 0.75)
    # M1 order inside each bar: first minute of the bar's low and of its high
    v = pos >= 0
    mt = np.arange(len(pos))
    df = pd.DataFrame({"k": pos[v], "i": mt[v], "l": m1["low"].to_numpy(float)[v],
                       "h": m1["high"].to_numpy(float)[v]})
    lo_i = np.full(len(b), -1); hi_i = np.full(len(b), -1)
    if len(df):
        g = df.groupby("k")
        lo_i[g["l"].idxmin().index.to_numpy()] = df.loc[g["l"].idxmin().to_numpy(), "i"].to_numpy()
        hi_i[g["h"].idxmax().index.to_numpy()] = df.loc[g["h"].idxmax().to_numpy(), "i"].to_numpy()
    k = np.arange(1, len(b))
    up = prev_ok[k] & bear_exp[k - 1] & (c[k] > o[k])          # long after bearish expansion
    dn = prev_ok[k] & bull_exp[k - 1] & (c[k] < o[k])          # short after bullish expansion
    idx = k[up | dn]
    d = np.where(up[up | dn], 1, -1)
    sweep = np.where(d > 0, l[idx] < l[idx - 1], h[idx] > h[idx - 1])
    order = np.where(d > 0, lo_i[idx] < hi_i[idx], hi_i[idx] < lo_i[idx])   # same minute -> False
    stop = np.where(d > 0, l[idx], h[idx])
    return _out(ct, idx, d, stop, sweep & order)


READ = {
    "u1007a": dict(det=detect_a, hold="150min", tf="15min", rules=[
        "P = complete 15m candle (15/15 M1) closing in direction d; N = the next contiguous complete 15m candle closing in d",
        "EQ_P = (P.high + P.low)/2; decide at N's close; trade d; stop = N.low (bull) / N.high (bear); 2R; hold 150min",
        "gate: inside N, an M1 strict 3-bar swing low with low in [EQ_P, P.high] (bear: swing high in [P.low, EQ_P]); right neighbour inside N"],
        src={"htf": "corpus: 9H15ZZvaKPQ 'we want to see the upper 50% of this' on the 5m/15m chart; draft ambiguity '5m vs 15m' -> 15m declared-before-run so a 3-bar 1m swing fits inside one HTF candle",
             "ltf": "corpus: 9H15ZZvaKPQ 'Use a 3m minute. You can use the one minute ... Needs to form a one minute swing in this area'",
             "swing": "declared-before-run: 1m swing = strict 3-bar fractal (left=1,right=1), the minimal swing",
             "zone": "corpus: 9H15ZZvaKPQ 'the upper 50% of this ... This is the area I want to see hold'; library YAML 'the upper half of a higher time frame candle support price higher' (wvP9Y74Q_hQ)",
             "book": "declared-before-run: expansion = P and N both close in d (library 'when price is expanding'); stop on the low formed (library execution 'stop on the low')",
             "rr": "corpus: library YAML execution '2R (stated in the 4th-day example)'",
             "max_hold": "phase3: 10 entry-TF bars (meta/conjunction_preregistration.md §1.8-1.16) = 10 x 15m",
             "full_bars": "declared-before-run: complete bars only (n_m1 == minutes), README trap 6"}),
    "u1007b": dict(det=detect_b, hold="50min", tf="5min", rules=[
        "A = complete 5m candle, body >= 50% of range, close in bottom 25% (bearish expansion; bull mirror top 25%)",
        "B = next contiguous complete 5m candle closing opposite to A (the reaction); decide at B's close; trade against A",
        "stop = B.low (long) / B.high (short); 2R; hold 50min",
        "gate: B took out A's low (high) AND B's M1 low minute came before its M1 high minute (high before low for shorts); tie -> fail"],
        src={"htf": "corpus: 9H15ZZvaKPQ 'this is a fivem minute' (the candles discussed are 5m)",
             "expansion": "corpus: 9H15ZZvaKPQ 'This is kind of a bearish expansion candle. Usually we'll close in the low' -> declared-before-run body >= 0.5 range, close in bottom 25%",
             "reaction": "corpus: 9H15ZZvaKPQ 'And then you have a bullish reaction' -> B closes bullish",
             "gate": "corpus: 9H15ZZvaKPQ 'go lower first, right? Take out the previous candle's low. And then you have a bullish reaction' + 'it pointed its upper wick first which is more bearish'",
             "rr": "corpus: library YAML execution '2R (stated in the 4th-day example)'",
             "max_hold": "phase3: 10 entry-TF bars (meta/conjunction_preregistration.md §1.8-1.16) = 10 x 5m",
             "full_bars": "declared-before-run: complete bars only (n_m1 == minutes), README trap 6"}),
}


def run(rd):
    R = READ[rd]
    det = R["det"]
    ev = cl.cache_frame(f"{CID}_{rd}", lambda: det(cl.load_m1()))
    print(rd, len(ev), "gate rate", round(ev["gate"].mean(), 3))
    probe = cl.probe_lookahead(det, ev, lookback="5D")
    print("probe", probe["passed"])
    res = cl.gate_test(ev, "gate", mask_available_at="decision_time", max_hold=R["hold"])
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "exposure_bars", "ties", "ctrl_overlap")})
    vals = {"htf": R["tf"], "ltf": "1min", "rr": RR, "max_hold": R["hold"], "full_bars": True}
    op = {"rules": R["rules"], "params": {k: vals.get(k, "see rules") for k in R["src"]}}
    p = cl.write_result(CID, rd, res, operationalization=op, params_source=R["src"], script=__file__,
                        probe=probe, notes=f"TTrades live Q&A 9H15ZZvaKPQ refinement; gate firing rate "
                        f"{ev['gate'].mean():.3f} on {len(ev)} events. Prior readings __a/__b untouched.")
    print(p)


if __name__ == "__main__":
    for rd in sys.argv[1:] or list(READ):
        run(rd)
