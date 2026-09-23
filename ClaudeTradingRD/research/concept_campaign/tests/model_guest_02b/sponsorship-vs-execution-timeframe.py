"""sponsorship-vs-execution-timeframe (guest: Ben, yRmKkR4CojU).

"the first model is the sponsorship, the second model is your execution":
the HTF PD array price has reached fixes the TARGET ("weekly sponsorship means
weekly target"), a lower-timeframe shift inside that array fixes the ENTRY and
the stop (the execution model's swing). Trade test of that full two-model trade:

  sponsorship  a 4H (forex grid) three-candle FVG, live for 30 4H bars after it
               forms; the array FAILS at the first 4H CLOSE beyond its defending
               (far) edge (his stated invalidation)
  execution    the FIRST 5m CISD (phase-3 config) in the gap's direction whose
               protected swing formed after the gap and lies inside the gap
               (price arrived into the array and shifted there), confirmed while
               the array is live
  stop         the execution model's protected swing
  target       the sponsoring timeframe's liquidity: the most recent confirmed 4H
               2/2 swing high (low) beyond the entry, searched back 30 days
  hold         10 sponsoring-TF bars (40h)
One trade per sponsoring array (re-entry rules are not given).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.primitives import fair_value_gaps, swing_points

GRID = "forex"
LIVE_BARS = 30
TGT_LOOKBACK = np.timedelta64(30, "D")
MAX_HOLD = "40h"


def detect(m1):
    H = cl.build_bars(m1, "4h", grid4h=GRID)
    H = H[H["n_m1"] > 0]
    nh = len(H)
    hc = cl.data.utc_ns(H["close_time"])
    hh, hl, hcl = H["high"].to_numpy(), H["low"].to_numpy(), H["close"].to_numpy()
    g = fair_value_gaps(H)
    sw = swing_points(H, 2, 2)
    pos = np.arange(nh)
    mh = sw["swing_high"].to_numpy() & (pos + 2 < nh)
    ml = sw["swing_low"].to_numpy() & (pos + 2 < nh)
    sh_t, sh_p = hc[pos[mh] + 2], hh[mh]
    sl_t, sl_p = hc[pos[ml] + 2], hl[ml]

    F = cl.build_bars(m1, "5min")
    F = F[F["n_m1"] > 0]
    cz = cisd_events(F[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    ct = cl.data.utc_ns(F.loc[cz["confirm_time"], "close_time"])
    ext_t = cl.data.utc_ns(F.loc[cz["extreme_time"], "first_m1"])
    cbull = (cz["direction"] == "bullish").to_numpy()
    px = cz["protected_swing"].to_numpy()
    cclose = cz["confirm_close"].to_numpy()
    order = np.argsort(ct, kind="stable")
    ct, ext_t, cbull, px, cclose = ct[order], ext_t[order], cbull[order], px[order], cclose[order]

    rows = []
    for bull in (True, False):
        gi = np.where(g["bullish_fvg" if bull else "bearish_fvg"].to_numpy())[0]
        glo_all, ghi_all = g["gap_low"].to_numpy(), g["gap_high"].to_numpy()
        for i in gi:
            glo, ghi = glo_all[i], ghi_all[i]
            t0 = hc[i]
            last = min(i + LIVE_BARS, nh - 1)
            end = hc[last] if i + LIVE_BARS < nh else np.datetime64("2100-01-01", "ns")
            # invalidation: first 4H close beyond the defending edge
            for j in range(i + 1, min(i + LIVE_BARS, nh - 1) + 1):
                if (bull and hcl[j] < glo) or ((not bull) and hcl[j] > ghi):
                    end = hc[j]
                    break
            a = np.searchsorted(ct, t0, side="right")
            b = np.searchsorted(ct, end, side="left")      # decisions strictly before end
            for k in range(a, b):
                if cbull[k] != bull or ext_t[k] < t0:
                    continue
                if not (glo <= px[k] <= ghi):
                    continue
                if bull and cclose[k] <= px[k] or (not bull) and cclose[k] >= px[k]:
                    continue
                # sponsoring-TF target
                if bull:
                    m = (sh_t <= ct[k]) & (sh_t > ct[k] - TGT_LOOKBACK) & (sh_p > cclose[k])
                    cand_t, cand_p = sh_t[m], sh_p[m]
                else:
                    m = (sl_t <= ct[k]) & (sl_t > ct[k] - TGT_LOOKBACK) & (sl_p < cclose[k])
                    cand_t, cand_p = sl_t[m], sl_p[m]
                if not len(cand_t):
                    break                                   # no sponsoring target -> no trade
                tgt = cand_p[np.argmax(cand_t)]
                rows.append((ct[k], 1 if bull else -1, px[k], tgt, t0))
                break
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px",
                                     "array_time"])
    ev["decision_time"] = pd.DatetimeIndex(ev["decision_time"]).tz_localize("UTC")
    ev["array_time"] = pd.DatetimeIndex(ev["array_time"]).tz_localize("UTC")
    ev["available_at"] = ev["decision_time"]
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("sponsor_4hfvg_5mcisd", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "sponsorship: 4H forex-grid 3-candle FVG, live 30 4H bars; fails at the first 4H close "
        "beyond its far edge",
        "execution: first 5m CISD (series_open, 2/2, max_wait 3) in the gap's direction whose "
        "protected swing formed after the gap and lies inside it, confirmed while live",
        "enter next M1 open after the 5m confirm close; stop = protected swing",
        "target = most recent confirmed 4H 2/2 swing beyond the entry (<=30 days old) - the "
        "sponsoring timeframe's liquidity; hold 40h; one trade per array"],
        "params": {"sponsor_tf": "4h", "exec_tf": "5min", "grid4h": GRID,
                   "live_bars": LIVE_BARS, "target_lookback": "30D", "max_hold": MAX_HOLD,
                   "cisd": "phase3 locked"}}
    src = {"sponsor_tf": "corpus: yRmKkR4CojU (concept htf 1W/1D/4H; 4H chosen for sample, "
                         "declared-before-run)",
           "exec_tf": "corpus: yRmKkR4CojU 'he executes on 1m, 2m and 5m'",
           "grid4h": "session_window_fit / data.py forex grid default (carried as knob)",
           "live_bars": "declared-before-run: array live 30 4H bars (~1 trading week)",
           "target_lookback": "declared-before-run: sponsoring-TF liquidity within 30 days",
           "max_hold": "phase3: 10 bars - of the SPONSORING timeframe, since the target is "
                       "the sponsor's ('weekly sponsorship means weekly target')",
           "cisd": "phase3: locked CISD config"}
    print(cl.write_result("sponsorship-vs-execution-timeframe", None, res,
                          operationalization=op, params_source=src, script=__file__,
                          probe=probe,
                          notes="Tests the two-model trade (HTF array target, LTF execution "
                                "entry/stop) against a matched random entry with the same "
                                "stop/target geometry."))
