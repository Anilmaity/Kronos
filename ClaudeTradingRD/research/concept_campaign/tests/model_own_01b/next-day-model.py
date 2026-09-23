"""next-day-model (TTrades own voice, contested) — batch model_own_01b.

Reading a (trade): the daily decision table. Day D took exactly one side of D-1's
range. Close outside -> continuation (same direction next day); close back inside
-> reversal (opposite direction next day). Trade D+1: enter at the first M1 open
after D's close ("simply at the candle open"), stop at the extreme of the candle
just formed (D's low for longs, D's high for shorts), 2R, exit after one session.

Reading b (rate): the 2-2 reversal's objective. After a reversal day (took one side
of D-1, closed back inside), does D+1 reach D-1's OPPOSITE extreme ("the objective
is the other side of the range")? Null: same signed distance from price, same side,
same number of M1 bars, at matched random moments (+/-30 d).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
from _common import cl, np, pd, prev_candle_state, summary  # noqa: E402

CID = "next-day-model"
MIN_NM1 = 600           # declared-before-run: drop stub sessions (data holes)
SESSION_BARS = 1380     # one full 18:00-17:00 NY session in M1 bars


def detect_trade(m1):
    d = cl.build_bars(m1, "1D")
    st = prev_candle_state(d)
    ok_prev = (d["n_m1"].shift(1) >= MIN_NM1).fillna(False).to_numpy()
    keep = (st["state"].isin(["continuation", "reversal"]).to_numpy()
            & (d["n_m1"].to_numpy() >= MIN_NM1) & ok_prev)
    dd, ss = d[keep], st[keep]
    ct = pd.DatetimeIndex(dd["close_time"])
    dirn = ss["implied"].to_numpy()
    return pd.DataFrame({
        "decision_time": ct, "available_at": ct, "direction": dirn,
        "stop_px": np.where(dirn > 0, dd["low"].to_numpy(), dd["high"].to_numpy()),
        "rr": 2.0, "state": ss["state"].to_numpy(),
    }).reset_index(drop=True)


def detect_rate(m1):
    d = cl.build_bars(m1, "1D")
    st = prev_candle_state(d)
    ok_prev = (d["n_m1"].shift(1) >= MIN_NM1).fillna(False).to_numpy()
    keep = ((st["state"] == "reversal").to_numpy()
            & (d["n_m1"].to_numpy() >= MIN_NM1) & ok_prev)
    dd, ss = d[keep], st[keep]
    ct = pd.DatetimeIndex(dd["close_time"])
    dirn = ss["implied"].to_numpy()
    tgt = np.where(dirn > 0, ss["prev_high"].to_numpy(), ss["prev_low"].to_numpy())
    return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": dirn,
                         "target": tgt}).reset_index(drop=True)


def run_a():
    ev = cl.cache_frame("ndm_trade_1d_v1", lambda: detect_trade(cl.load_m1()))
    probe = cl.probe_lookahead(detect_trade, ev, lookback="30D")
    res = cl.trade_test(ev, max_hold="23h", hold_basis="bars")
    print("reading a\n" + summary(res))
    print("  states", ev["state"].value_counts().to_dict())
    op = {"rules": [
        "1D bars on the 18:00 NY trading day; day D vs D-1: took exactly one side",
        "close outside D-1's range -> continuation, trade D's direction on D+1",
        "close back inside -> reversal, trade the opposite direction on D+1",
        "both sides / inside day -> no trade; stub sessions (<600 M1) dropped (D and D-1)",
        "decide at D's close; enter next M1 open; stop at D's low (long) / high (short)",
        "target 2R; exit after one session (1380 M1 bars, trading time)"],
        "params": {"tf": "1D", "day_open_hour": 18, "rr": 2.0, "max_hold": "23h",
                   "hold_basis": "bars", "min_nm1": MIN_NM1}}
    src = {"tf": "corpus: next-day-model.yaml timeframes htf 1D ('Next Day Model')",
           "day_open_hour": "method_spec: §1.4 daily open 18:00 canon",
           "rr": "corpus: next-day-model.yaml execution.targets '2R'",
           "max_hold": "declared-before-run: the anticipated candle is D+1 only (one session)",
           "hold_basis": "declared-before-run: one session in trading time so Friday decisions are not emptied by the weekend",
           "min_nm1": "declared-before-run: drop stub sessions (README trap 6)"}
    notes = ("stop = 'the extreme of the higher-timeframe candle just formed' (execution.stop); "
             "entry = 'simply at the candle open' (execution.entry, the no-LTF alternative). "
             "Rerun once: the first run tested the frame minus its state column, so write_result refused the probe fingerprint; same book, identical numbers expected.")
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print("  wrote", p)
    return res


def run_b():
    ev = cl.cache_frame("ndm_rate_1d_v1", lambda: detect_rate(cl.load_m1()))
    probe = cl.probe_lookahead(detect_rate, ev, lookback="30D")
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    dirn = ev["direction"].to_numpy()
    tgt = ev["target"].to_numpy(float)
    side_up = dirn > 0
    obs = np.full(len(t), np.nan)
    up = cl.touch(t[side_up], tgt[side_up], "above", horizon_bars=SESSION_BARS)["hit"].to_numpy()
    dn = cl.touch(t[~side_up], tgt[~side_up], "below", horizon_bars=SESSION_BARS)["hit"].to_numpy()
    obs[side_up], obs[~side_up] = up, dn
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = tgt - first_px
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k])
        if tk.tz is None:
            tk = tk.tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
        lv = px + dist[ok]
        su = side_up[ok]
        r = np.full(ok.sum(), np.nan)
        tko = tk[ok]
        r[su] = cl.touch(tko[su], lv[su], "above", horizon_bars=SESSION_BARS)["hit"].to_numpy()
        r[~su] = cl.touch(tko[~su], lv[~su], "below", horizon_bars=SESSION_BARS)["hit"].to_numpy()
        out[ok] = r
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                       null_fn=null_fn, predictors=ev)
    print("reading b\n" + summary(res))
    op = {"rules": [
        "reversal day D: took exactly one side of D-1's range and closed back inside",
        "prediction: D+1 reaches D-1's opposite extreme (bullish reversal -> D-1 high)",
        "hit = any M1 high>=/low<= target within one session (1380 M1 bars) after D's close",
        "null = same signed distance from the first price, same side, same bar count, "
        "at matched random moments (5 reps, +/-30 d)"],
        "params": {"tf": "1D", "day_open_hour": 18, "horizon_bars": SESSION_BARS,
                   "min_nm1": MIN_NM1}}
    src = {"tf": "corpus: next-day-model.yaml timeframes htf 1D",
           "day_open_hour": "method_spec: §1.4 daily open 18:00 canon",
           "horizon_bars": "declared-before-run: the anticipated candle is D+1 (one session in trading time)",
           "min_nm1": "declared-before-run: drop stub sessions (README trap 6)"}
    notes = ("objective per detection_rules: 'the objective is the other side of the range' / "
             "'the magnitude is the previous candle's opposite extreme' (STRAT 2-2 reversal).")
    p = cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print("  wrote", p)
    return res


if __name__ == "__main__":
    run_a()
    run_b()
