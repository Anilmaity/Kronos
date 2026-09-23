"""poi-timeframe-selection (TTrades own voice, wDXTIDbIMwU). Declared before any run.

'Entering on the 5-minute, 1-minute or sub-1-minute ... most of my points of interest lie on
The Daily 4 Hour one hour' and NOT monthly/weekly (those belong to a 4H entry).
Measurable (concept file): hit rate of entries taken from an out-of-band POI (e.g. a weekly
level with a low-TF entry).

Gate test on a 5m entry book (claim '+': in-band POIs beat out-of-band POIs):
  baseline : phase-3 bare 5m CISD (series_open, 2/2, max_wait 3), stop at protected swing,
             2R, 50min hold (10 entry-TF bars).
  POI tag  : the CISD's extreme bar (the swing the reversal turned on) traded THROUGH a level
             (bar low <= level <= bar high) -- highs for a bearish CISD, lows for a bullish one.
             Levels = the most recent COMPLETED period's high/low as of that bar's START:
             in-band 1D (18:00 roll), 4h (forex grid), 1h; out-of-band 1W, 1M.
  population: 5m CISDs whose extreme tagged at least one of these levels.
  gate     : in-band only (tagged a 1D/4h/1h level and no W/M level);
  complement: tagged a weekly or monthly level (the out-of-band POI he says not to use at 5m).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_raw

TF = "5min"
INB = ("1D", "4h", "1h")
OUTB = ("1W", "1M")


def detect(m1):
    b, ev = cisd_raw(m1, TF)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "tag_time", "in_band_only"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    xt = pd.DatetimeIndex(ev["extreme_time"])
    xb = b.loc[xt]
    bull = (ev["direction"] == "bullish").to_numpy()
    hi, lo = xb["high"].to_numpy(float), xb["low"].to_numpy(float)
    xst = xt.tz_convert("UTC") if xt.tz is not None else xt.tz_localize("UTC")

    def tagged(kind):
        pr = cl.prior_hilo(xst, kind, m1=m1)
        lvl = np.where(bull, pr["low"].to_numpy(float), pr["high"].to_numpy(float))
        return np.isfinite(lvl) & (lo <= lvl) & (lvl <= hi)

    tin = np.zeros(len(ev), bool)
    tout = np.zeros(len(ev), bool)
    for k in INB:
        tin |= tagged(k)
    for k in OUTB:
        tout |= tagged(k)
    out = pd.DataFrame({
        "decision_time": close, "available_at": close,
        "direction": np.where(bull, 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
        "tag_time": pd.DatetimeIndex(xb["close_time"]),
        "in_band_only": tin & ~tout,
    })
    return out[(tin | tout)].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("t03b_poi_tf_cisd5_v1", lambda: detect(cl.load_m1()))
    print(len(ev), "in-band-only share", ev["in_band_only"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="100D")  # monthly level warm-up needs > 62 days
    res = cl.gate_test(ev, "in_band_only", mask_available_at="tag_time", max_hold="50min", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "ties", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": ["baseline: phase-3 bare 5m CISD (series_open, 2/2, max_wait 3), decide at confirming 5m close, enter next M1 open, stop at protected swing, 2R, 50min hold",
                    "POI tag: the CISD extreme bar's range contains a prior completed period's low (bullish) / high (bearish), levels read as of that bar's start",
                    "population: events whose extreme tagged any of 1D/4h/1h/1W/1M levels",
                    "gate: tagged only in-band (1D/4h/1h) levels; complement: tagged a weekly or monthly level"],
          "params": {"entry_tf": TF, "in_band": list(INB), "out_band": list(OUTB), "grid4h": "forex",
                     "day_open_hour": 18, "rr": 2.0, "max_hold": "50min", "level_rule": "series_open",
                     "swing": "2/2", "max_wait": 3, "tag_rule": "extreme bar low<=level<=high"}}
    ph3 = "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked rung-0 config)"
    src = {"entry_tf": "corpus: wDXTIDbIMwU entry on the 5-minute; phase3 5m stack",
           "in_band": "corpus: wDXTIDbIMwU 'most of my points of interest lie on The Daily 4 Hour one hour'",
           "out_band": "corpus: wDXTIDbIMwU no monthly/weekly POIs for a 5m/1m entry",
           "grid4h": "session_window_fit: forex grid for gold (weak; knob recorded)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "rr": ph3, "max_hold": ph3, "level_rule": ph3, "swing": ph3, "max_wait": ph3,
           "tag_rule": "declared-before-run: POI = a high/low taken out (method_spec §4.1); the extreme bar trades through it"}
    out = cl.write_result("poi-timeframe-selection", None, res, operationalization=op,
                          params_source=src, script=__file__, probe=probe,
                          notes="'Sometimes the 15-minute' band member not used (unconditioned in the source). Only the 5m rung of the mapping is tested; the 4H-entry rung is not.")
    print(out)
