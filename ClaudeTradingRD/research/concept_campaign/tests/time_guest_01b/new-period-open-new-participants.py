"""new-period-open-new-participants (Alex's Options, guest).

Claim: each new period open brings a new participant group; the new period's early
direction either CONFIRMS the previous period (continues its colour) or FLIPS it (the
reversal candidate) - either way the new period's early direction is what to trade, and a
new period that prints a 1 (inside) means nobody is in control (no trade).

Operationalisation (day trading: 'the relevant new opens are the hour and the day'):
  period = trading day (18:00 NY open). 'First bars' = the first 1h candle of the day
  (18:00-19:00 NY). Decide at its close.
  previous-period direction = colour of the prior trading day (close vs open).
  new-period direction = colour of the day so far (first-hour close vs day open).
  1-invalidation, applied on the hour fractal ('every hour is like a new day'): skip when
  the first hour is an inside bar of the preceding 1h candle.
  Trade the new-period direction (flip and confirm alike), enter next M1 open, stop at
  0.5 x prior-day range, no target, exit 16:00 NY (21h hold, inside the same day).
  Column `flip` records flips (diagnostic only).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd

STOP_K = 0.5
MIN_DAY_M1 = 600
MIN_HOUR_M1 = 30


def detect(m1):
    h = cl.build_bars(m1, "1h")
    d = cl.build_bars(m1, "1D")
    hny = cl.to_ny(h.index)
    first = h[(hny.hour == 18) & (h["n_m1"].to_numpy() >= MIN_HOUR_M1)]
    # the 1h candle before each first hour (the last hour of the prior session)
    pos = h.index.get_indexer(first.index)
    ok = pos >= 1
    first, pos = first[ok], pos[ok]
    prevh = h.iloc[pos - 1]
    # prior complete trading day: day bar whose close_time <= first-hour open
    dct = pd.DatetimeIndex(d["close_time"])
    j = np.searchsorted(dct.asi8, first.index.asi8, side="right") - 1
    ok = j >= 0
    first, prevh, j = first[ok], prevh.iloc[np.nonzero(ok)[0]], j[ok]
    pdb = d.iloc[j]
    keep = (pdb["n_m1"].to_numpy() >= MIN_DAY_M1)
    # prior day must be the immediately preceding session (no multi-day data hole)
    gap = (first.index - pd.DatetimeIndex(pdb["close_time"])) <= pd.Timedelta("3D")
    keep &= np.asarray(gap)
    prev_col = np.sign(pdb["close"].to_numpy() - pdb["open"].to_numpy())
    new_col = np.sign(first["close"].to_numpy() - first["open"].to_numpy())
    inside = (first["high"].to_numpy() <= prevh["high"].to_numpy()) & \
             (first["low"].to_numpy() >= prevh["low"].to_numpy())
    keep &= (prev_col != 0) & (new_col != 0) & ~inside
    close = pd.DatetimeIndex(first["close_time"])[keep]
    rngp = (pdb["high"].to_numpy() - pdb["low"].to_numpy())[keep]
    return pd.DataFrame({
        "decision_time": close, "available_at": close,
        "direction": new_col[keep].astype(int),
        "stop_dist": STOP_K * rngp,
        "rr": np.nan,
        "flip": (new_col != prev_col)[keep],
    }).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("tg01b_newopen_day_1h", lambda: detect(cl.load_m1()))
    print(len(ev), "events; flip share", ev["flip"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold="21h", claim="+", hold_basis="bars")
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "period = trading day (18:00 NY open); first bars = first 1h candle (18:00-19:00 NY); decide at its close",
        "previous-period direction = prior trading-day colour (close vs open); new direction = first-hour close vs day open",
        "skip if the first hour is an inside bar (a 1) of the preceding 1h candle; skip prior-day stubs (<600 M1) or zero-colour candles",
        "trade the new-period direction (flip = reversal candidate, same colour = confirmation); enter next M1 open",
        "stop 0.5 x prior-day range; no target; exit after 21h (16:00 NY, same session)"],
        "params": {"period": "1D (18:00 NY)", "first_bars": "first 1h candle", "inside_check": "vs preceding 1h candle",
                   "stop": "0.5 x prior-day range", "target": "none", "max_hold": "21h",
                   "min_day_m1": MIN_DAY_M1, "min_hour_m1": MIN_HOUR_M1, "hold_basis": "bars"}}
    src = {"period": "corpus: 1XWyy6Q-_8Q 'every single time frame that opens' - yaml: for day trading the relevant opens are the hour and the day",
           "first_bars": "declared-before-run: 'how quickly after the open' is unbounded (yaml ambiguity); first hourly candle = the LTF named in the yaml",
           "inside_check": "declared-before-run: yaml invalidation 'prints a 1', applied on the hour fractal ('every hour is like a new day', 1XWyy6Q-_8Q)",
           "stop": "declared-before-run: no stop given; half the prior-day range (ATR units)",
           "target": "declared-before-run: no target given; hold for the rest of the period",
           "max_hold": "declared-before-run: to 16:00 NY, before the 17:00 halt",
           "min_day_m1": "declared-before-run: stub-session guard (README trap 6)",
           "min_hour_m1": "declared-before-run: stub-hour guard",
           "hold_basis": "declared-before-run: README trap 7 - first clock-basis run showed exposure_bars real 1243 vs control 1090 (>10%), so rerun on trading-time basis as the README prescribes"}
    p = cl.write_result("new-period-open-new-participants", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes=f"Rerun once with hold_basis=bars per README trap 7 (clock run: NULL, diff +0.004 [-0.052,+0.061], exposure 1243 vs 1090). flip share {ev['flip'].mean():.3f}. Hourly/monthly/quarterly opens not separately tested; day open is the day-trading reading.")
    print(p)
