"""four-entry-models — (batch model_own_04a).

The four numbered entry models (plus BPR). Model 1 = liquidity grab -> break of
structure with displacement -> entry on the retracement into the resulting FVG;
model 3 = model 1 with the entry inside the OTE of the displacement leg.
  reading a (trade_test): model 1 as a full trade, 1-minute execution, New York open
  reading b (gate_test):  model 3 vs model 1 — does requiring the entry to sit in the
                          0.62-0.79 OTE of the displacement leg improve the model-1 book?
Models 2/4 (internal range liquidity taken first) and 5 (BPR) are not tested: IRL
is "used as a gate without threshold" and BPR is its own concept (balanced-price-range-overlap).

Declared operationalisation (before run):
  * execution TF 1m (he uses 1-minute and 15-second; no sub-minute data)
  * swings: three-candle fractal; a grab = a 1m bar trading below an untaken swing low
    formed within the previous 60 min (mirror for shorts)
  * BOS = the first 1m CLOSE above the last confirmed swing high formed before the grab,
    within 15 bars of the grab; displacement evidenced by the FVG the leg leaves: the
    first bullish FVG whose third bar is after the grab and no later than one bar after
    the break
  * setup must complete inside the New York open kill zone 08:30-11:00 NY
  * entry: first 1m bar trading back to the gap top within 15 min of the setup; decide at
    its close, enter next M1 open. stop beyond the grab extreme; 2R target; 60 min hold
  * OTE (reading b): (leg_high - gap_top) / (leg_high - grab_low) in [0.62, 0.79], leg
    high = highest high from the grab to the setup completion
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

KZ = ("08:30", "11:00")
SWING_LB = 60
BOS_WAIT = 15
FILL_WAIT = 15
OTE = (0.62, 0.79)
MAX_HOLD = "60min"


def one_side(t, O, H, L, C, active_mask, d):
    """Bullish logic on (possibly mirrored) arrays. Returns rows
    (setup_idx, fill_idx, stop, gap_top, leg_high, grab_low)."""
    if d == -1:
        O, H, L, C = -O, -L, -H, -C
    n = len(H)
    sl = np.zeros(n, bool)
    sh = np.zeros(n, bool)
    sl[1:-1] = (L[1:-1] < L[:-2]) & (L[1:-1] < L[2:])
    sh[1:-1] = (H[1:-1] > H[:-2]) & (H[1:-1] > H[2:])
    rows = []
    lows, highs = [], []
    MIN = 60_000_000_000
    for j in range(2, n):
        # swings at j-2 are confirmed by bar j-1, usable at bar j
        k = j - 2
        if k >= 1:
            if sl[k]:
                lows.append(k)
            if sh[k]:
                highs.append(k)
        lows = [x for x in lows if t[j] - t[x] <= SWING_LB * MIN]
        highs = [x for x in highs if t[j] - t[x] <= 4 * SWING_LB * MIN]
        swept = [x for x in lows if L[j] < L[x]]
        if not swept:
            continue
        lows = [x for x in lows if x not in swept]      # taken, in or out of the kill zone
        if not active_mask[j]:
            continue
        g = j
        prior = [x for x in highs if x < g]
        if not prior:
            continue
        bos_lvl = H[prior[-1]]
        grab_low = L[g]
        brk = -1
        for b in range(g, min(g + BOS_WAIT + 1, n)):
            grab_low = min(grab_low, L[b])
            if C[b] > bos_lvl:
                brk = b
                break
            if t[b] - t[g] > BOS_WAIT * MIN:
                break
        if brk < 0:
            continue
        fvg = -1
        for f in range(g + 2, min(brk + 2, n)):
            if L[f] > H[f - 2]:
                fvg = f
                break
        if fvg < 0:
            continue
        s = max(brk, fvg)
        if not active_mask[s]:
            continue
        top = L[fvg]
        leg_high = H[g:s + 1].max()
        for u in range(s + 1, n):
            if t[u] - t[s] > FILL_WAIT * MIN:
                break
            if L[u] <= grab_low:
                break
            if L[u] <= top:
                rows.append((s, u, grab_low, top, leg_high, grab_low))
                break
    if d == -1:
        rows = [(s, u, -st, -tp, -lh, -gl) for (s, u, st, tp, lh, gl) in rows]
    return rows


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "setup_time",
            "ote_depth", "in_ote"]
    t = m1.index.as_unit("ns").asi8
    O, H, L, C = (m1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    act = cl.in_window(m1.index, *KZ)
    ONE = 60_000_000_000
    out = []
    for d in (1, -1):
        for (s, u, st, tp, lh, gl) in one_side(t, O, H, L, C, act, d):
            depth = (lh - tp) / (lh - gl) if lh != gl else np.nan
            out.append((t[u] + ONE, d, st, t[s] + ONE, depth))
    if not out:
        return pd.DataFrame(columns=cols)
    ev = pd.DataFrame(out, columns=["decision_time", "direction", "stop_px", "setup_time",
                                    "ote_depth"])
    ev["decision_time"] = pd.to_datetime(ev["decision_time"], utc=True)
    ev["setup_time"] = pd.to_datetime(ev["setup_time"], utc=True)
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = 2.0
    ev = ev[np.isfinite(ev["ote_depth"])]
    ev["in_ote"] = (ev["ote_depth"] >= OTE[0]) & (ev["ote_depth"] <= OTE[1])
    ev = (ev.sort_values(["decision_time", "setup_time", "direction"], kind="stable")
            .drop_duplicates(["decision_time"], keep="first"))
    return ev[cols].reset_index(drop=True)


PARAMS = {"entry_tf": "1min", "swing": "1/1 fractal", "grab_swing_lookback_min": SWING_LB,
          "bos_wait_bars": BOS_WAIT, "fvg": "first FVG after grab to break+1",
          "killzone": "08:30-11:00 NY", "fill_wait_min": FILL_WAIT, "stop": "grab extreme",
          "rr": 2.0, "max_hold": MAX_HOLD}
SRC = {"entry_tf": "corpus: four-entry-models 'he uses 1-minute and 15-second'",
       "swing": "method_spec: §1.1 three-candle fractal",
       "grab_swing_lookback_min": "declared-before-run: swings formed in the prior hour",
       "bos_wait_bars": "declared-before-run: the break must follow the grab within 15 bars",
       "fvg": "corpus: A8UpRZlRzlg 'the classic fair value Gap setup liquidity grab break a structure fair value Gap'",
       "killzone": ("corpus: A8UpRZlRzlg 'the next thing you need to know is which kill zones you enter in' "
                    "(he trades the New York open); hours from KILLZONES ix_ny_am (killzones.yaml)"),
       "fill_wait_min": "declared-before-run: 15 minutes for the retrace into the gap",
       "stop": "corpus: four-entry-models execution 'Beyond the swing or the candle bodies that formed the level'",
       "rr": "method_spec: §5.3 2R floor",
       "max_hold": "declared-before-run: 60 one-minute bars"}
RULES = ["1m 3-candle swings; grab = a bar trading below an untaken swing low formed in the prior "
         "60 min (mirror above highs for shorts), inside 08:30-11:00 NY",
         "BOS = first close above the last swing high formed before the grab within 15 bars; the "
         "leg's first FVG (third bar after the grab, <= break+1) is the entry gap",
         "entry: first 1m bar back to the gap's near edge within 15 min of the setup; decide at "
         "its close, enter next M1 open; stop at the grab extreme; 2R; 60 min hold"]


def run(reading):
    ev = cl.cache_frame("four_entry_models_m1_nyopen", lambda: detect(cl.load_m1()))
    print("events", len(ev), "in_ote", float(ev["in_ote"].mean()))
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    if reading == "a":
        res = cl.trade_test(ev, max_hold=MAX_HOLD)
        op = {"rules": RULES + ["model 1 as traded, all setups"], "params": PARAMS}
        src = SRC
    else:
        res = cl.gate_test(ev, "in_ote", mask_available_at="setup_time", max_hold=MAX_HOLD)
        op = {"rules": RULES + ["gate (model 3): gap top sits 0.62-0.79 retraced of the leg from "
                                "the grab extreme to the leg high at setup; complement = model-1 "
                                "setups outside the OTE"],
              "params": {**PARAMS, "ote_band": list(OTE)}}
        src = {**SRC, "ote_band": "corpus: optimal-trade-entry 'the retracement into the 0.62 to 0.79 band'"}
    p = cl.write_result("four-entry-models", reading, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Models 2/4 (IRL) and 5 (BPR) not tested; no sub-minute data.")
    print(reading, p)
    for k in ("n", "n_complement", "gate_firing_rate", "avg_R", "win_rate", "diff", "ci_lo",
              "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars", "ties",
              "ctrl_overlap"):
        print("  ", k, res.get(k))


if __name__ == "__main__":
    for r in sys.argv[1:] or ["a", "b"]:
        run(r)
