"""htf-opening-price-entry — gate_test on the phase-3 bare 15m CISD book.

Claim (+): entries located around (or beyond, in the trade's favour) the opening
price of the governing higher-timeframe candle, before that candle has made its
typical range, beat the rest (the "chase" entries).
Contested on WHICH higher timeframe governs (daily vs 4-hour; "the example moved
between the daily and the 4-hour") -> reading a = 1D, reading b = 4H (forex grid).
All parameters declared before the first run.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, cisd_book, run_and_print, PHASE3_SRC  # noqa: E402

TF = "15min"
MAX_HOLD = "150min"
NEAR = 0.25          # d*(price - open) <= 0.25 x typical range of that HTF candle
SPENT = 1.0          # candle's realised range must still be < its typical range
READINGS = {"a": dict(htf="1D", k=5, min_m1=600),
            "b": dict(htf="4h", k=30, min_m1=120)}


def htf_position(m1: pd.DataFrame, times, htf: str, k: int, min_m1: int) -> pd.DataFrame:
    """For each t: open of the HTF candle containing t, its realised range from M1
    closed by t, and the mean range of the last k completed candles (>= min_m1 bars).
    A t sitting exactly on a candle boundary means the entry opens a new candle:
    distance 0 and realised range 0 (known by the clock)."""
    t = pd.DatetimeIndex(times).tz_convert("UTC")
    b = cl.build_bars(m1, htf)
    starts = pd.DatetimeIndex(b.index).tz_convert("UTC")
    ends = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    tn = cl.data.utc_ns(t)
    pos = np.searchsorted(cl.data.utc_ns(starts), tn, side="right") - 1
    pc = np.clip(pos, 0, None)
    inside = (pos >= 0) & (cl.data.utc_ns(ends)[pc] > tn) & (cl.data.utc_ns(starts)[pc] < tn)
    # running hi/lo of each candle from M1 (cumulative within the bucket)
    mt = pd.DatetimeIndex(m1.index).tz_convert("UTC")
    mb = np.searchsorted(cl.data.utc_ns(starts), cl.data.utc_ns(mt), side="right") - 1
    hi = pd.Series(m1["high"].to_numpy()).groupby(mb).cummax().to_numpy()
    lo = pd.Series(m1["low"].to_numpy()).groupby(mb).cummin().to_numpy()
    p = np.searchsorted(cl.data.utc_ns(mt), tn, side="left") - 1   # last M1 closed by t
    pp = np.clip(p, 0, None)
    same = (p >= 0) & (mb[pp] == pos)
    opn = np.where(inside, b["open"].to_numpy(float)[pc], np.nan)
    real = np.where(inside & same, hi[pp] - lo[pp], np.nan)
    ok_in = inside & same
    # typical range of completed candles
    c = b[b["n_m1"] >= min_m1].copy()
    c["typ"] = (c["high"] - c["low"]).rolling(k, min_periods=k).mean()
    typ = cl.asof(c, t)["typ"].to_numpy(float)
    return pd.DataFrame({"inside": inside, "ok_in": ok_in, "htf_open": opn,
                         "realised": real, "typ": typ}, index=t)


def make_detect(htf: str, k: int, min_m1: int):
    def detect(m1: pd.DataFrame) -> pd.DataFrame:
        ev = cisd_book(m1, TF)
        if ev.empty:
            return ev.assign(near_open=pd.Series(dtype=bool))
        hp = htf_position(m1, ev["decision_time"], htf, k, min_m1)
        d = ev["direction"].to_numpy()
        px = ev["confirm_close"].to_numpy()
        inside = hp["inside"].to_numpy()
        dist = np.where(inside, d * (px - hp["htf_open"].to_numpy()), 0.0)
        real = np.where(inside, hp["realised"].to_numpy(), 0.0)
        typ = hp["typ"].to_numpy()
        valid = np.isfinite(typ) & (~inside | hp["ok_in"].to_numpy())
        ev = ev.assign(dist_open=dist / typ, realised_frac=real / typ)[valid]
        ev = ev.reset_index(drop=True)
        ev["near_open"] = ((ev["dist_open"] <= NEAR) & (ev["realised_frac"] < SPENT)).astype(bool)
        return ev
    return detect


if __name__ == "__main__":
    for rd, kw in READINGS.items():
        detect = make_detect(**kw)
        ev = cl.cache_frame(f"htfope_{TF}_{kw['htf']}_k{kw['k']}_n{NEAR}_s{SPENT}",
                            lambda: detect(cl.load_m1()))
        print(rd, kw, len(ev), "gate rate", round(ev["near_open"].mean(), 3))
        probe = cl.probe_lookahead(detect, ev, lookback="30D")
        print("probe", probe.get("passed"))
        res = cl.gate_test(ev, "near_open", mask_available_at="decision_time", max_hold=MAX_HOLD)
        run_and_print(res)
        op = {"rules": [
            "baseline book: phase-3 bare 15m CISD (series_open, 2/2, max_wait 3, min_series 1), decide at "
            "confirming bar close, enter next M1 open, stop = protected swing, 2R, hold 150min",
            f"governing HTF candle = the {kw['htf']} candle containing the decision time "
            "(forex 4H grid, 18:00 NY day roll); a decision on a candle boundary opens a new candle (distance 0)",
            f"gate: direction x (confirm close - HTF open) <= {NEAR} x typical range (at/below the open for "
            "longs is accepted) AND the candle's realised range so far < typical range (not already expanded)",
            f"typical range = mean high-low of the last {kw['k']} completed {kw['htf']} candles"],
            "params": {"tf": TF, "max_hold": MAX_HOLD, "htf": kw["htf"], "typ_k": kw["k"],
                       "min_m1": kw["min_m1"], "near": NEAR, "spent": SPENT, "grid4h": "forex"}}
        src = {"tf": "phase3: primary entry TF 15m (concept ltf 15m/5m/3m/1m)",
               "max_hold": PHASE3_SRC + " — 10 entry-TF bars",
               "htf": "corpus: m8xcjkOuBHU 'enter around the opening price of the higher time frame candles' — "
                      "reading a daily / b 4-hour ('the example moved between the daily and the 4-hour')",
               "typ_k": "declared-before-run: typical range = mean of the last 5 trading days of candles",
               "min_m1": "declared-before-run: skip stub candles under half coverage (trap 6)",
               "near": "declared-before-run: 'near the opening price' never bounded -> a quarter of the typical range",
               "spent": "corpus: Qv6Ux_Z8VrA/i2HhHhWdaPQ 'do not enter once the candle's realised range approaches "
                        "or exceeds its typical range' -> realised < 1.0 x typical",
               "grid4h": "session_window_fit: forex grid (carried as a knob, trap 8)"}
        notes = ("Entry-location filter tested as a gate on the phase-3 15m CISD book. The yearly-open "
                 "long-term variant is explicitly outside the trading model and is not tested.")
        p = cl.write_result("htf-opening-price-entry", rd, res, operationalization=op,
                            params_source=src, script=__file__, probe=probe, notes=notes)
        print("wrote", p)
