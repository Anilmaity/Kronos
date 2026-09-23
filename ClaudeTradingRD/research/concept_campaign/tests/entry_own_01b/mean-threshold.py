"""mean-threshold — two readings (contested).

Order block = the opposing-close series the 1h CISD closes through (phase-3 rung-0 CISD);
body_high/body_low span the WHOLE series (detectors.blocks.order_blocks zone='body');
mean threshold MT = (body_high + body_low) / 2.

Reading a (entry refinement, trade_test): after the CISD confirms, rest a limit at MT for
10 bars (10h). Fill = first M1 bar trading to MT; decide at that M1 bar's close, enter next
M1 open (~MT). Stop kept at the protected swing (the speaker moves the entry, not the stop);
target 2R. claim '+' vs matched random entry.

Reading b (respect test, gate_test): baseline = the first 1h bar after the CISD that trades
back into the block's body zone (within 10 bars); enter at that bar's close, stop protected
swing, 2R. Gate = that retest bar did NOT close beyond the MT (block respected).
claim '+': respected retests beat violated ones, control-adjusted.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b")
from _common import cl, np, pd, cisd_frame, m1_arrays, first_touch, PHASE3_SRC

CID = "mean-threshold"
TF = "1h"
WAIT_BARS = 10
HOLD = "10h"
RR = 2.0


def _blocks(b):
    ev = cisd_frame(b)
    if ev.empty:
        return ev
    o = b["open"].to_numpy(float)
    c = b["close"].to_numpy(float)
    bh = np.array([max(o[s:e + 1].max(), c[s:e + 1].max()) for s, e in zip(ev.s_pos, ev.e_pos)])
    bl = np.array([min(o[s:e + 1].min(), c[s:e + 1].min()) for s, e in zip(ev.s_pos, ev.e_pos)])
    ev["body_hi"], ev["body_lo"] = bh, bl
    ev["mt"] = (bh + bl) / 2.0
    return ev


def detect_a(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "mt"]
    b = cl.build_bars(m1, TF)
    ev = _blocks(b)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    sgn = ev["sgn"].to_numpy()
    mt = ev["mt"].to_numpy()
    swing = ev["protected_swing"].to_numpy(float)
    close = ev["confirm_close"].to_numpy(float)
    ok = np.where(sgn > 0, (close > mt) & (mt > swing), (close < mt) & (mt < swing))
    ev, sgn, mt, swing = ev[ok].reset_index(drop=True), sgn[ok], mt[ok], swing[ok]
    t_ns = pd.DatetimeIndex(ev["conf_close_time"]).tz_convert("UTC").as_unit("ns").asi8
    # limit window = the next WAIT_BARS bars of this timeframe (by bar close_time)
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC").as_unit("ns").asi8
    endpos = np.minimum(ev["conf_pos"].to_numpy() + WAIT_BARS, len(b) - 1)
    has_full = ev["conf_pos"].to_numpy() + WAIT_BARS <= len(b) - 1
    end_ns = np.where(has_full, ct[endpos], np.iinfo(np.int64).max)
    mt_, mh, ml, _ = m1_arrays(m1)
    k = first_touch(mt_, mh, ml, t_ns, end_ns, mt, np.where(sgn > 0, "below", "above"))
    fill = k >= 0
    dec = pd.DatetimeIndex(mt_[k[fill]]).tz_localize("UTC") + pd.Timedelta(minutes=1)
    out = pd.DataFrame({"decision_time": dec, "available_at": dec, "direction": sgn[fill],
                        "stop_px": swing[fill], "rr": RR, "mt": mt[fill]})
    return out[cols].sort_values("decision_time", kind="stable").reset_index(drop=True)


def detect_b(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "mt_held"]
    b = cl.build_bars(m1, TF)
    ev = _blocks(b)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    hi, lo, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    rows = []
    for r in ev.itertuples(index=False):
        for j in range(r.conf_pos + 1, min(len(b), r.conf_pos + 1 + WAIT_BARS)):
            if lo[j] <= r.body_hi and hi[j] >= r.body_lo:          # traded into the body zone
                ok_side = c[j] > r.protected_swing if r.sgn > 0 else c[j] < r.protected_swing
                if ok_side:
                    held = c[j] >= r.mt if r.sgn > 0 else c[j] <= r.mt
                    rows.append((ct[j], r.sgn, r.protected_swing, bool(held)))
                break
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "mt_held"])
    out["available_at"] = out["decision_time"]
    out["rr"] = RR
    return out[cols].sort_values("decision_time", kind="stable").reset_index(drop=True)


BASE_RULES = ["1h bars; CISD = close through the open of the first candle of the opposing-close "
              "series after a 2/2 fractal swing, within 3 bars (phase-3 rung 0)",
              "order block = that series; body_high/body_low over ALL candles of the series; "
              "MT = (body_high + body_low)/2"]
PARAMS = {"tf": TF, "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
          "block_span": "whole series bodies", "wait_bars": WAIT_BARS, "rr": RR, "max_hold": HOLD}
SRC = {"tf": PHASE3_SRC, "level_rule": PHASE3_SRC, "swing": PHASE3_SRC, "max_wait": PHASE3_SRC,
       "block_span": "corpus: DMUiDBnTYc8/Y8DkNYhq0X0 'from body high to body low' of the block; "
                     "series span per mean-threshold.yaml detection_rules (across the candles of the series)",
       "wait_bars": "declared-before-run: limit / retest valid for 10 entry-TF bars (mirrors phase3 §1.13 hold)",
       "rr": "phase3: §1.12 2R fixed; corpus Y8DkNYhq0X0 examples target >= 2R",
       "max_hold": "phase3: §1.13 10 entry-TF periods"}

if __name__ == "__main__":
    which = sys.argv[1]
    if which == "a":
        ev = cl.cache_frame(f"{CID}_a_limit_mt", lambda: detect_a(cl.load_m1()))
        print(len(ev))
        probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
        print("probe", probe["passed"], probe["events_compared"])
        res = cl.trade_test(ev, max_hold=HOLD)
        op = {"rules": BASE_RULES + [
            "limit at MT resting from the CISD close for 10 bars; fill = first M1 bar whose low<=MT "
            "(longs) / high>=MT (shorts); decide at that M1 bar's close, enter next M1 open",
            "stop at the protected swing (unchanged); target 2R from the actual entry; exit after 10h",
            "CISD events where the confirm close is not beyond MT or MT is not beyond the swing are skipped"],
            "params": PARAMS}
        notes = "fill book; unfilled limits are not trades"
    else:
        ev = cl.cache_frame(f"{CID}_b_retest_respect", lambda: detect_b(cl.load_m1()))
        print(len(ev), ev["mt_held"].mean())
        probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
        print("probe", probe["passed"], probe["events_compared"])
        res = cl.gate_test(ev, "mt_held", mask_available_at="decision_time", max_hold=HOLD)
        op = {"rules": BASE_RULES + [
            "baseline: first 1h bar within 10 bars after the CISD that trades into the body zone; "
            "decide at its close (dropped if it closed beyond the protected swing); stop swing; 2R; 10h",
            "gate mt_held: that retest bar closed on the block's side of MT (no close beyond MT)"],
            "params": PARAMS}
        notes = f"gate firing rate {ev['mt_held'].mean():.3f}"
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "avg_R", "exposure_bars", "ctrl_overlap")})
    p = cl.write_result(CID, which, res, operationalization=op, params_source=SRC, script=__file__,
                        probe=probe, notes=notes)
    print(p)
