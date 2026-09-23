"""propulsion-block (TTrades own voice, contested) — batch structure_own_03a.

"A propulsion block is an ORDER BLOCK OFF OF ANOTHER ORDER BLOCK." Built stepwise
(bullish; bearish mirrored):
  OB1  a down-close candle / series into an extreme (2/2 swing low) is CLOSED OVER
       (close above the series' first open) within 3 bars — the phase-3 CISD book.
       Zone = the series' bodies [body bottom, first open].
  retrace price trades back into OB1 (low <= OB1 top) within 20 bars, without a close
       below OB1's body bottom.
  OB2  the down-close series that traded into OB1 (contiguous run ending at the
       retracement low; a new lower low resets it) is closed over (close above its
       first candle's OPEN) within 20 bars of the retrace -> that is the propulsion block.
Trade (execution block): entry on the propulsion block's OPENING PRICE (limit; modelled
as the first M1 bar within 150 M1 bars whose low reaches the opening price, decided at
that M1 bar's close, entered at the next M1 open), target 2R.
Reading a: stop "on the low" (the block's extreme low).
Reading b: stop "on the body" (the block's lowest body level) — "he is fine with the
           body on a propulsion block".
trade_test vs matched random entries, claim '+'. TF 15m (yaml ltf 15m/5m).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a")
from _common import PHASE3, cl, np, pd, summary  # noqa: E402

CID = "propulsion-block"
TF, RR, HOLD = "15min", 2.0, "150min"
MAX_WAIT, W_RETRACE, W_PB, FILL_BARS, MAX_SERIES = 3, 20, 20, 150, 10


def _run(o, c, pos):
    """Down-close run ending at pos (or <= 2 bars before it), <= MAX_SERIES long."""
    end = pos
    while end >= 0 and not (c[end] < o[end]):
        end -= 1
        if pos - end > 2:
            return -1, -1
    if end < 0:
        return -1, -1
    start = end
    while start > 0 and c[start - 1] < o[start - 1] and end - start + 1 < MAX_SERIES:
        start -= 1
    return start, end


def _bull_blocks(o, h, l, c):
    """Propulsion blocks in 'bullish space'. Returns rows
    (j2, open_px, low_px, body_bot)."""
    n = len(o)
    out = []
    last_j2 = -1
    for pos in range(2, n - 2):
        if not ((l[pos] < l[pos - 2:pos]).all() and (l[pos] <= l[pos + 1:pos + 3]).all()):
            continue
        s1, e1 = _run(o, c, pos)
        if s1 < 0:
            continue
        lvl1 = o[s1]
        begin = max(e1, pos + 2) + 1
        j1 = -1
        for j in range(begin, min(n, begin + MAX_WAIT)):
            if c[j] > lvl1:
                j1 = j
                break
        if j1 < 0:
            continue
        top1 = max(np.maximum(o[s1:e1 + 1], c[s1:e1 + 1]).max(), lvl1)
        bot1 = np.minimum(o[s1:e1 + 1], c[s1:e1 + 1]).min()
        t0 = -1
        for j in range(j1 + 1, min(n, j1 + 1 + W_RETRACE)):
            if l[j] <= top1:
                t0 = j
                break
            if c[j] < bot1:
                break
        if t0 < 0 or c[t0] < bot1:
            continue
        m = j1 + 1 + int(np.argmin(l[j1 + 1:t0 + 1]))
        for j in range(t0 + 1, min(n, t0 + 1 + W_PB)):
            if c[j] < bot1:
                break
            if l[j] < l[m]:
                m = j
                continue
            s2, e2 = _run(o, c, m)
            if s2 < 0 or s2 <= e1:
                continue
            if c[j] > o[s2]:
                if j > last_j2:
                    body_bot = np.minimum(o[s2:e2 + 1], c[s2:e2 + 1]).min()
                    out.append((j, o[s2], l[s2:m + 1].min(), body_bot))
                    last_j2 = j
                break
    return out


def detect(m1, stop_kind: str):
    b = cl.build_bars(m1, TF)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = b["close_time"].to_numpy()
    mo = m1["open"].to_numpy(float)
    mh = m1["high"].to_numpy(float)
    ml = m1["low"].to_numpy(float)
    mc = m1["close"].to_numpy(float)
    mt = cl.data.utc_ns(m1.index)
    rows = []
    for d, arrs in ((1, (o, h, l, c)), (-1, (-o, -l, -h, -c))):
        for j2, opx, lowpx, bodyb in _bull_blocks(*arrs):
            stop = lowpx if stop_kind == "low" else bodyb
            if not stop < opx:
                continue
            t_close = cl.data.utc_ns(pd.DatetimeIndex([ct[j2]]))[0]
            i0 = int(np.searchsorted(mt, t_close, side="left"))
            i1 = min(len(mt), i0 + FILL_BARS)
            if i0 >= i1:
                continue
            seg_l = (ml[i0:i1] if d > 0 else -mh[i0:i1])
            hit = np.flatnonzero(seg_l <= opx)
            if not len(hit):
                continue
            k = i0 + int(hit[0])
            ck = mc[k] if d > 0 else -mc[k]
            if ck <= stop:
                continue
            rows.append((mt[k], d, d * stop, d * opx, int(k - i0)))
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "open_px", "fill_wait"]
    if not rows:
        return pd.DataFrame(columns=cols)
    r = pd.DataFrame(rows, columns=["tk", "d", "stop", "opx", "wait"])
    dt = cl.data.from_ns(r["tk"].to_numpy()) + pd.Timedelta(minutes=1)
    ev = pd.DataFrame({"decision_time": dt, "available_at": dt,
                       "direction": r["d"].to_numpy().astype(int),
                       "stop_px": r["stop"].to_numpy(float), "rr": RR,
                       "open_px": r["opx"].to_numpy(float),
                       "fill_wait": r["wait"].to_numpy(int)})
    ev = ev.drop_duplicates(["decision_time", "direction"], keep="first")
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    rules = [f"{TF} bars. OB1 = down-close series (<=10) into a 2/2 swing low, closed over "
             f"(close > series first open) within {MAX_WAIT} bars after the swing confirms "
             "(phase-3 CISD); zone = series bodies",
             f"price trades back into OB1 (low <= OB1 top) within {W_RETRACE} bars, no close "
             "below OB1 body bottom",
             "OB2 = down-close series ending at the retracement low (new lower low resets); a "
             f"close above OB2's first open within {W_PB} bars = propulsion block",
             f"entry: first M1 bar within {FILL_BARS} M1 bars of the PB close whose low reaches "
             "the PB opening price; decide at that M1 close (must be above the stop), enter "
             "next M1 open; target 2R; exit after " + HOLD + "; bearish mirrored"]
    params = {"tf": TF, "swing": "2/2", "max_wait": MAX_WAIT, "retrace_window": W_RETRACE,
              "pb_window": W_PB, "fill_window_m1": FILL_BARS, "max_series": MAX_SERIES,
              "rr": RR, "max_hold": HOLD}
    src = {"tf": "corpus: propulsion-block.yaml timeframes ltf ['15m','5m']",
           "swing": PHASE3, "max_wait": PHASE3, "max_series": PHASE3,
           "retrace_window": "declared-before-run: 20 bars (5h) for the return into OB1",
           "pb_window": "declared-before-run: 20 bars for OB2 to be closed over",
           "fill_window_m1": "declared-before-run: limit at the opening price lives 150 M1 "
                             "bars (the phase-3 15m hold length)",
           "rr": "corpus: hKCMqh0ZsY0 / yaml execution 'target 2R'",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    for reading, kind, extra in (
            ("a", "low", "stop = the propulsion block's LOW (lowest low of the series to "
                         "the retracement low)"),
            ("b", "body", "stop = the propulsion block's BODY (lowest open/close of the series)")):
        ev = cl.cache_frame(f"pb_{TF}_{kind}_v1", lambda: detect(cl.load_m1(), kind))
        print(reading, len(ev), ev["direction"].value_counts().to_dict(),
              ev["fill_wait"].describe().to_dict())
        probe = cl.probe_lookahead(lambda m: detect(m, kind), ev, lookback="10D")
        res = cl.trade_test(ev, max_hold=HOLD)
        print(f"reading {reading}\n" + summary(res))
        p = cl.write_result(CID, reading, res,
                            operationalization={"rules": rules + [extra],
                                                "params": {**params, "stop": kind}},
                            params_source={**src, "stop": "corpus: yaml execution 'stop on "
                                           "the low or on the body (the body is acceptable "
                                           "here)'"},
                            script=__file__, probe=probe,
                            notes="Limit fill at the opening price is modelled as the next "
                                  "M1 open after the first M1 bar that reaches it (harness "
                                  "entry convention); OB1 'important level' is the swept 2/2 "
                                  "swing extreme, no further POI gate.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
