"""Step 1 - context + sequence features for all 178 entries -> entries_features.csv, grid.parquet.

Thresholds below were fixed BEFORE any outcome table was looked at and were not tuned afterwards.

DECISION EVENT  consecutive clicks on the same side <= 30 s apart = one decision (the trader sizes
                up by tapping 0.04 several times; treating taps as independent entries is pseudo-replication).
ROLE (book state just before the event's first click, from the deal ledger):
    first        account has no same-side and no opposite-side position
    avg_add      same-side basket open and its VWAP is >= 1.0 pt worse than this fill (adding to a loser)
    pyramid_add  same-side basket open and >= 1.0 pt in profit (adding to a winner)
    level_add    same-side basket open, within +-1.0 pt
    hedge        only opposite-side positions open
CONTEXT TYPE (market state at the last closed S5 bar before the click; a5 = ATR14 on M5), first match wins:
    breakout       price is beyond the prior 60-min range (window ending 2 min ago) in the trade direction
    momentum       5-min return in the trade direction >= 1.0 x a5
    pullback       60-min return with the trade AND M5 EMA20>EMA50 with the trade AND 5-min return against it
    range_fade     entry in the adverse third of the 60-min range (pos60_dir <= 1/3) or beyond the 60-min
                   extreme AGAINST the trade (selling a new high / buying a new low)
    other          none of the above
SETUP = 'averaging_add' / 'hedge' when the role says so, else the context type.

Run: ../../../.venv/bin/python 01_features.py
"""
import json

import numpy as np
import pandas as pd

from lib import HERE, ROOT, MIN, NS, build_grid, load_deals, load_m1, load_s5, ns, outcomes, sign_features

BURST_S = 30
ADD_PTS = 1.0
basis = json.loads((HERE / "basis.json").read_text())

s5, m1 = load_s5(), load_m1()
t0 = ns(pd.DatetimeIndex(["2026-11-04T00:00:00Z"]))[0]
g = build_grid(s5, m1, basis["basis_bid"], fwd=True, start=t0)
g.to_parquet(HERE / "grid.parquet")
print("grid rows", len(g), "from", pd.to_datetime(g.c.iloc[0], utc=True), "to", pd.to_datetime(g.c.iloc[-1], utc=True))

# ---------- the 178 clicks ----------
t = pd.read_csv(ROOT / "trades.csv")
for col in ("open_time", "close_time"):
    t[col] = pd.to_datetime(t[col], utc=True, format="ISO8601")
t = t.sort_values(["open_time", "position_id"]).reset_index(drop=True)
t["s"] = np.where(t.side.eq("BUY"), 1, -1)
T, C = ns(t.open_time), ns(t.close_time)
gi = np.searchsorted(g.c.to_numpy(), T, "right") - 1          # last S5 bar closed at or before the click
assert (gi >= 0).all() and (g.c.to_numpy()[gi] <= T).all()
t["ctx_lag_s"] = (T - g.c.to_numpy()[gi]) / NS
rows = g.iloc[gi].reset_index(drop=True)
feat = sign_features(rows, t.s.to_numpy())
out = outcomes(rows, t.s.to_numpy())

# deal price vs the constructed XM price (sanity for the basis correction)
xm = np.where(t.s > 0, rows.ask + basis["basis_ask"], rows.bid + basis["basis_bid"])
print("deal price - constructed XM price at last closed S5 bar: median %.3f, MAD %.3f, p95|.| %.2f" % (
    np.median(t.entry - xm), np.median(np.abs(t.entry - xm - np.median(t.entry - xm))), np.quantile(np.abs(t.entry - xm), .95)))
print("context lag (click - last closed S5 bar): median %.1fs, max %.1fs" % (t.ctx_lag_s.median(), t.ctx_lag_s.max()))

# ---------- time ----------
ot = t.open_time
t["hour_utc"], t["minute"], t["second"] = ot.dt.hour, ot.dt.minute, ot.dt.second
t["hour_ist"] = (ot + pd.Timedelta("5h30min")).dt.hour
t["dow"] = ot.dt.day_name().str[:3]
t["session"] = pd.cut(t.hour_utc, [-1, 6, 11, 16, 20, 23], labels=["asia_00-07", "london_07-12", "ny_am_12-17", "ny_pm_17-21", "rollover_21-24"]).astype(str)

# ---------- book state just before each click ----------
deals = load_deals()
dt_, dp = ns(deals.time), (deals.profit.fillna(0) + deals.commission.fillna(0) + deals.swap.fillna(0)).to_numpy()
S, V, E = t.s.to_numpy(), t.volume.to_numpy(), t.entry.to_numpy()
st = []
for k in range(len(t)):
    open_ = [j for j in range(k) if C[j] > T[k]]
    same = [j for j in open_ if S[j] == S[k]]
    opp = [j for j in open_ if S[j] != S[k]]
    closed = [j for j in range(len(t)) if C[j] <= T[k]]
    r = dict(n_same=len(same), lots_same=V[same].sum(), n_opp=len(opp), lots_opp=V[opp].sum())
    if same:
        vwap = (E[same] * V[same]).sum() / V[same].sum()
        r["same_adverse_vwap"] = S[k] * (vwap - E[k])          # >0: basket under water, this fill is 'better'
        r["same_adverse_last"] = S[k] * (E[same[-1]] - E[k])   # spacing from the previous same-side fill
        r["same_adverse_first"] = S[k] * (E[same[0]] - E[k])
        r["mins_since_basket_start"] = (T[k] - T[same[0]]) / MIN
    if opp:
        vwap_o = (E[opp] * V[opp]).sum() / V[opp].sum()
        r["opp_upl_pts"] = -S[k] * (E[k] - vwap_o)             # opposite basket P&L per lot at this price
    r["net_lots_before"] = S[k] * ((S[open_] * V[open_]).sum())  # signed in the direction of this trade
    r["secs_since_prev_click"] = (T[k] - T[k - 1]) / NS if k else np.nan
    if closed:
        j = max(closed, key=lambda q: C[q])
        r.update(secs_since_last_exit=(T[k] - C[j]) / NS, last_exit_reason=t.exit_reason[j].replace("DEAL_REASON_", ""),
                 last_exit_same_side=bool(S[j] == S[k]), last_exit_net=t.net[j])
    bal = dp[dt_ < T[k]].sum()                                  # balance + bonus credit, realised only
    flo = sum(S[j] * (E[k] - E[j]) * V[j] * 100 for j in open_)  # floating P&L marked at this fill (spread ignored)
    r["equity_before"] = bal + flo
    net_after = abs((S[open_] * V[open_]).sum() + S[k] * V[k])
    r["pts_to_zero_equity"] = (bal + flo) / (net_after * 100) if net_after > 0 else np.inf
    st.append(r)
st = pd.DataFrame(st)

# ---------- decision events, campaigns ----------
gap = np.r_[np.inf, np.diff(T) / NS]
new = (gap > BURST_S) | (np.r_[0, S[:-1]] != S)
t["event_id"] = np.cumsum(new)
t["click_in_event"] = t.groupby("event_id").cumcount()
camp, cid, end = [], 0, -1
for k in range(len(t)):                                         # flat-to-flat campaign: >=1 position open throughout
    if T[k] > end:
        cid += 1
    end = max(end, C[k])
    camp.append(cid)
t["campaign_id"] = camp

df = pd.concat([t, st, feat, out], axis=1)

def role(r):
    if r.n_same:
        return "avg_add" if r.same_adverse_vwap >= ADD_PTS else "pyramid_add" if r.same_adverse_vwap <= -ADD_PTS else "level_add"
    return "hedge" if r.n_opp else "first"

def ctx(r):
    if r.brk60_dir == 1:
        return "breakout"
    if r.ret5_atr_dir >= 1.0:
        return "momentum"
    if r.ret60_dir > 0 and r.ematrend_m5_dir > 0 and r.ret5_dir <= 0:
        return "pullback"
    if r.pos60_dir <= 1 / 3 or r.brk60_dir == -1:
        return "range_fade"
    return "other"

first = df[df.click_in_event == 0].set_index("event_id")
first["role"] = first.apply(role, axis=1)
df["role"] = df.event_id.map(first.role)
df["ctx_type"] = df.event_id.map(first.apply(ctx, axis=1))
df["setup"] = np.where(df.role.eq("avg_add"), "averaging_add", np.where(df.role.eq("hedge"), "hedge", df.ctx_type))
flip = (first.role.eq("first")) & (first.secs_since_last_exit <= 300) & (first.last_exit_same_side == False)  # noqa: E712
df["flip"] = df.event_id.map(flip)
df["win"] = df.net > 0
df["exit_kind"] = df.exit_reason.str.replace("DEAL_REASON_", "") + np.where(df.exit_entry_type.eq("DEAL_ENTRY_OUT_BY"), "_CLOSEBY", "")

keep = (["position_id", "event_id", "click_in_event", "campaign_id", "side", "open_time", "close_time", "volume", "entry", "exit",
         "tp", "sl", "net", "pts", "hold_s", "win", "exit_kind", "role", "ctx_type", "setup", "flip",
         "hour_utc", "hour_ist", "minute", "second", "dow", "session", "ctx_lag_s"]
        + list(st.columns) + list(feat.columns) + list(out.columns))
df[keep].to_csv(HERE / "entries_features.csv", index=False)
print("wrote entries_features.csv", df[keep].shape, "| events", df.event_id.nunique(), "| campaigns", df.campaign_id.nunique())
print(df.groupby("event_id").size().value_counts().sort_index().to_dict(), "= clicks per event")

# ---------- look-ahead self-test: rebuild the features from data truncated at the click ----------
if __name__ == "__main__":
    rng = np.random.default_rng(7)
    raw_cols = [c for c in g.columns if not c.startswith(("fwd", "B_", "S_"))]
    s5c, m1c = ns(s5.time) + 5 * NS, ns(m1.time) + MIN
    worst = 0.0
    for k in rng.choice(len(t), 12, replace=False):
        gt = build_grid(s5[s5c <= T[k]].reset_index(drop=True), m1[m1c <= T[k]].reset_index(drop=True), basis["basis_bid"], fwd=False)
        a, b = gt.iloc[-1][raw_cols].astype(float), g.iloc[gi[k]][raw_cols].astype(float)
        assert gt.c.iloc[-1] == g.c.iloc[gi[k]]
        diff = (a - b).abs().where(~(a.isna() & b.isna()), 0.0).replace(np.inf, 0).fillna(np.inf)
        worst = max(worst, diff.max())
        assert diff.max() < 1e-9, (k, diff[diff >= 1e-9])
    print("look-ahead self-test passed: 12 entries rebuilt from data truncated at the click, max abs diff", worst)

    # first-touch self-test: brute-force bar-by-bar walk vs the vectorised columns, 40 random grid rows
    from lib import TOUCH
    c_all = ns(s5.time) + 5 * NS
    q = s5[["bid_high", "bid_low", "ask_high", "ask_low", "bid_close", "ask_close"]].to_numpy()
    for n in rng.choice(len(g), 40, replace=False):
        i = int(np.searchsorted(c_all, g.c.iloc[n]))
        for name, (tpd, sld, cap) in TOUCH.items():
            exp_b = exp_s = np.nan
            for j in range(i + 1, min(i + 1 + cap, len(q))):
                if np.isnan(exp_b) and (q[j, 1] <= q[i, 5] - sld or q[j, 0] >= q[i, 5] + tpd):
                    exp_b = 0.0 if q[j, 1] <= q[i, 5] - sld else 1.0
                if np.isnan(exp_s) and (q[j, 2] >= q[i, 4] + sld or q[j, 3] <= q[i, 4] - tpd):
                    exp_s = 0.0 if q[j, 2] >= q[i, 4] + sld else 1.0
            assert np.array_equal([exp_b, exp_s], [g[f"B_{name}"].iloc[n], g[f"S_{name}"].iloc[n]], equal_nan=True), (n, name)
    print("first-touch self-test passed: 40 rows x", len(TOUCH), "exit geometries match a brute-force walk")
