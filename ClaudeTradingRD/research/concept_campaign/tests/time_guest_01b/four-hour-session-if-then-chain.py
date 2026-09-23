"""four-hour-session-if-then-chain (GxTradez, guest).

Claim: if the 02:00 4H candle manipulates, expect 06:00 to continue away from it; if 06:00
manipulates, 10:00 continues; if 10:00 manipulates, 14:00 continues (New York times, the
futures 4H grid 18/22/02/06/10/14 as stated). Continuation requires a draw on liquidity
still open.

Operationalisation (trade_test):
  manipulation = the candle trades beyond ONE side of the previous 4H candle (sweeps its
  low or high, not both) and closes back inside, on the non-swept side of the swept level.
  Decide at that candle's close; trade away from the manipulation (swept low -> long).
  stop = the manipulation candle's swept extreme; target = the previous 4H candle's
  opposite extreme (the open draw), required to be beyond the entry reference (else no
  open draw -> no trade); max hold = the continuation candle (4h).
  Chain candles only: manipulating candle opening 02:00, 06:00 or 10:00 NY.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd

GRID = "futures"
CHAIN_HOURS = (2, 6, 10)


def detect(m1):
    b = cl.build_bars(m1, "4h", grid4h=GRID)
    b = b[b["n_m1"] >= 60]
    o, h, l, c = (b[k].to_numpy() for k in ("open", "high", "low", "close"))
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    ct = pd.DatetimeIndex(b["close_time"])
    prev_ct = np.r_[np.datetime64("NaT"), ct[:-1].tz_localize(None).to_numpy()]
    start_ny = cl.to_ny(b.index)
    contiguous = (b.index.tz_localize(None).to_numpy() - prev_ct) <= np.timedelta64(1, "h")
    chain = np.isin(start_ny.hour, CHAIN_HOURS) & np.asarray(contiguous)
    sw_lo = (l < pl) & ~(h > ph) & (c > pl)
    sw_hi = (h > ph) & ~(l < pl) & (c < ph)
    long_ok = chain & sw_lo & (ph > c)
    short_ok = chain & sw_hi & (pl < c)
    sel = long_ok | short_ok
    d = np.where(long_ok, 1, -1)[sel]
    t = ct[sel]
    return pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                         "stop_px": np.where(long_ok, l, h)[sel],
                         "target_px": np.where(long_ok, ph, pl)[sel],
                         "chain_hour": start_ny.hour[sel]}).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("tg01b_4h_chain_futures", lambda: detect(cl.load_m1()))
    print(len(ev), ev["chain_hour"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold="4h", claim="+")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": ["4H bars on the futures grid (18/22/02/06/10/14 NY); candles with <60 M1 or not contiguous with the previous 4H candle skipped",
                    "manipulation: the 02:00 / 06:00 / 10:00 NY candle sweeps exactly one side of the previous 4H candle and closes back on the inside of the swept level",
                    "decide at its close; trade away from the sweep (swept low -> long) into the next chain candle (06:00 / 10:00 / 14:00)",
                    "stop = the swept extreme of the manipulation candle; target = previous candle's opposite extreme, required beyond the close (open draw on liquidity)",
                    "max hold 4h = the continuation candle"],
          "params": {"grid4h": GRID, "chain_pairs": "02->06, 06->10, 10->14",
                     "manipulation": "one-sided sweep of prior 4H candle, close back inside",
                     "stop": "swept extreme", "target": "prior 4H opposite extreme", "max_hold": "4h",
                     "min_bar_m1": 60}}
    src = {"grid4h": "corpus: J_EeS2_2CAM - the stated 2am/6am/10am/14:00 candles are the futures grid (README trap 8: grid recorded)",
           "chain_pairs": "corpus: J_EeS2_2CAM yaml definition (18:00-22:00 link garbled in transcript -> omitted)",
           "manipulation": "corpus: yaml detection rule 'manipulated (swept a prior high or low)'; close-back-inside declared-before-run to separate manipulation from expansion",
           "stop": "declared-before-run: no stop stated; the manipulation extreme is the level traded away from",
           "target": "corpus: yaml 'continuation requires a draw on liquidity still to be open' - nearest open draw = prior candle's opposite extreme",
           "max_hold": "corpus: the continuation is the next 4H candle",
           "min_bar_m1": "declared-before-run: stub-bar guard"}
    p = cl.write_result("four-hour-session-if-then-chain", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="The 'large opposing wick in the candle in play -> wait' clause concerns the continuation candle's own future wick and is not applied. Index-futures concept applied to XAUUSD with the stated clock.")
    print(p)
