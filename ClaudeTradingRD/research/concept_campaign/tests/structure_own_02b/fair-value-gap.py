"""fair-value-gap — two readings (contested; the YAML's execution names two roles).

Object (method_spec §3.9): three candles whose 1st and 3rd WICKS do not overlap;
bullish low[i] > high[i-2], gap [high[i-2], low[i]]; bearish mirror. Known at candle 3's close.
Execution bias: "toward the unfilled gap when it is the draw; away from it when it is the
entry array."

(a) ENTRY ARRAY — trade_test. First return of price to the gap's near edge within 24 trading
    hours (1440 M1 bars) of the gap being known -> enter in the gap's polarity at the next M1
    open, stop beyond the far edge (the defending edge), 2R, hold 10h. A return M1 bar that
    also trades through the far edge is dropped (it cannot be entered next-open).
    claim '+': beats a matched random entry with the same stop/target geometry.
(b) DRAW — rate_test. At the gap's formation, is the gap FULLY closed (price trades to the
    far edge; "counts as efficient only once it is fully closed") within the next 1440 M1
    bars, more often than a level at the same distance on the same side from a matched random
    moment (+/-30 d, same bar count)? claim '+'.
1h gaps (the method's structure timeframe; YAML ltf lists 1H).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, ns, empty, fvg_arrays, M1, first_touch, ONE_MIN  # noqa: E402

CID = "fair-value-gap"
TF, RET_BARS, HOLD, RR = "1h", 1440, "10h", 2.0
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "rr"]
COLS_B = ["decision_time", "available_at", "direction", "far_edge", "near_edge"]


def gaps(m1):
    b = cl.build_bars(m1, TF)
    if len(b) < 5:
        return None
    h, l = b["high"].to_numpy(float), b["low"].to_numpy(float)
    bull, bear, glo, ghi = fvg_arrays(h, l)
    return b, bull, bear, glo, ghi


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    g = gaps(m1)
    if g is None:
        return empty(COLS_A)
    b, bull, bear, glo, ghi = g
    ct = ns(b["close_time"])
    m = M1(m1)
    rows = []
    for i in np.flatnonzero(bull | bear):
        up = bool(bull[i])
        near, far = (ghi[i], glo[i]) if up else (glo[i], ghi[i])
        i0 = int(np.searchsorted(m.t, ct[i], "left"))
        i1 = min(i0 + RET_BARS, m.n)
        if i1 <= i0:
            continue
        j = first_touch(m, m.t[i0], m.t[i1 - 1] + 1, near, up)
        if j < 0:
            continue
        through = (m.l[j] <= far) if up else (m.h[j] >= far)
        if through:
            continue
        rows.append((m.t[j] + ONE_MIN, 1 if up else -1, far))
    if not rows:
        return empty(COLS_A)
    out = pd.DataFrame(rows, columns=["t", "direction", "stop_px"])
    t = pd.DatetimeIndex(pd.to_datetime(out["t"].to_numpy(np.int64), utc=True))
    return pd.DataFrame({"decision_time": t, "available_at": t, "direction": out["direction"].to_numpy(),
                         "stop_px": out["stop_px"].to_numpy(), "rr": RR}
                        ).sort_values("decision_time", kind="stable").reset_index(drop=True)[COLS_A]


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    g = gaps(m1)
    if g is None:
        return empty(COLS_B)
    b, bull, bear, glo, ghi = g
    sel = bull | bear
    t = pd.DatetimeIndex(b["close_time"])[sel]
    up = bull[sel]
    return pd.DataFrame({"decision_time": t, "available_at": t,
                         "direction": np.where(up, 1, -1),
                         "far_edge": np.where(up, glo[sel], ghi[sel]),
                         "near_edge": np.where(up, ghi[sel], glo[sel])}).reset_index(drop=True)[COLS_B]


SRC_COMMON = {"tf": "method_spec: §1.2 hourly structure timeframe; YAML ltf [1H, 15m, 5m, 1m]",
              "fvg": "corpus: YAML 'bullish_fvg at i: low[i+1] > high[i-1]' (wick test, method_spec §3.9)"}

if __name__ == "__main__":
    rd = sys.argv[1]
    if rd == "a":
        ev = cl.cache_frame(f"{CID}_a_{TF}_{RET_BARS}", lambda: detect_a(cl.load_m1()))
        print(len(ev))
        probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
        print("probe", probe["passed"])
        res = cl.trade_test(ev, max_hold=HOLD)
        print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p", "mde",
                                       "win_rate", "exposure_bars", "ties", "ctrl_overlap")})
        op = {"rules": ["1h 3-candle FVGs (wicks), known at the 3rd candle's close",
                        "first M1 bar within the next 1440 M1 bars reaching the gap's near edge; decide at that M1 close",
                        "enter next M1 open in the gap's polarity; stop = far edge; 2R; hold 10h",
                        "return bars that also trade through the far edge are dropped"],
              "params": {"tf": TF, "return_bars": RET_BARS, "rr": RR, "max_hold": HOLD}}
        src = {**SRC_COMMON,
               "return_bars": "declared-before-run: a gap not revisited within one trading day (1440 M1) is dropped (no expiry rule in the corpus)",
               "rr": "phase3: 2R (the gap's 'opposing array' target is undefined mechanically)",
               "max_hold": "phase3: 10 structure-TF (1h) bars",
               "stop": "corpus: YAML execution 'Beyond the gap's far edge'"}
        p = cl.write_result(CID, "a", res, operationalization=op, params_source=src, script=__file__,
                            probe=probe, notes="entry-array reading: limit at near edge on first return")
        print(p)
    else:
        ev = cl.cache_frame(f"{CID}_b_{TF}", lambda: detect_b(cl.load_m1()))
        print(len(ev))
        probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
        print("probe", probe["passed"])
        mkt = cl.get_market()
        t = pd.DatetimeIndex(ev["decision_time"])
        up = ev["direction"].to_numpy() == 1
        far = ev["far_edge"].to_numpy(float)
        px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
        dist = np.abs(px - far)                         # far edge is below (bull) / above (bear)

        def fill(times, level, upmask):
            out = np.full(len(times), np.nan)
            for side, s in (("below", upmask), ("above", ~upmask)):
                if s.any():
                    out[s] = cl.touch(times[s], level[s], side, horizon_bars=RET_BARS)["hit"].to_numpy()
            return out

        obs = fill(t, far, up)
        rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

        def null_fn(rng, k):
            tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
            ok = ~tk.isna()
            out = np.full(len(t), np.nan)
            pk = mkt.o[mkt.pos_at_or_after(tk[ok])]
            lvl = np.where(up[ok], pk - dist[ok], pk + dist[ok])
            out[ok] = fill(tk[ok], lvl, up[ok])
            return out

        res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, predictors=ev, claim="+")
        print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "observed_rate", "null_rate", "diff",
                                       "ci_lo", "ci_hi", "p", "mde")})
        op = {"rules": ["1h 3-candle FVGs (wicks), known at the 3rd candle's close",
                        "hit = price trades to the far edge (full close of the gap) within the next 1440 M1 bars",
                        "distance = |first M1 open after the decision - far edge|; far edge sits against the gap's polarity",
                        "null: matched random moments (+/-30 d, locked seed), a level at the same distance on the same side, same 1440-bar horizon"],
              "params": {"tf": TF, "horizon_bars": RET_BARS, "fill": "far edge (full close)"}}
        src = {**SRC_COMMON,
               "horizon_bars": "declared-before-run: one trading day of M1 bars (no expiry rule in the corpus)",
               "fill": "corpus: YAML 'counts a gap as efficient only once it is fully closed'; 'A partial tap does not count as filled'"}
        p = cl.write_result(CID, "b", res, operationalization=op, params_source=src, script=__file__,
                            probe=probe, notes="draw reading: the unfilled gap attracts price back to its far edge")
        print(p)
