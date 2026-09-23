"""mean-reversion-3atr-21ema (guest: STRATalorian, kG8BuEPVppo).

Claim: price "overextended plus three ATR" comes "back to say the 21 EMA".
Only trigger + target are given (no stop), so this is a rate_test: after a
+/-3 ATR extension from the 21 EMA, does price reach the EMA (as it stood at
the trigger) more often than it reaches a level at the SAME distance in the
SAME direction from a matched random moment, within the SAME number of M1 bars?

Unstated knobs (timeframe, ATR period, horizon, symmetry) are declared here
BEFORE the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

TF = "1h"
EMA_N = 21
ATR_N = 14
K_ATR = 3.0
HORIZON_M1 = 1440      # one trading day of M1 bars


def detect(m1):
    b = cl.build_bars(m1, TF)
    b = b[b["n_m1"] > 0]
    c, h, l = b["close"], b["high"], b["low"]
    ema = c.ewm(span=EMA_N, adjust=False).mean()
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / ATR_N, adjust=False).mean()
    up = c >= ema + K_ATR * atr            # overextended above -> expect return down
    dn = c <= ema - K_ATR * atr
    first_up = up & ~up.shift(1, fill_value=False)
    first_dn = dn & ~dn.shift(1, fill_value=False)
    # need warm-up: at least 5*EMA_N bars
    warm = np.arange(len(b)) >= 5 * EMA_N
    sel = (first_up | first_dn) & warm
    ev = pd.DataFrame({
        "decision_time": pd.DatetimeIndex(b.loc[sel, "close_time"]),
        "available_at": pd.DatetimeIndex(b.loc[sel, "close_time"]),
        "direction": np.where(first_up[sel], -1, 1),
        "level": ema[sel].to_numpy(),
        "close": c[sel].to_numpy(),
    }).reset_index(drop=True)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"mr3atr_{TF}_{EMA_N}_{ATR_N}_{K_ATR}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = ev["level"].to_numpy() - first_px          # signed distance to the EMA
    lv = ev["level"].to_numpy()
    obs = np.full(len(ev), np.nan)
    # long events: EMA is ABOVE price -> side 'above'; short: EMA below -> 'below'
    longm = ev["direction"].to_numpy() == 1
    o1 = cl.touch(t[longm], lv[longm], "above", horizon_bars=HORIZON_M1)["hit"].to_numpy()
    o2 = cl.touch(t[~longm], lv[~longm], "below", horizon_bars=HORIZON_M1)["hit"].to_numpy()
    obs[longm] = o1
    obs[~longm] = o2
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k])
        tk = tk.tz_localize("UTC") if tk.tz is None else tk
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        for sidem, side in ((longm, "above"), (~longm, "below")):
            m = ok & sidem
            px = mkt.o[mkt.pos_at_or_after(tk[m])]
            out[m] = cl.touch(tk[m], px + dist[m], side, horizon_bars=HORIZON_M1)["hit"].to_numpy()
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                       null_fn=null_fn, predictors=ev, claim="+")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "1h bars (UTC hourly), EMA21 of close (adjust=False), Wilder ATR14",
        "trigger: first 1h close >= EMA+3*ATR (short: expect return down) or <= EMA-3*ATR (long)",
        "decide at the trigger bar's close; target level = EMA value at that close",
        "hit = price touches that level within 1440 M1 bars (one trading day)",
        "null = same signed distance from the first open after a matched random moment "
        "(+/-30d), same side, same 1440-bar horizon"],
        "params": {"tf": TF, "ema_n": EMA_N, "atr_n": ATR_N, "k_atr": K_ATR,
                   "horizon_m1": HORIZON_M1, "symmetric": True}}
    src = {"ema_n": "corpus: kG8BuEPVppo 'looking for it to come back to say the 21 EMA'",
           "k_atr": "corpus: kG8BuEPVppo 'overextended plus three ATR'",
           "tf": "declared-before-run: timeframe unstated in the corpus; 1h chosen as the "
                 "middle of the campaign's intraday grid",
           "atr_n": "declared-before-run: ATR period unstated; Wilder's standard 14",
           "horizon_m1": "declared-before-run: one trading day (1440 M1 bars)",
           "symmetric": "declared-before-run: symmetry unstated; tested both sides pooled"}
    p = cl.write_result("mean-reversion-3atr-21ema", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Guest's non-ICT system; only trigger/target stated, so tested as a "
                              "rate of reaching the EMA vs a same-distance matched null.")
    print(p)
