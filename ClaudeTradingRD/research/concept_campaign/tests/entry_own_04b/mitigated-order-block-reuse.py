"""mitigated-order-block-reuse — gate_test.

Concept (r7yW6ou1LDs, Sunday Q&A): an order block / CISD level that price has already
traded into stays usable on a later tap ONLY while the drawn objective it pointed at is
untaken; once the objective is reached the block is spent and a re-tap is "not a trade".

Test: baseline book = every SECOND-AND-LATER tap of a 1h CISD order block, traded in the
block's direction; gate = the block's drawn objective still untaken at the tap's close.
claim '+': gated (objective untaken) taps beat the complement (objective already taken),
control-adjusted.

All parameters are declared here before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.primitives import swing_points

TF = "1h"
MAX_WAIT = 3          # phase3 locked CISD config
SWING = 2             # 2/2 fractal (phase3)
LIFE_BARS = 120       # block lifetime scanned for taps (5 trading days of 1h bars)
OBJ_LOOKBACK = 120    # how far back an unswept swing can be the drawn objective
RR = 2.0
MAX_HOLD = "10h"      # phase3: 10 entry-TF bars


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    ohlc = b[["open", "high", "low", "close"]]
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr",
            "obj_untaken", "block_id", "tap_no", "objective"]
    ev = cisd_events(ohlc, level_rule="series_open", left=SWING, right=SWING,
                     max_wait=MAX_WAIT, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    sw = swing_points(ohlc, left=SWING, right=SWING)
    idx = b.index
    pos_of = pd.Series(np.arange(len(idx)), index=idx)
    H, L, C = (b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy())
    ct = b["close_time"].to_numpy()
    sh_pos = np.flatnonzero(sw["swing_high"].to_numpy())
    sl_pos = np.flatnonzero(sw["swing_low"].to_numpy())
    rows = []
    for e in ev.itertuples(index=False):
        j0 = int(pos_of[e.confirm_time])
        bull = e.direction == "bullish"
        lvl = float(e.level)
        ps = float(e.protected_swing)
        # drawn objective: nearest swing (opposite side) beyond the CISD close, confirmed
        # by j0 (pos + SWING <= j0), not traded through between formation and j0.
        cand = sh_pos if bull else sl_pos
        cand = cand[(cand + SWING <= j0) & (cand >= j0 - OBJ_LOOKBACK)]
        best = np.nan
        for p in cand:
            if bull:
                px = H[p]
                if px <= C[j0] or H[p + 1:j0 + 1].max(initial=-np.inf) >= px:
                    continue
                if np.isnan(best) or px < best:
                    best = px
            else:
                px = L[p]
                if px >= C[j0] or L[p + 1:j0 + 1].min(initial=np.inf) <= px:
                    continue
                if np.isnan(best) or px > best:
                    best = px
        if np.isnan(best):
            continue                       # no drawn objective -> rule cannot be applied
        taken = False
        in_ep = False                      # currently inside a touch episode
        ep = 0                             # touch-episode counter (1 = first tap)
        traded_ep = -1
        end = min(len(idx), j0 + 1 + LIFE_BARS)
        for k in range(j0 + 1, end):
            if bull:
                if H[k] >= best:
                    taken = True
                touch_ = L[k] <= lvl
                if C[k] < ps:              # closes through the block: dead
                    break
            else:
                if L[k] <= best:
                    taken = True
                touch_ = H[k] >= lvl
                if C[k] > ps:
                    break
            if touch_ and not in_ep:
                ep += 1
                in_ep = True
            elif not touch_:
                in_ep = False
            if not touch_ or ep < 2 or traded_ep == ep:
                continue
            react = (C[k] > lvl and L[k] > ps) if bull else (C[k] < lvl and H[k] < ps)
            if not react:
                continue
            traded_ep = ep
            rows.append({"decision_time": ct[k], "available_at": ct[k],
                         "direction": 1 if bull else -1, "stop_px": ps, "rr": RR,
                         "obj_untaken": not taken, "block_id": str(idx[j0]),
                         "tap_no": ep, "objective": float(best)})
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"]).tz_convert("UTC") \
        if pd.DatetimeIndex(out["decision_time"]).tz is not None else \
        pd.DatetimeIndex(out["decision_time"]).tz_localize("UTC")
    out["available_at"] = out["decision_time"]
    out["obj_untaken"] = out["obj_untaken"].astype(bool)
    return out.sort_values(["decision_time", "block_id"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"mobr_{TF}_mw{MAX_WAIT}_life{LIFE_BARS}_obj{OBJ_LOOKBACK}",
                        lambda: detect(cl.load_m1()))
    print(len(ev), ev["obj_untaken"].mean(), ev["tap_no"].describe().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "obj_untaken", mask_available_at="decision_time",
                       max_hold=MAX_HOLD, cluster="block_id")
    for k in ("n", "n_other", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "blocks: 1h CISD (series_open level = the block's opening price; 2/2 swings; close "
        "through within 3 bars); block extreme = protected swing",
        "drawn objective: nearest confirmed 2/2 swing high (bullish; swing low bearish) beyond "
        "the CISD close, formed within 120 bars and untouched up to the CISD bar",
        "taps: touch episodes of the block level (low<=level bullish) after the CISD; episode "
        "1 = first (mitigating) tap; a trade fires on the first bar of episode>=2 that "
        "closes back beyond the level without trading through the protected swing",
        "block dies on a close through the protected swing; scanned for 120 bars",
        "entry next M1 open after the tap bar's close; stop = protected swing; target 2R; 10h",
        "gate obj_untaken: no bar from the CISD through the tap bar reached the objective",
        "baseline book = all second-and-later taps; complement = objective already taken"],
        "params": {"tf": TF, "max_wait": MAX_WAIT, "swing": SWING, "life_bars": LIFE_BARS,
                   "obj_lookback": OBJ_LOOKBACK, "rr": RR, "max_hold": MAX_HOLD,
                   "level_rule": "series_open", "cluster": "block_id"}}
    src = {"tf": "method_spec: §1.2 daily/1-hour pairing; concept timeframes ltf 1H",
           "max_wait": "phase3: locked CISD config (conjunction_preregistration §1.8-1.13)",
           "swing": "phase3: locked 2/2 swing",
           "level_rule": "method_spec: §4.2/§4.6 order block level = opening price (first-candle open default)",
           "life_bars": "declared-before-run: 5 trading days of 1h bars (no tap limit stated)",
           "obj_lookback": "declared-before-run: objective must be a swing from the last 120 1h bars",
           "rr": "method_spec: §5.3 2R floor",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "cluster": "declared-before-run: taps of one block share a cluster"}
    p = cl.write_result("mitigated-order-block-reuse", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Drawn objective is not defined mechanically in the corpus "
                              "(ambiguity 1); operationalised as the nearest unswept opposite "
                              "swing. A wick reaching the objective counts as taken.")
    print(p)
