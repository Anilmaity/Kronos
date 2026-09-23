"""internal-external-range-liquidity (guests: $niper, Ash Trades) -> rate_test, daily.

Claim (the alternation): once one liquidity type is tagged, the other becomes the
next draw.
  leg IRL->ERL: a daily bar makes the FIRST tag of an unfilled daily FVG
     (bullish FVG: low <= gap top; bearish mirrored) -> draw = the nearest
     still-unswept confirmed daily swing high above the bar's high (bullish FVG)
     / swing low below the bar's low (bearish FVG).
  leg ERL->IRL: a daily bar RUNS an unswept confirmed daily swing high (trades
     above it) -> draw = the nearest still-untagged bullish FVG below the bar's
     low, target its top edge (mirrored for a swing-low run: the nearest
     untagged bearish FVG above, target its bottom edge).
  Swings: 3-candle swing (left=1, right=1), known at the close of the right bar.
  FVGs: 3-bar daily gaps, known at the close of the third bar.
  Decide at the daily close; hit = M1 reaches the draw within 5 sessions.
  Null: matched random daily-close moments (+/-30d), same signed distance from
  the next M1 open, same side, same M1-bar horizon. Both legs pooled.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

H_BARS = 5 * 1380
MIN_M1 = 600
MEM = 20          # swings/FVGs older than MEM sessions are forgotten


def detect(m1):
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= MIN_M1]
    h, l = d["high"].to_numpy(), d["low"].to_numpy()
    ct = pd.DatetimeIndex(d["close_time"])
    n = len(d)
    sh, sl = [], []          # [price, alive] swing highs/lows (confirmed)
    fb, fs = [], []          # bullish FVGs [lo, hi, alive(untagged)], bearish FVGs
    rows = []
    for i in range(n):
        # --- forget structures older than MEM sessions (bounded memory)
        sh[:] = [s for s in sh if i - s[2] <= MEM]; sl[:] = [s for s in sl if i - s[2] <= MEM]
        fb[:] = [g for g in fb if i - g[3] <= MEM]; fs[:] = [g for g in fs if i - g[3] <= MEM]
        # --- events at bar i, using structures known at close of i-1 / i
        # IRL -> ERL: first tag of an untagged FVG formed before i
        for g in fb:
            if g[2] and l[i] <= g[1]:
                g[2] = False
                c = [s[0] for s in sh if s[1] and s[0] > h[i]]
                if c:
                    rows.append((ct[i], 1, min(c), "irl_to_erl"))
        for g in fs:
            if g[2] and h[i] >= g[0]:
                g[2] = False
                c = [s[0] for s in sl if s[1] and s[0] < l[i]]
                if c:
                    rows.append((ct[i], -1, max(c), "irl_to_erl"))
        # ERL -> IRL: run of an unswept swing confirmed before i
        ran_h = [s for s in sh if s[1] and h[i] > s[0]]
        if ran_h:
            for s in ran_h:
                s[1] = False
            c = [g[1] for g in fb if g[2] and g[1] < l[i]]
            if c:
                rows.append((ct[i], -1, max(c), "erl_to_irl"))
        ran_l = [s for s in sl if s[1] and l[i] < s[0]]
        if ran_l:
            for s in ran_l:
                s[1] = False
            c = [g[0] for g in fs if g[2] and g[0] > h[i]]
            if c:
                rows.append((ct[i], 1, min(c), "erl_to_irl"))
        # --- structures that become known at close of i
        if i >= 2:
            if l[i] > h[i - 2]:
                fb.append([h[i - 2], l[i], True, i])
            if h[i] < l[i - 2]:
                fs.append([h[i], l[i - 2], True, i])
        if 1 <= i:
            j = i - 1
            if j >= 1 and h[j] > h[j - 1] and h[i] <= h[j]:
                sh.append([h[j], True, i])
            if j >= 1 and l[j] < l[j - 1] and l[i] >= l[j]:
                sl.append([l[j], True, i])
        # prune dead
        if i % 50 == 0:
            sh[:] = [s for s in sh if s[1]]; sl[:] = [s for s in sl if s[1]]
            fb[:] = [g for g in fb if g[2]]; fs[:] = [g for g in fs if g[2]]
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "target_px", "leg"])
    out["available_at"] = out["decision_time"]
    return out[["decision_time", "available_at", "direction", "target_px", "leg"]]


if __name__ == "__main__":
    ev = cl.cache_frame(f"irl_erl_1d_mem{MEM}", lambda: detect(cl.load_m1())).reset_index(drop=True)
    print("events", len(ev), ev.groupby(["leg", "direction"]).size().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe.get("passed"))
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    tgt = ev["target_px"].to_numpy()
    up = ev["direction"].to_numpy() == 1
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = tgt - first_px

    def hits(times, levels, upmask):
        o = np.zeros(len(times), bool)
        if upmask.any():
            o[upmask] = cl.touch(times[upmask], levels[upmask], "above", horizon_bars=H_BARS)["hit"].to_numpy()
        if (~upmask).any():
            o[~upmask] = cl.touch(times[~upmask], levels[~upmask], "below", horizon_bars=H_BARS)["hit"].to_numpy()
        return o

    obs = hits(t, tgt, up).astype(float)
    grid = pd.DatetimeIndex(cl.bars("1D")["close_time"])
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, grid_times=grid)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
        out[ok] = hits(tk[ok], px + dist[ok], up[ok])
        return out

    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, predictors=ev,
                       outcome_horizon="7D", claim="+")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    for lg in ("irl_to_erl", "erl_to_irl"):
        m = (ev["leg"] == lg).to_numpy()
        print(lg, m.sum(), obs[m].mean())
    op = {"rules": ["1D bars (18:00 NY roll), stub sessions (<600 M1) dropped",
                    "structures older than 20 sessions forgotten; swings: 3-candle (left=1,right=1), known at the right bar's close; FVG: 3-bar daily gap known at the third bar's close",
                    "IRL->ERL: first tag of an untagged daily FVG -> target nearest unswept swing high above bar high (bullish FVG) / swing low below bar low (bearish FVG)",
                    "ERL->IRL: bar runs an unswept swing high -> target top edge of nearest untagged bullish FVG below bar low (mirror for lows)",
                    "decide at daily close; hit = M1 reaches target within 5 sessions (6,900 M1 bars)",
                    "null: matched random daily-close moments +/-30d, same signed distance from next M1 open, same side and horizon; legs pooled"],
          "params": {"tf": "1D", "day_open_hour": 18, "swing": "1/1", "horizon_m1_bars": H_BARS,
                     "tag_rule": "first touch (tag, not full fill)", "memory_sessions": MEM, "min_session_m1": MIN_M1,
                     "outcome_horizon": "7D"}}
    src = {"tf": "corpus: zXtJSSkiNmo Ash Trades variant stated for the daily only; 5aRB_ZY3474 applies it on 1D among others",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "swing": "corpus: zXtJSSkiNmo three-candle swing point (swing-point-stop-hunt, same guest)",
           "horizon_m1_bars": "declared-before-run: one trading week (5 x 1380 M1 bars)",
           "tag_rule": "declared-before-run: yaml ambiguity 'tagged vs filled' -> tagged, as the rule text says 'traded into'",
           "memory_sessions": "declared-before-run: 'old highs/lows' and unfilled gaps are only tracked for 20 sessions (~1 month) so the state is bounded; needed for a finite probe warm-up",
           "min_session_m1": "declared-before-run: skip stub sessions (README trap 6)",
           "outcome_horizon": "declared-before-run: 5 sessions span ~7 calendar days"}
    p = cl.write_result("internal-external-range-liquidity", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Both legs of the alternation pooled into one reading; per-leg hit rates printed by the script, not scored separately. 'Before the FVG side is revisited' race clause not applied: plain reach-within-horizon vs geometry-matched null.")
    print(p)
