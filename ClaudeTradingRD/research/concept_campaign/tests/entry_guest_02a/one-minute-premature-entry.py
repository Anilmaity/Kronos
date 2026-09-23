"""one-minute-premature-entry — NickDoesFutures: enter when a 1-minute candle closes through the
5-minute level instead of waiting for the 5-minute close, keeping the 5-minute trade's stop.

Test: gate_test on a two-arm book built from the same 5m levels.
  5m level (long) = a confirmed 2/2 5m swing high; the setup must break within 48 5m bars of
  confirmation.  confirmed row = the first 5m bar that CLOSES above the level (decide at that
  5m close).  premature row = the first M1 bar after the level's confirmation (within the same
  48-bar window) that closes above the level, when that M1 close is not itself a 5m close;
  it is emitted whether or not the 5m later confirms (unknowable at entry).
  Both rows: stop = the most recent confirmed 5m swing low at the row's decision time (the
  5-minute trade's stop, below the level), 2R target, 50 min (10 x 5m) max hold.
  Shorts mirrored.  gate = premature; claim '+': premature entries beat waiting for the 5m close.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "one-minute-premature-entry"
BREAK_WITHIN = 48
RR = 2.0
MAX_HOLD = "50min"


def swings(h, l, left=2, right=2):
    hs = pd.Series(h); ls = pd.Series(l)
    prev_h = hs.shift(1).rolling(left).max(); prev_l = ls.shift(1).rolling(left).min()
    next_h = hs[::-1].shift(1).rolling(right).max()[::-1]
    next_l = ls[::-1].shift(1).rolling(right).min()[::-1]
    return ((hs > prev_h) & (hs >= next_h)).to_numpy(), ((ls < prev_l) & (ls <= next_l)).to_numpy()


def long_rows(h, l, c, ct_ns, m_t_ns, m_c):
    """ct_ns: 5m close times (int ns); m_t_ns: M1 START times (int ns); m_c: M1 closes."""
    n = len(h)
    is_h, is_l = swings(h, l)
    sl_piv = np.where(is_l)[0]
    sl_piv = sl_piv[sl_piv + 2 < n]
    sl_conf = ct_ns[sl_piv + 2]                 # confirmation time of each swing low
    one_min = 60_000_000_000
    rows = []
    for p in np.where(is_h)[0]:
        q = p + 2
        if q >= n:
            continue
        L = h[p]
        conf = ct_ns[q]
        end = min(n, q + 1 + BREAK_WITHIN)
        cand = []
        # premature: first M1 close above L inside the level's window, whether or not the 5m
        # later confirms (that is only known later), and not on a 5m close boundary
        a = np.searchsorted(m_t_ns, conf)
        b = np.searchsorted(m_t_ns, ct_ns[end - 1])
        hit = np.where(m_c[a:b] > L)[0]
        if len(hit):
            t1 = m_t_ns[a + hit[0]] + one_min
            if t1 % (5 * one_min) != 0:
                cand.append((t1, True))
        brk = np.where(c[q + 1:end] > L)[0]
        if len(brk):
            cand.append((ct_ns[q + 1 + brk[0]], False))   # first 5m close above L
        for td, prem in cand:
            k = np.searchsorted(sl_conf, td, side="right") - 1
            if k < 0:
                continue
            stop = l[sl_piv[k]]
            if not stop < L:
                continue
            rows.append((td, stop, prem))
    return rows


def detect(m1):
    b = cl.build_bars(m1, "5min")
    h, l, c = (b[x].to_numpy() for x in ("high", "low", "close"))
    ct_ns = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC").as_unit("ns").asi8
    m_t_ns = m1.index.tz_convert("UTC").as_unit("ns").asi8
    m_c = m1["close"].to_numpy()
    out = []
    for sgn, (hh, ll, cc, mc) in ((1, (h, l, c, m_c)), (-1, (-l, -h, -c, -m_c))):
        for td, stop, prem in long_rows(hh, ll, cc, ct_ns, m_t_ns, mc):
            out.append((td, sgn, sgn * stop, prem))
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "premature"]
    if not out:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(out, columns=["t", "direction", "stop_px", "premature"])
    df["t"] = pd.to_datetime(df["t"], utc=True)
    df = df.sort_values(["t", "direction", "premature"]).drop_duplicates(
        ["t", "direction"], keep="last").reset_index(drop=True)
    return pd.DataFrame({"decision_time": df.t, "available_at": df.t,
                         "direction": df.direction.astype(int), "stop_px": df.stop_px,
                         "rr": RR, "premature": df.premature.astype(bool).to_numpy()})


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_bw{BREAK_WITHIN}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.premature.mean(), ev.direction.value_counts().to_dict())
    if "--dry" in sys.argv:
        print(ev.head(8)); raise SystemExit
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    res = cl.gate_test(ev, "premature", mask_available_at="decision_time", max_hold=MAX_HOLD, claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": [
        "5m level = confirmed 2/2 5m swing high (long) / low (short); live for 48 5m bars after confirmation",
        "confirmed row = the first 5m close through the level (decide at that 5m close)",
        "premature row = the first M1 close through the level within the level's 48-bar window, if not "
        "itself a 5m close; emitted whether or not the 5m later confirms",
        "stop (both) = most recent confirmed 5m swing low (long) / high (short) at the decision; 2R; 50 min",
        "gate = premature vs confirmed"],
        "params": {"level": "5m swing 2/2", "break_within_5m_bars": BREAK_WITHIN, "rr": RR,
                   "max_hold": MAX_HOLD}}
    src = {"level": "phase3: meta/conjunction_preregistration.md §1.8 swing left=2,right=2 (the 5m level; the source's 'breaker' naming is contested)",
           "break_within_5m_bars": "declared-before-run: a level must break within 4h (48 x 5m) to be the 'marked level' being traded",
           "rr": "corpus: tDiwwMRWF2k premature entry used when the 5m close is too late 'for a 2R trade'",
           "max_hold": "phase3: §1.13 10 entry-TF (5m) periods"}
    notes = ("A first version emitted the premature row only for levels the 5m later broke (a future "
             "filter); the lookahead probe caught it before any test ran and it was fixed. Not modelled: the early cut when the 5m candle fails to confirm — that exit depends on the "
             "5m close AFTER entry, which cannot be a per-row column without reading the future; so the "
             "premature arm carries the full stop on its failures (a conservative reading of the method). "
             "The 4H and 15m level preconditions are not modelled.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, notes=notes, probe=probe)
    print(p)
