"""indicator-print-conditions (TTrades own voice, contested) — batch model_own_01b.

Claim: a 'model' exists only when a higher-timeframe C2 closure at a POI is PAIRED
with a change in the state of delivery on the aligned lower timeframe INSIDE that
candle; a closure alone is not a setup ("loss rate of closure-only entries vs
closure-plus-CISD entries").

Baseline book: every HTF C2 closure (method_spec §3.2 test: bullish low[i] < low[i-1]
and close[i] > low[i-1]; bearish mirrored; two-sided outside bars dropped). The POI
gate is satisfied by construction (C2 takes out C1's high/low = 'a high/low taken
out'). Trade C3: decide at C2's close, enter next M1 open in the reversal direction,
stop at C2's extreme, 2R, hold two HTF candles (C3 and C4) in trading time.
Gate: an LTF CISD in the same direction confirmed inside C2 (LTF bars that start at
or after C2's open and close by C2's close): find the extreme, the series of
opposing-close candles into it, and require an LTF close through the series' first
open (series_open), exactly the hourly_cisd_in_candle procedure (§2.4).

Reading a: pair 1H -> 5m.   Reading b: pair 4H (forex grid) -> 15m.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
from _common import cl, np, pd, summary  # noqa: E402
from detectors.cisd import _run_into_extreme  # noqa: E402

CID = "indicator-print-conditions"
PAIRS = {"a": ("1h", "5min", 120), "b": ("4h", "15min", 480)}


def c2_book(H: pd.DataFrame) -> pd.DataFrame:
    lo, hi, c = H["low"].to_numpy(), H["high"].to_numpy(), H["close"].to_numpy()
    plo, phi = np.r_[np.nan, lo[:-1]], np.r_[np.nan, hi[:-1]]
    bull = (lo < plo) & (c > plo)
    bear = (hi > phi) & (c < phi)
    one = bull ^ bear
    sel = np.flatnonzero(one)
    d = np.where(bull[sel], 1, -1)
    return pd.DataFrame({"pos": sel, "direction": d,
                         "stop_px": np.where(d > 0, lo[sel], hi[sel])})


def ltf_cisd_inside(L: pd.DataFrame, a: int, b: int, bullish: bool) -> bool:
    seg = L.iloc[a:b]
    if len(seg) < 3:
        return False
    ext = int(np.argmin(seg["low"].to_numpy()) if bullish else np.argmax(seg["high"].to_numpy()))
    s, e = _run_into_extreme(seg, ext, bullish, max_len=10)
    if s < 0:
        return False
    lvl = float(seg["open"].iloc[s])
    cc = seg["close"].to_numpy()[e + 1:]
    return bool((cc > lvl).any() if bullish else (cc < lvl).any())


def make_detect(htf: str, ltf: str):
    def detect(m1):
        H = cl.build_bars(m1, htf)
        L = cl.build_bars(m1, ltf)
        bk = c2_book(H)
        hs = cl.data.utc_ns(pd.DatetimeIndex(H.index))
        hc = cl.data.utc_ns(pd.DatetimeIndex(H["close_time"]))
        ls = cl.data.utc_ns(pd.DatetimeIndex(L.index))
        lc = cl.data.utc_ns(pd.DatetimeIndex(L["close_time"]))
        gate = np.zeros(len(bk), bool)
        for k, (p, d) in enumerate(zip(bk["pos"].to_numpy(), bk["direction"].to_numpy())):
            a = np.searchsorted(ls, hs[p], side="left")
            b = np.searchsorted(lc, hc[p], side="right")      # LTF bars closed by C2 close
            gate[k] = ltf_cisd_inside(L, a, b, d > 0)
        ct = pd.DatetimeIndex(H["close_time"].to_numpy()[bk["pos"].to_numpy()])
        return pd.DataFrame({"decision_time": ct, "available_at": ct,
                             "direction": bk["direction"].to_numpy(),
                             "stop_px": bk["stop_px"].to_numpy(float), "rr": 2.0,
                             "ltf_cisd": gate}).reset_index(drop=True)
    return detect


def main():
    for reading, (htf, ltf, hold_bars) in PAIRS.items():
        detect = make_detect(htf, ltf)
        ev = cl.cache_frame(f"ipc_c2_{htf}_{ltf}_v1", lambda: detect(cl.load_m1()))
        probe = cl.probe_lookahead(detect, ev, lookback="20D")
        hold = f"{hold_bars}min"
        res = cl.gate_test(ev, "ltf_cisd", mask_available_at="decision_time",
                           max_hold=hold, hold_basis="bars")
        print(f"reading {reading} ({htf}->{ltf})\n" + summary(res))
        op = {"rules": [
            f"HTF {htf} C2 closure: bullish low<prev low and close>prev low; bearish mirrored; "
            "two-sided outside bars dropped",
            "trade C3: decide at C2 close, enter next M1 open in the reversal direction, "
            "stop at C2's extreme, 2R, hold two HTF candles (trading time)",
            f"gate: {ltf} CISD in the same direction confirmed by LTF bars inside C2 "
            "(extreme -> series of opposing closes -> close through the series' first open)"],
            "params": {"htf": htf, "ltf": ltf, "grid4h": "forex", "rr": 2.0,
                       "max_hold": hold, "hold_basis": "bars", "level_rule": "series_open",
                       "max_series": 10}}
        src = {"htf": "method_spec: §1.2 timeframe pairing table",
               "ltf": "method_spec: §1.2 timeframe pairing table",
               "grid4h": "session_window_fit: forex grid for gold (weak; knob recorded)",
               "rr": "method_spec: §5.3 2R default",
               "max_hold": "declared-before-run: C3 and C4, the two continuation candles (method_spec §3.1)",
               "hold_basis": "declared-before-run: trading time so halts/weekends do not shorten the hold",
               "level_rule": "method_spec: §4.2 first-candle-open default",
               "max_series": "method_spec: §2.4 hourly_cisd_in_candle default (detectors.bias)"}
        p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe,
                            notes="gate uses only LTF bars closed by the C2 close, so it is "
                                  "knowable at the decision time.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
