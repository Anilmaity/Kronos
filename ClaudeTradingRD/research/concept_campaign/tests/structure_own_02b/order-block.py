"""order-block — trade_test, two readings (contested: the two validations are not reconciled).

His model: price raids a short-term high (bearish case) — the raid of a high is itself a
POI (method_spec §4.1 "a high being taken out") — the up-close candle(s) of the move that
swept it are the block; the block is validated only when price CLOSES back through it; the
level traded from is the block's OPENING PRICE (open of the first candle of the series);
stop beyond the block's extreme (the swept high); retest entry.
Readings (YAML: "the structural version requires ... close back below their low, the candle
version requires only a close beyond the block's opening price"):
  (a) structural validation — a close below the LOW of the up-close series (series_extreme)
  (b) candle / propulsion validation — a close below the series' OPENING PRICE (series_open)
Detector: 1h 2/2 swing extreme that exceeded the most recent confirmed swing high before it
(the raid), its contiguous up-close run (<= 10 candles), validation close within 3 bars
(phase-3 max_wait). Entry: first M1 retest of the opening price within 24 x 1h after the
validating close, before price trades beyond the extreme -> short at the next M1 open, stop =
the extreme, 2R, hold 10h. Mirror for bullish blocks.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, ns, empty, cisd_frame, bar_arrays, M1, first_touch, ONE_MIN  # noqa: E402

CID = "order-block"
TF, WAIT_H, HOLD, RR, RIGHT = "1h", 24, "10h", 2.0, 2
LEVEL_RULE = {"a": "series_extreme", "b": "series_open"}
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]


def make_detect(reading: str):
    def detect(m1: pd.DataFrame) -> pd.DataFrame:
        b = cl.build_bars(m1, TF)
        if len(b) < 30:
            return empty(COLS)
        d = bar_arrays(b)
        ev = cisd_frame(b, level_rule=LEVEL_RULE[reading])
        if ev.empty:
            return empty(COLS)
        sh_idx, sl_idx = np.flatnonzero(d["sh"]), np.flatnonzero(d["sl"])
        m = M1(m1)
        ct = d["ct"]
        rows = []
        for r in ev.itertuples(index=False):
            x, s, cp = int(r.ext_pos), int(r.s_pos), int(r.conf_pos)
            up = r.sgn == 1                                     # bullish block (raid of a low)
            piv = sl_idx if up else sh_idx
            prior = piv[piv + RIGHT <= x - 1]
            if not len(prior):
                continue
            p = prior[-1]
            raided = (d["l"][x] < d["l"][p]) if up else (d["h"][x] > d["h"][p])
            if not raided:
                continue
            level = d["o"][s]                                   # block opening price
            ext = float(r.protected_swing)
            if not ((ext < level) if up else (ext > level)):
                continue
            t0, t1 = ct[cp], ct[min(cp + WAIT_H, len(ct) - 1)]
            if t1 <= t0:
                continue
            j = first_touch(m, t0, t1, level, up, cancel=ext)
            if j < 0:
                continue
            if (m.l[j] <= ext) if up else (m.h[j] >= ext):
                continue
            rows.append((m.t[j] + ONE_MIN, 1 if up else -1, ext))
        if not rows:
            return empty(COLS)
        out = pd.DataFrame(rows, columns=["t", "direction", "stop_px"])
        t = pd.DatetimeIndex(pd.to_datetime(out["t"].to_numpy(np.int64), utc=True))
        return pd.DataFrame({"decision_time": t, "available_at": t, "direction": out["direction"].to_numpy(),
                             "stop_px": out["stop_px"].to_numpy(), "rr": RR}
                            ).sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)[COLS]
    return detect


SRC = {"tf": "corpus: YAML ltf [1H, 5m, 1m] under htf [1W, 1D, 4H]; method_spec §1.2 hourly structure TF",
       "swing": "phase3: 2/2 fractal swings (§1.8)",
       "max_wait": "phase3: CISD max_wait 3 (the OB validation close is the CISD close, detectors/blocks.py)",
       "raid": "corpus: YAML 'Price raids the short-term high ... into the important level'; method_spec §4.1 a high taken out is a POI",
       "level": "corpus: YAML 'Mark the block's opening price; that is the level expected to support price'",
       "wait_h": "declared-before-run: the retest must come within 24 x 1h of validation",
       "rr": "phase3: 2R (YAML targets 'opposing liquidity' not mechanically defined)",
       "max_hold": "phase3: 10 structure-TF bars",
       "stop": "corpus: YAML execution 'Beyond the block's extreme (the swept high/low)'"}
READ_SRC = {"a": "corpus: YAML 'Bearish: ... the zone becomes valid once price closes back below their low'",
            "b": "corpus: YAML 'Alternative validation used in the propulsion-block video: ... closes beyond the OPENING PRICE'"}

if __name__ == "__main__":
    rd = sys.argv[1]
    detect = make_detect(rd)
    ev = cl.cache_frame(f"{CID}_{rd}_{TF}", lambda: detect(cl.load_m1()))
    print(rd, len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe["passed"])
    res = cl.trade_test(ev, max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p", "mde",
                                   "win_rate", "exposure_bars", "ties", "ctrl_overlap")})
    op = {"rules": [
        "1h bars; 2/2 swing extreme that exceeds the most recent swing confirmed before it (raid of a short-term high/low)",
        "block = the contiguous opposing-close run (<= 10 candles) into that extreme (detectors.cisd run)",
        f"validation = a close through the run's {'extreme (low of up-close / high of down-close run)' if rd == 'a' else 'opening price'} "
        "within 3 bars of the run end / swing confirmation",
        "entry = first M1 retest of the block's opening price (open of the first run candle) within 24 x 1h after the "
        "validating close, cancelled if price trades beyond the extreme first; decide at that M1 close",
        "stop = the extreme; 2R; hold 10h"],
        "params": {"tf": TF, "swing": "2/2", "max_wait": 3, "level_rule": LEVEL_RULE[rd], "level": "block open",
                   "wait_h": WAIT_H, "rr": RR, "max_hold": HOLD, "raid": "swept last confirmed swing"}}
    p = cl.write_result(CID, rd, res, operationalization=op, params_source={**SRC, "level_rule": READ_SRC[rd]},
                        script=__file__, probe=probe,
                        notes="the 'important level' is taken as the raided short-term swing itself (a POI per §4.1); "
                              "HTF PD-array confluence and the 0.5 mean-threshold refinement are not modelled")
    print(p)
