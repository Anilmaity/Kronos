"""half-wick-respect (TTrades own voice, contested) — batch structure_own_02a.

Rule (method_spec §3.6): after a higher-timeframe REVERSAL candle, measure the wick from
the BODY to the extreme and mark its 50%. Bullish: the following period should open,
form its low in the UPPER half of the wick and trade higher; a close through 0.5 of the
wick means the swing is expected to fail and the low to be taken. Mirror for bearish.
Branch (threshold_fits §1 / method_spec §3.6): the wick half applies to LARGE-wick
candles; reversal candle := "the wick is larger than the body" (grade A).

Operationalisation:
  C1 = a 4H candle (forex grid) whose lower wick (min(open,close) - low) exceeds its body
       and its upper wick -> bullish reversal candle (mirror: upper wick -> bearish).
       half = body bottom - 0.5 x lower wick.
  C2 = the next 4H candle. Inside it, the FIRST 1h bar that trades into the wick
       (low <= body bottom) while C1's low is still intact (no 1h bar of C2 through it
       has traded below C1's low) is the test bar; decide at its close.
  Baseline trade: long (the reversal direction) at the next M1 open, stop = C1's low (the
       wick extreme), 2R, exit after 240 trading minutes (one 4H period).
  Gate (respected) — the corpus leaves "close" vs "touch" open, so two readings:
    a  close-based: the test bar CLOSES at/above the half level ("A close through 0.5 of
       the wick counts as disrespect")
    b  touch-based: the test bar's LOW stays at/above the half level ("form a low at or
       above that level" / "form its low in the upper half of the wick")
  claim '+': respected entries beat disrespected ones, control-adjusted.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a")
from _common import cl, np, pd, summary  # noqa: E402

CID = "half-wick-respect"
RR, HOLD = 2.0, "240min"


def detect(m1):
    H = cl.build_bars(m1, "4h", grid4h="forex")
    b = cl.build_bars(m1, "1h")
    o, h, l, c = (H[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    Hs = H.index
    Hc = pd.DatetimeIndex(H["close_time"])
    bo, bh, bl, bc = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    bs = b.index
    bct = pd.DatetimeIndex(b["close_time"])
    body = np.abs(c - o)
    lw = np.minimum(o, c) - l
    uw = h - np.maximum(o, c)
    rows = []
    for i in range(len(H) - 1):
        if lw[i] > body[i] and lw[i] > uw[i]:
            bull = True
        elif uw[i] > body[i] and uw[i] > lw[i]:
            bull = False
        else:
            continue
        a, z = bs.searchsorted(Hs[i + 1]), bs.searchsorted(Hc[i + 1])
        # 1h bars fully inside C2
        for k in range(a, z):
            if bct[k] > Hc[i + 1]:
                break
            if bull:
                if bl[k] < l[i]:
                    break
                edge = min(o[i], c[i])
                if bl[k] <= edge:
                    half = edge - 0.5 * lw[i]
                    rows.append((k, 1, l[i], half, bc[k] >= half, bl[k] >= half))
                    break
            else:
                if bh[k] > h[i]:
                    break
                edge = max(o[i], c[i])
                if bh[k] >= edge:
                    half = edge + 0.5 * uw[i]
                    rows.append((k, -1, h[i], half, bc[k] <= half, bh[k] <= half))
                    break
    ev = pd.DataFrame(rows, columns=["k", "dir", "stop", "half", "resp_close", "resp_touch"])
    ct = bct[ev["k"].to_numpy()]
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": ev["dir"].to_numpy().astype(int),
                         "stop_px": ev["stop"].to_numpy(), "rr": RR,
                         "half": ev["half"].to_numpy(),
                         "resp_close": ev["resp_close"].to_numpy(bool),
                         "resp_touch": ev["resp_touch"].to_numpy(bool)})


def main():
    ev = cl.cache_frame("halfwick_4h_1h_v1", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    rules = ["C1 = 4H candle (forex grid) whose lower wick exceeds its body and its upper wick "
             "(bullish reversal candle; mirror bearish); half = body edge -/+ 0.5 x wick",
             "C2 = next 4H candle; test bar = first complete 1h bar inside C2 that trades into "
             "the wick (beyond the body edge) while C1's extreme is intact",
             f"decide at the test bar's close; trade C1's reversal direction at the next M1 "
             f"open, stop = C1's wick extreme, {RR}R, exit after {HOLD} of trading time"]
    params = {"htf": "4h", "grid4h": "forex", "ltf": "1h", "reversal_candle": "wick > body and > other wick",
              "rr": RR, "max_hold": HOLD, "hold_basis": "bars"}
    src = {"htf": "corpus yaml timeframes htf 1D/4H/1H; threshold_fits §1 wick effects live on 4h/1D",
           "grid4h": "session_window_fit: forex grid for gold (weak; recorded)",
           "ltf": "corpus yaml timeframes: the next period is read on a lower timeframe (15m/5m listed; 1h is the 4H's hourly CISD layer, method_spec §2.4)",
           "reversal_candle": "threshold_fits: large wick / reversal candle = opposing run > body (grade A); corpus TND1aTpnq5c 'the wick is larger than the body'",
           "rr": "corpus yaml execution targets: '2R'", "max_hold": "declared-before-run: one 4H period",
           "hold_basis": "declared-before-run: trading time (the 17:00 grid candle spans the halt)"}
    for reading, col, rule, quote in (
            ("a", "resp_close", "gate: the test bar CLOSES at/beyond the half level on the reversal side",
             "corpus yaml: 'A close through 0.5 of the wick counts as disrespect'"),
            ("b", "resp_touch", "gate: the test bar's low (high) stays at/above (below) the half level",
             "corpus yaml: 'on the following period price should open, form a low at or above that level'")):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD,
                           hold_basis="bars")
        print(f"reading {reading}\n" + summary(res))
        p = cl.write_result(CID, reading, res, operationalization={
            "rules": rules + [rule], "params": {**params, "respect": col}},
            params_source={**src, "respect": quote}, script=__file__, probe=probe,
            notes="Both arms enter long at the same test bar; the concept says a disrespect "
                  "close should instead lean the other way, so a respected-minus-disrespected "
                  "differential captures both halves of the claim.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
