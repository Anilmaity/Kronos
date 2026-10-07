"""update_20261007 / break-even-management — two NEW claims (prior reading 'a' untouched).

u1007a (live_02, h1ZQWWQDhKA): "if you were short ... off this protected swing 2R ...
  you should go break even once it runs down into these lows or at least trail ...
  you wouldn't want to let it reverse on you after sweeping out a low."
  Parent = the campaign's 15m rung-0 CISD book (protected-swing stop, 2R, 150min).
  Interim liquidity = the nearest untaken confirmed 15m 2/2 swing low (short) / high
  (long), formed in the last 24h, lying strictly between entry and the 2R target.
  BE only differs from holding on parents that reach that level and then come BACK
  TO ENTRY (still open). Event = close of that return bar; trade = continue in the
  parent direction with the parent's stop, target and remaining hold.
  Claim "-": BE is right -> the continuation is WORSE than a matched random entry.

u1007b (live_06, uW55Tuk-ngY): "if we get a good closure today I don't want to see
  price come above 50% of this ... if we're going to have a candle two candle 3
  continuation." Daily C2 closure = a day closing beyond the prior real day's extreme
  (bearish: close < prior low; bullish: close > prior high). Hit = the NEXT session
  trades back through 50% of that closed candle. rate_test vs a matched null (same
  distance from price, same side, same M1-bar horizon, +/-30d). Claim "-".

live_10 (GRc5FVB5tdg, entry-location vs expansion EQ) not run: at most two readings,
and its boundary ("entry right here") is a chart point.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
from _common import *   # noqa: F401,F403  (cl, np, pd, cisd_book, m1_arrays, show, BASE_*)

TF = "15min"
PARENT_HOLD = pd.Timedelta(HOLD[TF])
WMAX = 200
LOOKBACK = 96          # 15m bars = 24h of swings considered as interim liquidity
CID = "break-even-management"


# ---------------------------------------------------------------- u1007a
def interim_levels(b, ev, entry, tgt):
    """Per event: nearest untaken confirmed 2/2 swing (in the trade's favour) strictly
    between entry and target, known at the CISD confirm bar's close. NaN if none."""
    s = ev["direction"].to_numpy()
    hi, lo = b["high"].to_numpy(float), b["low"].to_numpy(float)
    n = len(b)
    sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    sh[2:-2] = (hi[2:-2] > np.maximum.reduce([hi[:-4], hi[1:-3], hi[3:-1], hi[4:]]))
    sl[2:-2] = (lo[2:-2] < np.minimum.reduce([lo[:-4], lo[1:-3], lo[3:-1], lo[4:]]))
    out = np.full(len(ev), np.nan)
    conf = ev["conf_pos"].to_numpy()
    for j in range(len(ev)):
        c = conf[j]
        if c < 0 or not np.isfinite(entry[j]):
            continue
        a = max(2, c - LOOKBACK)
        if s[j] > 0:
            x, flag = hi[a:c + 1], sh[a:c - 1]           # swing at k needs k+2 <= c
            k = np.nonzero(flag)[0]
            if not len(k):
                continue
            lv = x[k]
            later_max = np.maximum.accumulate(x[::-1])[::-1]  # max of x[k+1:] = later_max[k+1]
            ok = later_max[k + 1] < lv                       # untaken through bar c
            ok &= (lv > entry[j]) & (lv < tgt[j])
            if ok.any():
                out[j] = lv[ok].min()
        else:
            x, flag = lo[a:c + 1], sl[a:c - 1]
            k = np.nonzero(flag)[0]
            if not len(k):
                continue
            lv = x[k]
            later_min = np.minimum.accumulate(x[::-1])[::-1]
            ok = later_min[k + 1] > lv
            ok &= (lv < entry[j]) & (lv > tgt[j])
            if ok.any():
                out[j] = lv[ok].max()
    return out


def detect_a(m1):
    ev, _, b = cisd_book(m1, TF)
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    tn, o, h, l_, c = m1_arrays(m1)
    N = len(tn)
    dec = cl.data.utc_ns(pd.DatetimeIndex(ev["decision_time"])).astype(np.int64)
    s = ev["direction"].to_numpy().astype(float)
    stop = ev["stop_px"].to_numpy(float)
    i0 = np.searchsorted(tn, dec, side="left")
    ok = i0 < N
    i0c = np.minimum(i0, N - 1)
    entry = np.where(ok, o[i0c], np.nan)
    risk = s * (entry - stop)
    ok &= np.isfinite(risk) & (risk > 0)
    tgt = entry + s * 2.0 * risk
    lvl = interim_levels(b, ev, np.where(ok, entry, np.nan), tgt)
    ok &= np.isfinite(lvl)
    end_ns = dec + PARENT_HOLD.value
    i1 = np.searchsorted(tn, end_ns, side="left")
    K = np.arange(WMAX)
    idx = i0c[:, None] + K[None, :]
    inwin = (idx < i1[:, None]) & (idx < N)
    idx = np.minimum(idx, N - 1)
    up = np.where(s[:, None] > 0, h[idx], -l_[idx])
    dn = np.where(s[:, None] > 0, l_[idx], -h[idx])
    E, S, T = (s * entry)[:, None], (s * stop)[:, None], (s * tgt)[:, None]
    L = (s * lvl)[:, None]
    stop_hit = inwin & (dn <= S)
    tgt_hit = inwin & (up >= T)
    trig = inwin & (up >= L)
    back = inwin & (dn <= E)
    BIG = WMAX + 1

    def first(m):
        return np.where(m.any(1), m.argmax(1), BIG)
    f_stop, f_tgt, f_trig = first(stop_hit), first(tgt_hit), first(trig)
    ok &= (f_trig < f_stop) & (f_trig < f_tgt)
    f_back = first(back & (K[None, :] > f_trig[:, None]))
    ok &= f_back < BIG
    ok &= (f_back <= f_stop) & (f_back <= f_tgt)
    rr_ = np.arange(len(ev))
    fb = np.minimum(f_back, WMAX - 1)
    ok &= ~stop_hit[rr_, fb] & ~tgt_hit[rr_, fb]
    ret_close = tn[np.minimum(i0c + fb, N - 1)] + 60_000_000_000
    rem = end_ns - ret_close
    ok &= rem > 0
    t = pd.to_datetime(ret_close[ok], utc=True)
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": s[ok].astype(int), "stop_px": stop[ok],
                        "target_px": tgt[ok], "max_hold": pd.to_timedelta(rem[ok], unit="ns")})
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)[cols]


def run_a():
    ev = cl.cache_frame("be_interim_liq_15m_lb96", lambda: detect_a(cl.load_m1()))
    print(len(ev))
    probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, claim="-")
    show(res)
    op = {"rules": ["parent: 15m rung-0 CISD, entry next M1 open, protected-swing stop, 2R target, 150min hold, resolved on M1",
                    "interim liquidity: nearest untaken confirmed 15m 2/2 swing (lows for shorts, highs for longs) from the last 96 bars, strictly between entry and target, known at the CISD confirm close",
                    "event: first M1 bar after the parent touched that level that trades back to entry, parent still open; return bars also touching stop/target dropped",
                    "decide at that bar's close; continue in the parent direction with the parent's stop, target and remaining hold",
                    "claim -: BE at interim liquidity is right -> continuation worse than a matched random entry"],
          "params": {"parent_tf": TF, **BASE_PARAMS, "parent_hold": HOLD[TF], "interim_swing": "2/2 on 15m",
                     "interim_lookback_bars": LOOKBACK, "interim_pick": "nearest to entry", "grid4h": "n/a"}}
    src = {"parent_tf": "phase3: primary stack entry TF (as in prior reading a)",
           **{k: BASE_SRC for k in BASE_PARAMS}, "parent_hold": HOLD_SRC,
           "rr": "corpus: h1ZQWWQDhKA 'off this protected swing 2R'",
           "interim_swing": "declared-before-run: 'these lows' are shown on chart, not stated; parent-TF 2/2 swings as in the locked config",
           "interim_lookback_bars": "declared-before-run: one day of 15m bars",
           "interim_pick": "corpus: h1ZQWWQDhKA 'go break even once it runs down into these lows' (first lows reached)",
           "grid4h": "declared-before-run: no 4h bars used"}
    p = cl.write_result(CID, "u1007a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="New claim only (interim-liquidity BE trigger). Prior reading 'a' (+1R trigger, claim +) untouched.")
    print("wrote", p)


# ---------------------------------------------------------------- u1007b
def detect_b(m1):
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] > 600]   # an in-progress last day has close_time > data end, so it never enters (T-1D, T]
    o, h, l_, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    bear = np.zeros(len(d), bool); bull = np.zeros(len(d), bool)
    bear[1:] = c[1:] < l_[:-1]
    bull[1:] = c[1:] > h[:-1]
    m = bear | bull
    t = pd.DatetimeIndex(d["close_time"].to_numpy()[m]).tz_convert("UTC") if pd.DatetimeIndex(d["close_time"]).tz else pd.DatetimeIndex(d["close_time"].to_numpy()[m]).tz_localize("UTC")
    return pd.DataFrame({"decision_time": t, "available_at": t,
                         "direction": np.where(bull[m], 1, -1),
                         "mid": ((h + l_) / 2)[m]}).reset_index(drop=True)


def run_b():
    m1 = cl.load_m1()
    mkt = cl.get_market()
    ev = cl.cache_frame("be_daily_c2_mid", lambda: detect_b(m1))
    print(len(ev))
    probe = cl.probe_lookahead(detect_b, ev, lookback="45D")
    print("probe", probe.get("passed"))
    t = pd.DatetimeIndex(ev["decision_time"])
    # horizon = the next real session's M1-bar count (trading time)
    d = cl.bars("1D"); d = d[d["n_m1"] > 600]
    ct = pd.DatetimeIndex(d["close_time"]); nm = d["n_m1"].to_numpy()
    pos = ct.get_indexer(t)
    assert (pos >= 0).all()
    nxt = np.where(pos + 1 < len(nm), nm[np.minimum(pos + 1, len(nm) - 1)], 1440)
    s = ev["direction"].to_numpy()
    mid = ev["mid"].to_numpy(float)
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = mid - first_px

    def hits(times, level, horizon):
        out = np.zeros(len(times))
        for sd, side in ((-1, "above"), (1, "below")):
            k = s_sel == sd
            if k.any():
                out[k] = cl.touch(times[k], level[k], side, horizon_bars=horizon[k])["hit"].to_numpy()
        return out

    s_sel = s
    obs = hits(t, mid, nxt)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        nonlocal s_sel
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        px = mkt.o[mkt.pos_at_or_after(tk[ok])]
        s_sel = s[ok]
        out[ok] = hits(tk[ok], px + dist[ok], nxt[ok])
        s_sel = s
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]), null_fn=null_fn,
                       claim="-", predictors=ev)
    show(res)
    op = {"rules": ["daily bars, 18:00 NY roll, stub days (n_m1<=600) skipped",
                    "C2 closure: day closes below the prior real day's low (bearish) / above its high (bullish); decide at its close",
                    "level = 50% of that closed candle (high+low)/2",
                    "hit = the next session trades back through the level (bearish: M1 high >= mid; bullish: M1 low <= mid), horizon = next session's M1-bar count",
                    "null = same signed distance from price, same side, same bar count, at matched random moments (+/-30d)",
                    "claim -: after a good closure price should not come back beyond 50% -> hit rate below null"],
          "params": {"closure": "close beyond prior day extreme", "level": "50% of closed candle",
                     "horizon": "next session (M1 bars)", "day_open_hour": 18, "min_n_m1": 600, "grid4h": "n/a"}}
    src = {"closure": "corpus: uW55Tuk-ngY 'if we get a good closure today ... candle two candle 3 continuation'",
           "level": "corpus: uW55Tuk-ngY 'I don't want to see price come above 50% of this'",
           "horizon": "declared-before-run: the C3 day that follows the closure",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "min_n_m1": "declared-before-run: README stub-day skip as in the rate example",
           "grid4h": "declared-before-run: no 4h bars used"}
    p = cl.write_result(CID, "u1007b", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="New claim only (daily C2 50% break-even reference). Prior reading 'a' untouched.")
    print("wrote", p)


if __name__ == "__main__":
    for r in sys.argv[1:] or ["a", "b"]:
        {"a": run_a, "b": run_b}[r]()
