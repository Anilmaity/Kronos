"""daily-profile-framework (TTrades own voice, underspecified) — batch model_own_01b.

Purpose of the framework: know before New York opens whether and how to trade the
session. Session windows (NY, DST): Asia 20:00-00:00, London 02:00-05:00, NY a.m.
08:30-12:00 (method_spec §2.5).

Baseline book: phase-3 bare 15m CISD (series_open, swing 2/2, max_wait 3, stop at the
protected swing, 2R, 10 bars) restricted to decisions inside NY a.m. 08:30-12:00.
Days whose Asia or London window has < 60 M1 bars are dropped (profile not evaluable).

Reading a (Seek & Destroy = stand-aside day): S&D := London took BOTH Asia extremes
  (the intraday-safe clause; the outside-day clause needs the daily close). Gate =
  NOT S&D. Claim: trading NY on non-S&D days is better.
Reading b (London-counter -> New York continuation; London Reversal / NY Reversal):
  daily bias = previous-candle engine on the last completed day (continuation ->
  same, reversal -> opposite; inside/both -> none). London ran counter to the bias
  (bullish: London low < Asia low; bearish: London high > Asia high), not S&D.
  Gate = NY entry in the bias direction on such a day. Claim: better than the rest.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
from _common import PHASE3, cisd_book, cl, np, pd, prev_candle_state, summary  # noqa: E402

CID = "daily-profile-framework"
MIN_WIN_BARS = 60


def window_levels(m1: pd.DataFrame) -> pd.DataFrame:
    idx = pd.DatetimeIndex(m1.index).tz_convert("UTC")
    mod = cl.ny_minute_of_day(idx)
    td = cl.trading_day(idx)
    out = {}
    for name, (a, b) in (("asia", (20 * 60, 24 * 60)), ("london", (2 * 60, 5 * 60))):
        sel = (mod >= a) & (mod < b)
        g = pd.DataFrame({"h": m1["high"].to_numpy()[sel], "l": m1["low"].to_numpy()[sel],
                          "td": td[sel], "t": idx[sel]}).groupby("td")
        out[f"{name}_high"] = g["h"].max()
        out[f"{name}_low"] = g["l"].min()
        out[f"{name}_n"] = g.size()
        out[f"{name}_end"] = g["t"].max() + pd.Timedelta(minutes=1)
    return pd.DataFrame(out)


def detect(m1):
    ev = cisd_book(m1, "15min").drop(columns=["extreme_time", "extreme_price"])
    t = pd.DatetimeIndex(ev["decision_time"])
    # decision = close of a 15m bar; the bar that just closed defines the session clock
    last_bar = t - pd.Timedelta(minutes=1)
    mod = cl.ny_minute_of_day(last_bar)
    in_ny = (mod >= 8 * 60 + 30) & (mod < 12 * 60)
    ev, t, last_bar = ev[in_ny].reset_index(drop=True), t[in_ny], last_bar[in_ny]
    w = window_levels(m1)
    tdy = cl.trading_day(last_bar)
    ww = w.reindex(tdy)
    ok = ((ww["asia_n"].fillna(0).to_numpy() >= MIN_WIN_BARS)
          & (ww["london_n"].fillna(0).to_numpy() >= MIN_WIN_BARS))
    ev, ww, t = ev[ok].reset_index(drop=True), ww[ok], t[ok]
    lh, ll = ww["london_high"].to_numpy(), ww["london_low"].to_numpy()
    ah, al = ww["asia_high"].to_numpy(), ww["asia_low"].to_numpy()
    sd = (lh > ah) & (ll < al)
    # daily bias from the last completed day
    d = cl.build_bars(m1, "1D")
    st = prev_candle_state(d)
    pos = np.searchsorted(cl.data.utc_ns(pd.DatetimeIndex(d["close_time"])),
                          cl.data.utc_ns(t), side="right") - 1
    bias = np.where(pos >= 0, st["implied"].to_numpy()[np.clip(pos, 0, None)], 0)
    counter = np.where(bias > 0, ll < al, np.where(bias < 0, lh > ah, False))
    dirn = ev["direction"].to_numpy()
    ev["london_end"] = pd.to_datetime(np.asarray(ww["london_end"]), utc=True)
    ev["bias"] = bias
    ev["not_sd"] = ~sd
    ev["ldn_counter_cont"] = (bias != 0) & counter & ~sd & (dirn == bias)
    return ev


def main():
    ev = cl.cache_frame("dpf_cisd15_ny_v1", lambda: detect(cl.load_m1()))
    assert (ev["london_end"] <= ev["decision_time"]).all()
    probe = cl.probe_lookahead(detect, ev, lookback="15D")
    base_rules = ["baseline: 15m bare CISD (series_open, swing 2/2, max_wait 3) decided inside "
                  "NY a.m. 08:30-12:00 NY; enter next M1 open, stop protected swing, 2R, 150 min",
                  "Asia 20:00-00:00 and London 02:00-05:00 NY high/low of the same 18:00 trading "
                  "day; days with < 60 M1 bars in either window dropped"]
    base_params = {"baseline_tf": "15min", "level_rule": "series_open", "swing": "2/2",
                   "max_wait": 3, "rr": 2.0, "max_hold": "150min", "asia": "20:00-00:00",
                   "london": "02:00-05:00", "ny_am": "08:30-12:00",
                   "min_window_bars": MIN_WIN_BARS}
    base_src = {"baseline_tf": "corpus: daily-profile-framework.yaml timeframes ltf ['30m','15m','5m']",
                "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
                "max_hold": "phase3: 10 entry-TF bars (§1.13)",
                "asia": "session_window_fit: killzones.yaml forex Asia 20:00-00:00",
                "london": "method_spec: §2.5 daily-profile-session-windows London 02:00-05:00",
                "ny_am": "method_spec: §2.5 daily-profile-session-windows NY a.m. 08:30-12:00",
                "min_window_bars": "declared-before-run: profile not evaluable on holiday/stub windows"}
    for reading, col, extra, xp, xs in (
            ("a", "not_sd", ["gate: NOT Seek & Destroy (London took both Asia extremes)"], {}, {}),
            ("b", "ldn_counter_cont",
             ["daily bias: previous-candle engine on the last completed day",
              "gate: bias exists, London ran counter to it beyond the Asia extreme, not S&D, "
              "and the NY entry is in the bias direction"],
             {"bias_rule": "previous-candle engine (§2.3)"},
             {"bias_rule": "method_spec: §2.3/§2.4 previous-candle engine is the mechanical daily bias"})):
        res = cl.gate_test(ev, col, mask_available_at="london_end", max_hold="150min")
        print(f"reading {reading}\n" + summary(res))
        op = {"rules": base_rules + extra, "params": {**base_params, **xp}}
        p = cl.write_result(CID, reading, res, operationalization=op,
                            params_source={**base_src, **xs}, script=__file__, probe=probe,
                            notes="'Relevant HTF PD array' (London Reversal vs NY Reversal "
                                  "discriminator) is undefined [GAP]; reading b pools both "
                                  "London-counter profiles, which share the NY-direction claim.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
