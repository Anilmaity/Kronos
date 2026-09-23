"""decoupling-realignment (TTrades own voice) — batch structure_own_05a.

"something has to come back into alignment" (xraklBJHW5k): when correlated assets decouple
- one strongly directional on the day, the other flat or opposite - alignment is restored
next session, either by the LEADER giving back or the LAGGARD catching up, and the
realigning asset's target is the previous day's low/high (worked example: YM sharply
bullish, NQ/ES flat; next session YM came back, target the previous day's low).
The corpus gives no rule for WHICH asset realigns, so the two ways are tested as two
readings, each as the trade it implies on gold. Transfer: the campaign has no index
futures; silver is the method's sanctioned gold correlate (method_spec §2.6).

Decoupled day (completed 18:00-NY trading day, gold full session, silver >= 18 H1 bars):
  move z = day's close-to-close return / mean |return| of the 20 prior days (own asset)
  leader: |z| >= 1.0; the other: |z| <= 0.25 (flat) or opposite sign (and not itself |z|>=1)
reading a (leader gives back): gold is the leader -> trade gold AGAINST its day's move at
  the next session open; target = the decoupling day's opposite extreme (its low after an
  up day, as in the example), stop = the day's extreme in the move's direction.
reading b (laggard catches up): silver is the leader, gold the laggard -> trade gold IN
  silver's direction; target = gold's decoupling-day extreme in that direction (PDH for
  up), stop = its other extreme.
Hold: one trading session (23h of trading time, hold_basis='bars').
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05a")
from _common import cl, corr_h1, daily_from_h1, np, pd, summary  # noqa: E402

CID = "decoupling-realignment"
LB = 20
LEAD_Z = 1.0
FLAT_Z = 0.25
MIN_GOLD_M1 = 600
MIN_XAG_H1 = 18
MAX_HOLD = "23h"
HOLD_BASIS = "bars"


def _z(ret: pd.Series) -> pd.Series:
    return ret / ret.abs().rolling(LB, min_periods=LB).mean().shift(1)


def detect(m1: pd.DataFrame, reading: str) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    g = cl.build_bars(m1, "1D")
    x = corr_h1("xag", m1, drop_halt_hour=True, cut="gold_last")
    if len(g) < LB + 5 or len(x) < 24 * (LB + 5):
        return pd.DataFrame(columns=cols)
    g = g[g["n_m1"] > MIN_GOLD_M1].set_index("trading_day")
    s = daily_from_h1(x)
    s = s[s["n_h1"] >= MIN_XAG_H1]
    j = g[["high", "low", "close", "close_time"]].join(
        s[["close", "close_time"]].rename(columns={"close": "xc", "close_time": "xct"}), how="inner")
    j["gz"] = _z(j["close"].pct_change())
    j["sz"] = _z(j["xc"].pct_change())
    j = j.dropna(subset=["gz", "sz"])
    gz, sz = j["gz"].to_numpy(), j["sz"].to_numpy()

    def lead(a, b):   # a leads, b flat or opposite (and not itself strongly opposite)
        return (np.abs(a) >= LEAD_Z) & ((np.abs(b) <= FLAT_Z) |
                                         ((np.sign(b) == -np.sign(a)) & (np.abs(b) < LEAD_Z)))
    if reading == "a":
        sel = lead(gz, sz)
        d = -np.sign(gz)
    else:
        sel = lead(sz, gz)
        d = np.sign(sz)
    f = j[sel].copy()
    d = d[sel].astype(int)
    hi, lo = f["high"].to_numpy(float), f["low"].to_numpy(float)
    ct = pd.DatetimeIndex(f["close_time"])
    xct = pd.DatetimeIndex(f["xct"])
    out = pd.DataFrame({"decision_time": ct, "available_at": ct.where(xct <= ct, xct),
                        "direction": d,
                        "stop_px": np.where(d > 0, lo, hi),
                        "target_px": np.where(d > 0, hi, lo)})
    out = out[pd.DatetimeIndex(out["available_at"]) <= pd.DatetimeIndex(out["decision_time"])]
    return out.reset_index(drop=True)[cols]


def main():
    for reading in ("a", "b"):
        fn = lambda m, r=reading: detect(m, r)   # noqa: E731
        ev = cl.cache_frame(f"decouple_{reading}_lb{LB}_{LEAD_Z}_{FLAT_Z}",
                            lambda r=reading: detect(cl.load_m1(), r))
        print("reading", reading, "events", len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(fn, ev, lookback="60D")
        res = cl.trade_test(ev, max_hold=MAX_HOLD, hold_basis=HOLD_BASIS, claim="+")
        print(summary(res))
        common = [
            "trading day = 18:00 NY roll; gold sessions with <= 600 M1 bars and silver days with "
            "< 18 H1 bars dropped; silver = XAG_USD H1 (OANDA) aggregated to the same day, its 17:00-NY (gold halt) "
            "hour dropped so the silver day is complete at gold's last M1 close",
            "z = day's close-to-close return / mean |return| of the 20 prior days (per asset)",
            "leader |z| >= 1.0; the other |z| <= 0.25 or opposite sign with |z| < 1.0",
        ]
        if reading == "a":
            rr = ["gold is the leader -> at the day's close trade gold against its own move "
                  "(enter next M1 open); target = the day's opposite extreme, stop = the day's "
                  "extreme in the move's direction"]
        else:
            rr = ["silver is the leader, gold flat/opposite -> trade gold in silver's direction "
                  "(enter next M1 open); target = gold's day extreme in that direction, stop = "
                  "its other extreme"]
        op = {"rules": common + rr + ["exit after one session: 23h of trading time (hold_basis bars)"],
              "params": {"tf": "1D", "correlate": "XAG_USD H1 -> 1D", "z_lookback": LB,
                         "lead_z": LEAD_Z, "flat_z": FLAT_Z, "max_hold": MAX_HOLD,
                         "hold_basis": HOLD_BASIS, "min_gold_m1": MIN_GOLD_M1,
                         "min_xag_h1": MIN_XAG_H1}}
        src = {"tf": "corpus: xraklBJHW5k daily divergence / percent change (yaml htf 1D)",
               "correlate": "method_spec: §2.6 silver is the method's sanctioned gold correlate; campaign holds no ES/NQ/YM",
               "z_lookback": "phase3: lookback 20 knob",
               "lead_z": "declared-before-run: 'strongly directional' = at least a typical day's move (example: YM -0.63%, about one typical day then)",
               "flat_z": "declared-before-run: 'roughly flat' = a quarter of a typical day's move",
               "max_hold": "corpus: xraklBJHW5k 'the next session YM was the asset that came back'",
               "hold_basis": "declared-before-run: README trap 7 - a Friday-close decision must hold a full session of trading time",
               "min_gold_m1": "declared-before-run: README trap 6 stub-session guard",
               "min_xag_h1": "declared-before-run: stub-session guard for the correlate"}
        p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe,
                            notes="Transfer ES/NQ/YM -> XAU/XAG. The corpus admits it cannot say in "
                                  "advance which asset realigns (he inferred it after the fact), so "
                                  "each branch is a separate reading; both targets are the previous "
                                  "day's extreme as in the worked example. Stop is unstated; the "
                                  "decoupling day's other extreme is used.")
        print("wrote", p)


if __name__ == "__main__":
    main()
