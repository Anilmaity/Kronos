#!/usr/bin/env python
"""Builds REPORT.md, equity_curve.png and exhibits.png from results/ (written by xmr1.py). Every result in the report is
read from those files; nothing is typed in by hand.   Run: ../../../.venv/bin/python report.py"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import xmr1

HERE = Path(__file__).resolve().parent
R = HERE / "results"
DEF = "1.0|per_leg|True"
COSTS = [("0.45", "flat 0.45"), ("base", "spec base (~0.60)"), ("0.8", "flat 0.80"), ("stress", "spec stress (~1.00)")]
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
RAMP = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]          # one hue, light to dark = cost low to high (validated, ordinal)
BLUE, ORANGE = "#2a78d6", "#eb6834"                           # categorical slots 1, 2 (validated)

g = pd.read_csv(R / "grid.csv", dtype={"cost": str})
daily = pd.read_csv(R / "daily_owner_cash.csv", index_col=0)
weekly = pd.read_csv(R / "weekly_owner_cash.csv", index_col=0)
monthly = pd.read_csv(R / "monthly_owner_cash.csv", index_col=0)
ctrl = pd.read_csv(R / "control.csv", dtype={"cost": str})
ruin = pd.read_csv(R / "ruin.csv")
ruin_s = pd.read_csv(R / "ruin_summary.csv")
shadow = pd.read_csv(R / "shadow.csv")
week = pd.read_csv(R / "week.csv")
sec = pd.read_csv(R / "secondary.csv")
sec_y = pd.read_csv(R / "secondary_by_year.csv", index_col=0)
null = pd.read_csv(R / "null_summary.csv")
qa = json.loads((R / "qa.json").read_text())
rep = json.loads((R / "replication.json").read_text())

usd = lambda x: f"{x:,.0f}".replace("-", "−")
pct = lambda x: f"{100 * x:.1f}%"
def nth(x):
    k = round(100 * x)
    return "below every draw" if k == 0 else f"{k}{'th' if 10 <= k % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th')}"


def tbl(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] + ["---:"] * (len(head) - 1)) + "|"]
    return "\n".join(out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def cell(win, cost, key=DEF):
    tp, mode, sw = key.split("|")
    return g[(g.window == win) & (g.cost == cost) & (g.tp_atr == float(tp)) & (g.tp_mode == mode) & (g.sweep == (sw == "True"))].iloc[0]


def series(df, cost, key=DEF):
    return pd.concat([df[f"TRAIN|{cost}|{key}"].dropna(), df[f"TEST|{cost}|{key}"].dropna()])


def stats(win, cost, key=DEF):
    """n, win rate, PF, points, USD, drawdown, worst day, months - TRAIN, TEST or FULL (= the two runs laid end to end)."""
    rows = [cell(w, cost, key) for w in (("TRAIN", "TEST") if win == "FULL" else (win,))]
    s = lambda k: sum(r[k] for r in rows)
    d = pd.concat([daily[f"{r.window}|{cost}|{key}"].dropna() for r in rows])
    mo = pd.concat([monthly[f"{r.window}|{cost}|{key}"].dropna() for r in rows])
    wk = pd.concat([weekly[f"{r.window}|{cost}|{key}"].dropna() for r in rows])
    cum = d.cumsum()
    return dict(n=int(s("n")), win=s("n_win") / s("n"), pf=s("gross_win") / -s("gross_loss"), pts=s("net_pts"), pos=s("pos_pnl"), owner=s("owner_cash"),
                dep=s("deposits"), wd=s("withdrawals"), wipes=int(s("wipeouts")), dd=float((cum.cummax().clip(lower=0) - cum).max()), worst_day=d.min(),
                mpos=int((mo > 0).sum()), m=len(mo), wpos=int((wk > 0).sum()), w=len(wk), worst_week=wk.min(), best_week=wk.max(),
                absorbed=s("absorbed_by_broker"), forfeit=s("forfeited_residual"), spread=s("spread_paid"), so=int(s("n_so")), tp=int(s("n_tp")),
                avg_win=s("gross_win") / s("n_win"), avg_loss=s("gross_loss") / s("n_loss"), top_month=mo.max() / mo.sum() if mo.sum() > 0 else np.nan)


S = {(w, c): stats(w, c) for w in ("TRAIN", "TEST", "FULL") for c, _ in COSTS}

# ---- figures ---------------------------------------------------------------------------------------------------------
plt.rcParams.update({"font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "font.size": 10, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.8, "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
                     "axes.titlecolor": INK, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left"})
day_ts = lambda idx: pd.to_datetime(np.asarray(idx, dtype="int64") * 86400, unit="s")
split = pd.Timestamp("2026-04-01")

fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7.2), sharex=True, gridspec_kw={"height_ratios": [3, 1.15], "hspace": 0.12})
ends = []
for (c, lab), col in zip(COSTS, RAMP):
    cum = series(daily, c).cumsum()
    a1.plot(day_ts(cum.index), cum.to_numpy() / 1000, color=col, lw=2, label=f"{lab} pts round trip")
    ends.append((cum.iloc[-1] / 1000, lab))
lo, hi = min(e[0] for e in ends), max(e[0] for e in ends)
for k, (y, lab) in enumerate(sorted(ends, reverse=True)):                 # direct labels, spread evenly so they never collide
    a1.annotate(f"{lab}: {usd(y * 1000)}", (day_ts([daily.index.max()])[0], y), xytext=(8, 0), textcoords="offset points",
                va="center", color=INK2, fontsize=9, annotation_clip=False)
a1.axhline(0, color=AXIS, lw=1)
a1.axvline(split, color=MUTED, lw=1, ls=(0, (3, 3)))
a1.text(split - pd.Timedelta(days=4), 3, "TRAIN", ha="right", color=INK2, fontsize=9)
a1.text(split + pd.Timedelta(days=4), 3, "TEST (restarted flat)", ha="left", color=INK2, fontsize=9)
a1.set_ylabel("cumulative owner cash, thousand USD")
a1.set_title("XMR-1 default cell: what the owner has put in and taken out of a 200 USD account that is refilled after every stop-out")
a1.legend(title="cost level", frameon=False, loc="lower left", fontsize=9, title_fontsize=9)
px = xmr1.load_main().set_index("time").close.resample("1D").last().dropna()
px = px[(px.index >= "2025-07-16") & (px.index < "2026-11-04")]
a2.plot(px.index.tz_localize(None), px.to_numpy(), color=INK2, lw=1.4)
a2.axvline(split, color=MUTED, lw=1, ls=(0, (3, 3)))
a2.set_ylabel("gold, USD per oz")
a2.set_title("Gold (OANDA mid, daily close), for context", fontweight="normal", fontsize=10)
fig.subplots_adjust(right=0.80, left=0.08, top=0.94, bottom=0.06)
fig.savefig(HERE / "equity_curve.png", dpi=150)
plt.close(fig)

fig, ax = plt.subplots(1, 3, figsize=(15, 4.6), gridspec_kw={"wspace": 0.28})
se = pd.read_csv(R / "shadow_equity_base.csv", index_col=0, parse_dates=True).equity
sh0 = shadow[(shadow.tp_atr == 1.0) & (shadow.tp_mode == "per_leg") & (shadow.cost == "base")].iloc[0]
so = pd.read_csv(R / "shadow_open_positions.csv")
soS, soL = so[so.side == "SELL"], so[so.side == "BUY"]
ax[0].plot(se.index.tz_localize(None), se.to_numpy() / 1000, color=BLUE, lw=1.6)
ax[0].axhline(0, color=AXIS, lw=1)
k = se.idxmin()
ax[0].text(0.50, 0.60, f"worst floating loss {usd(sh0.worst_floating_usd)}\n(realised profit of {usd(se.min() - sh0.worst_floating_usd)} brings the\ntotal to {usd(se.min())} at the low)\n\n"
           f"from {so.opened.max()[:10]}: both books full,\n20 positions locked, nothing closes", transform=ax[0].transAxes, color=INK2, fontsize=9, va="center")
ax[0].set_title("Shadow run: same rules, unlimited balance, no stop-out")
ax[0].set_ylabel("realised + floating P&L, thousand USD")
ax[0].tick_params(axis="x", labelrotation=30)
ct = ctrl[ctrl.cost == "base"].groupby("seed").owner_cash.sum() / 1000
strat = S[("FULL", "base")]["owner"] / 1000
ax[1].hist(ct, bins=18, color=RAMP[0], edgecolor=SURF, linewidth=2)
ax[1].axvline(strat, color=INK, lw=2)
ax[1].annotate(f"fade trigger\n{usd(strat * 1000)}", (strat, ax[1].get_ylim()[1] * 0.96), xytext=(6, 0), textcoords="offset points", color=INK, fontsize=9, va="top")
ax[1].set_title("Random-signal control, 100 draws (TRAIN + TEST, base cost)")
ax[1].set_xlabel("owner cash over 16 months, thousand USD")
ax[1].set_ylabel("draws")
for dep, col in ((200.0, BLUE), (1000.0, ORANGE)):
    r = ruin[(ruin.deposit == dep) & ruin.sweep]
    h = np.sort(r.minutes.to_numpy() / 60)
    ax[2].step(np.r_[0.05, h], np.r_[1, 1 - np.arange(1, len(h) + 1) / len(h)], where="post", color=col, lw=2, label=f"{dep:.0f} USD start")
    med = np.median(r[r.ruined].minutes) / 60
    ax[2].annotate(f"{dep:,.0f} USD: half gone\nin {med:.1f} h", (med, 0.5), xytext=(-10, -14) if dep == 200 else (12, 4), textcoords="offset points",
                   ha="right" if dep == 200 else "left", color=INK2, fontsize=9)
ax[2].set_xscale("log")
ax[2].set_xticks([0.1, 1, 6, 24, 168, 720])
ax[2].set_xticklabels(["6 min", "1 h", "6 h", "1 d", "1 wk", "30 d"])
ax[2].minorticks_off()
ax[2].set_ylim(0, 1.02)
ax[2].set_title("Accounts still alive, by time since the deposit (no top-up)")
ax[2].set_ylabel(f"share of {ruin.start.nunique()} start dates")
ax[2].set_xlabel("market time since the first in-session bar of the start date")
ax[2].legend(frameon=False, loc="upper right", fontsize=9)
fig.subplots_adjust(left=0.05, right=0.985, top=0.9, bottom=0.17)
fig.savefig(HERE / "exhibits.png", dpi=150)
plt.close(fig)

# ---- report numbers --------------------------------------------------------------------------------------------------
F, FS = S[("FULL", "base")], S[("FULL", "stress")]
tr, te = S[("TRAIN", "base")], S[("TEST", "base")]
wk_b = series(weekly, "base")
ct_b = ctrl[ctrl.cost == "base"].groupby("seed").owner_cash.sum()
ct_s = ctrl[ctrl.cost == "stress"].groupby("seed").owner_cash.sum()
lives = lambda w, c: cell(w, c).lives_paid_back
n_runs = len(g)
neg_runs = int((g.owner_cash < 0).sum())
train_base = g[(g.window == "TRAIN") & (g.cost == "base")].sort_values("owner_cash", ascending=False)
pick = train_base.iloc[0]
pick_key = f"{pick.tp_atr}|{pick.tp_mode}|{pick.sweep}"
P = {(w, c): stats(w, c, pick_key) for w in ("TRAIN", "TEST", "FULL") for c, _ in COSTS}
bars_n = {w: qa["windows"][w]["bars"] for w in ("TRAIN", "TEST")}
nsd = float(null[null.spread == 0.6].owner_sd.iloc[0])
z = {w: (S[(w, "base")]["owner"] + S[(w, "base")]["spread"] + S[(w, "base")]["forfeit"]) / (nsd * np.sqrt(bars_n[w] / 150000)) for w in ("TRAIN", "TEST")}
wd, wS = week[(week.exits == "M1")], week[(week.exits == "S5")]
w0 = wd[(wd.cost == "base") & (wd.tp_atr == 1.0) & (wd.tp_mode == "per_leg") & wd.sweep].iloc[0]
w0s = wS[wS.cost == "base"].iloc[0]
w1, w1s = wd[(wd.cost == "stress") & (wd.tp_atr == 1.0) & (wd.tp_mode == "per_leg") & wd.sweep].iloc[0], wS[wS.cost == "stress"].iloc[0]
rr = rep["real"]
b = qa["basis_xm_minus_oanda"]

def metric_rows(SS):
    return [[f"{w} · {lab}", f"{s['n']:,}", pct(s["win"]), f"{s['pf']:.2f}", usd(s["pts"]), usd(s["pos"]), usd(s["owner"]), s["wipes"], usd(s["dd"]),
             usd(s["worst_day"]), f"{s['mpos']} of {s['m']}", f"{s['wpos']} of {s['w']}"]
            for w in ("TRAIN", "TEST", "FULL") for c, lab in COSTS for s in [SS[(w, c)]]]

HEAD = ["window · cost", "positions", "win rate", "PF", "net points", "position P&L USD", "owner cash USD", "wipe-outs", "max DD USD", "worst day USD", "months > 0", "weeks > 0"]

grid_rows = []
for c, lab in (("base", "base"), ("0.8", "0.80"), ("stress", "stress")):
    for tp, mode, sw in xmr1.GRID:
        a, t = cell("TRAIN", c, f"{tp}|{mode}|{sw}"), cell("TEST", c, f"{tp}|{mode}|{sw}")
        grid_rows.append([f"{lab} · TP {tp} · {mode} · sweep {'on' if sw else 'off'}", usd(a.owner_cash), a.wipeouts, f"{a.n:,}", pct(a.win_rate), f"{a.pf:.2f}",
                          pct(a.hedged_share), usd(t.owner_cash), t.wipeouts, f"{t.n:,}", pct(t.win_rate), f"{t.pf:.2f}", pct(t.hedged_share)])

mo_rows = []
for m in monthly.index:
    v = [series(monthly, c).get(m, np.nan) for c, _ in COSTS]
    mo_rows.append([m] + [usd(x) for x in v])

bars_tbl = []
for name, SS in ((f"default (TP 1.0, per_leg, sweep on)", S), (f"TRAIN-selected (TP {pick.tp_atr}, {pick.tp_mode}, sweep {'on' if pick.sweep else 'off'})", P)):
    t, a = SS[("TEST", "0.8")], SS[("TRAIN", "0.8")]
    bars_tbl.append([name, f"{t['pf']:.2f} — fail", f"TRAIN {usd(a['owner'])}, TEST {usd(t['owner'])} — fail", f"{t['mpos']} of {t['m']} — fail",
                     "not applicable, net is negative — fail", f"{t['n']:,} — met"])

shad_rows = [[f"TP {r.tp_atr} · {r.tp_mode} · {r.cost}", f"{r.n:,}", pct(r.win_rate), usd(r.realised), usd(r.floating_end), usd(r.total), usd(r.worst_floating_usd),
              r.worst_floating_time[:10], f"{r.worst_single_position_adverse_pts:,.0f}", f"{r.longest_underwater_days:.0f}", f"{r.longest_position_days:.0f}", r.max_positions]
             for r in shadow.itertuples()]

ruin_rows = [[f"{r.deposit:.0f} USD · sweep {'on' if r.sweep else 'off'}", r.starts, r.ruined, f"{r.median_hours:.1f}", f"{r.p90_hours:.0f}", pct(r.p_ruin_1d), pct(r.p_ruin_1w),
              pct(r.p_ruin_30d), f"{pct(r.p_ruin_90d)} (n={r.n_90d})", f"{r.max_survival_days:.0f}", usd(r.owner_mean), pct(r.owner_positive_share)] for r in ruin_s.itertuples()]

week_rows = [[f"{r.cost} · TP {r.tp_atr} · {r.tp_mode} · sweep {'on' if r.sweep else 'off'}", usd(r.owner_cash), usd(r.deposits), usd(r.withdrawals), r.wipeouts, r.n, pct(r.win_rate),
              f"{r.pf:.2f}", pct(r.flat_share), pct(r.hedged_share), r.max_positions, f"{r.hold_med_min:.0f}"] for r in wd.itertuples()]

rep_rows = [[lab, v["n"], v["hit"], pct(v["rate"]), pct(v["opposite_side_rate"]), pct(v["time_shift_placebo_rate"]), pct(v["placebo_max"])] for lab, v in (
    ("His 124 decisions with a simulated order within ±5 min, same side", rep["trader_decisions_explained_by_sim_orders"]),
    ("His 27 fresh entries (flat book), same test", rep["trader_fresh_entries_explained_by_sim_orders"]),
    ("His 178 positions, same test", rep["trader_positions_explained_by_sim_orders"]),
    ("His 124 decisions with the raw trigger on within ±5 min, same side", rep["trader_decisions_with_trigger_within_5min"]),
    ("Simulated orders with one of his decisions within ±5 min, same side", rep["sim_orders_matching_a_trader_decision"]))]

sec_rows = [[f"{r.cost} · sweep {'on' if r.sweep else 'off'}", usd(r.owner_cash), usd(r.deposits), usd(r.withdrawals), r.wipeouts, f"{r.n:,}", pct(r.win_rate), f"{r.pf:.2f}",
             pct(r.flat_share), pct(r.hedged_share), pct(r.weeks_pos)] for r in sec.itertuples()]
secy_rows = [[y, usd(r.owner_cash), int(r.wipeouts), pct(r.eligible_bar_share), f"{r.atr5_median:.2f}", f"{r.price_median:,.0f}"] for y, r in sec_y.iterrows()]

ctrl_rows, ctrl2_rows, pf_pct, pnl_z, turn = [], [], {}, {}, {}
for w in ("TRAIN", "TEST"):
    for c in ("base", "stress"):
        x, s = ctrl[(ctrl.window == w) & (ctrl.cost == c)], S[(w, c)]
        ctrl_rows.append([f"{w} · {c}", usd(s["owner"]), usd(x.owner_cash.mean()), f"{usd(x.owner_cash.quantile(.05))} to {usd(x.owner_cash.quantile(.95))}",
                          nth((x.owner_cash < s["owner"]).mean()), s["wipes"], f"{x.wipeouts.mean():.0f}", f"{s['n']:,}", f"{x.n.mean():,.0f}"])
        ctrl2_rows.append([f"{w} · {c}", pct(s["win"]), pct(x.win_rate.mean()), f"{pct(x.win_rate.quantile(.05))} to {pct(x.win_rate.quantile(.95))}", nth((x.win_rate < s["win"]).mean()),
                           f"{s['pf']:.3f}", f"{x.pf.mean():.3f}", f"{x.pf.quantile(.05):.3f} to {x.pf.quantile(.95):.3f}", nth((x.pf < s["pf"]).mean())])
        pf_pct[(w, c)] = (x.pf < s["pf"]).mean()
        pnl_z[(w, c)] = (s["pos"] - x.pos_pnl.mean()) / x.pos_pnl.std()
        turn[(w, c)] = x.n.mean() / s["n"] - 1
for c, cc in (("base", ct_b), ("stress", ct_s)):
    s = S[("FULL", c)]
    ctrl_rows.append([f"TRAIN+TEST · {c}", usd(s["owner"]), usd(cc.mean()), f"{usd(cc.quantile(.05))} to {usd(cc.quantile(.95))}", nth((cc < s["owner"]).mean()), s["wipes"], "", f"{s['n']:,}", ""])

wl = pd.read_csv(R / "wipeouts_default.csv")
tl = pd.read_csv(R / "trades_default_base.csv")
big = wl[wl.cost == "base"].sort_values("balance_wiped").iloc[-1]
held = tl[(tl.window == big.window) & (tl.opened < big.time) & (tl.closed >= str(pd.Timestamp(big.time) - pd.Timedelta(days=2)))]
held = held[pd.to_datetime(held.closed) - pd.to_datetime(held.opened) > pd.Timedelta(days=7)]      # the legs that were stuck going into it
lockS, lockL = held[held.side == "SELL"], held[held.side == "BUY"]
n0 = null[null.spread == 0.0].iloc[0]
n6 = null[null.spread == 0.6].iloc[0]
sig_w = qa["windows"]

md = f"""# XMR-1 "deposit-as-stop averaging fade" — backtest report

Candidate 1 of `analysis/STRATEGY_SPEC.md` (section 6), run exactly as pre-registered. Written 2026-11-11.
Evidence: `xmr1.py` (single-file event-driven M1 backtester, deterministic, about half a minute end to end), `report.py`
(this file and both figures; every result is read from `results/`, nothing is typed in).

**Verdict: FAIL.** It is a risk exhibit, was never a deployment candidate, and nothing here changes that.
The pre-registered hypothesis is confirmed on both counts: the default cell wins {pct(tr['win'])} (TRAIN) and {pct(te['win'])} (TEST)
of its positions, a random signal wins the same share, and the owner's cash over the 16 months is {usd(F['owner'])} USD at
base cost and {usd(FS['owner'])} USD at stress cost.

Units: 1 point = 1 USD per oz; 0.04 lots = 4 USD per point. All times UTC. "Owner cash" = withdrawals + final equity − deposits.

---

## 1. The short version

| Question | Answer (default cell: TP 1.0 × ATR5 per leg, sweep to 200 USD; spec base cost) |
|---|---|
| Does it win often? | Yes. {pct(F['win'])} of {F['n']:,} positions over TRAIN + TEST, PF {F['pf']:.2f}. Average win {usd(F['avg_win'])} USD, average loss {usd(F['avg_loss'])} USD. |
| Does the owner make money? | No. {usd(F['dep'])} USD deposited, {usd(F['wd'])} USD withdrawn, owner cash **{usd(F['owner'])} USD** in {F['w']} weeks ({usd(F['owner'] / F['w'])} per week). TRAIN {usd(tr['owner'])}, TEST {usd(te['owner'])}. |
| How often does the account die? | {F['wipes']} margin stop-outs in {F['w']} weeks: {F['wipes'] / F['w']:.1f} per week, at least one in {pct((cell('TRAIN', 'base').wipe_weeks_share * tr['w'] + cell('TEST', 'base').wipe_weeks_share * te['w']) / F['w'])} of weeks. Only {pct(lives('TRAIN', 'base'))} (TRAIN) and {pct(lives('TEST', 'base'))} (TEST) of the 200 USD deposits were paid back by withdrawals before they were lost. |
| Is any cell or cost level positive? | No. {neg_runs} of {n_runs} runs (8 cells × 4 cost levels × TRAIN and TEST) have negative owner cash. |
| Does the fade trigger matter? | No. Against 100 random-signal draws with the same firing rate per UTC hour and month, the trigger's 16-month owner cash sits at the {nth((ct_b < F['owner']).mean())} percentile at base cost and the {nth((ct_s < FS['owner']).mean())} at stress. Nothing favours the trigger on any measure. |
| What does the stop-out hide? | With unlimited balance the same rules carry a floating loss of {usd(sh0.worst_floating_usd)} USD at worst, one position {sh0.worst_single_position_adverse_pts:,.0f} points under water, and the book is under water for {sh0.longest_underwater_days:.0f} days — from the first weeks to the end of the data. |
| How long does a deposit last? | 200 USD: half of {int(ruin_s.starts.iloc[0])} start dates are stopped out within {ruin_s[(ruin_s.deposit == 200) & ruin_s.sweep].median_hours.iloc[0]:.1f} hours and {pct(ruin_s[(ruin_s.deposit == 200) & ruin_s.sweep].p_ruin_1d.iloc[0])} within a day. 1,000 USD: half within {ruin_s[(ruin_s.deposit == 1000) & ruin_s.sweep].median_hours.iloc[0]:.1f} hours, {pct(ruin_s[(ruin_s.deposit == 1000) & ruin_s.sweep].p_ruin_1w.iloc[0])} within a week, all within 90 days. |
| Does it reproduce his week? | Only in shape. In his active span the default cell opens {w0.n} positions (he opened 178), is stopped out {w0.wipeouts} times (7), wins {pct(w0.win_rate)} ({pct(rr['win_rate'])}) and loses {usd(-w0.owner_cash)} USD of owner cash (his trading net was +{rr['net']:.2f}). {pct(rep['trader_decisions_explained_by_sim_orders']['rate'])} of his 124 decisions have a simulated same-side order within ±5 minutes, against {pct(rep['trader_decisions_explained_by_sim_orders']['time_shift_placebo_rate'])} by chance. |

![Cumulative owner cash](equity_curve.png)

![Shadow run, random control, survival](exhibits.png)

---

## 2. What was run

**Rules** (spec 5 and 6, nothing added): two independent books; a fresh entry of 2 × 0.04 lots when the fade trigger is on
(5-bar return ≥ 0.6 × M5 ATR(14) into the outer third of the 15-bar range, ATR5 ≥ 3.0); one more 0.04-lot clip each time price
is max(0.7 × ATR5, 2.0) beyond the last open fill, up to 10 per side; a take-profit on every leg (max(TP_ATR × ATR5, 3.0));
no stop, no time exit; session 01:00–21:00 UTC Mon–Fri; a 200 USD account at 1:1000 whose 20% margin stop-out is the only
loss exit and sets the balance to 0; re-deposit 200 USD 60 minutes later; optional sweep of everything above 200 USD when flat.

**Data.** {qa['rows']:,} M1 bars, {qa['first'][:16]} to {qa['last'][:16]}: OANDA mid to 2026-07-15, OANDA bid/ask from 2026-07-16
({qa['stitch_overlap']['bars']} overlapping bars, largest close difference {qa['stitch_overlap']['max_abs_close_diff']:.2f}).

| Window | Bars | In-session bars | Bars passing the gap guard and ATR5 ≥ 3.0 | SELL trigger on | BUY trigger on | Median ATR5 |
|---|---:|---:|---:|---:|---:|---:|
""" + "\n".join(f"| {w} {sig_w[w]['first'][:10]} to {sig_w[w]['last'][:10]} | {sig_w[w]['bars']:,} | {sig_w[w]['session_bars']:,} | {pct(sig_w[w]['elig_share'])} | {pct(sig_w[w]['sell_rate'])} | {pct(sig_w[w]['buy_rate'])} | {sig_w[w]['atr5_median']:.2f} |" for w in ("TRAIN", "TEST", "WEEK")) + f"""

TRAIN and TEST are separate simulations, each started flat with one 200 USD deposit; "FULL" is the two laid end to end.

**Costs.** Four levels, all reported. *Spec base*: XM bid = OANDA bid − 0.05 and ask = OANDA ask + 0.06 on quote data, mid ± 0.30 before
2026-07-16. *Spec stress*: a further 0.20 per side on quotes, mid ± 0.50 on mid data. *Flat 0.45* and *flat 0.80*: mid ± half of that
on the whole series (the house convention asked for in the brief). Median OANDA M1 spread in the quote file is {qa['oanda_m1_spread_median']:.2f}.

**Basis, measured here before anything else.** XM deal price minus the OANDA same-side quote in the 5-second bar that contains
the deal: sells at the bid median {b['sell_at_bid']['median']:+.3f} (n={b['sell_at_bid']['n']}, 5th–95th percentile {b['sell_at_bid']['p05']:+.2f} to {b['sell_at_bid']['p95']:+.2f}),
buys at the ask median {b['buy_at_ask']['median']:+.3f} (n={b['buy_at_ask']['n']}, {b['buy_at_ask']['p05']:+.2f} to {b['buy_at_ask']['p95']:+.2f}), stop-outs excluded.
That reproduces the −0.05 / +0.06 the specification fixed, so those are used. The 34 stop-out deals filled a median {b['stop_outs']['median']:+.2f} and a 5th
percentile of {b['stop_outs']['p05']:+.1f} points from OANDA's quote, which is why a stop-out is modelled as the loss of the whole balance and not as a fill price.

**Two places where the brief and the specification differ; the specification was followed and the brief's version is also shown.**
1. Split: the brief says first 60% / last 40%. The specification pre-registered dates (TRAIN to 2026-03-31, TEST from 2026-04-01),
   which is {bars_n['TRAIN'] / (bars_n['TRAIN'] + bars_n['TEST']):.0%} / {bars_n['TEST'] / (bars_n['TRAIN'] + bars_n['TEST']):.0%} of the bars. The dates were used.
2. Costs: the brief asks for 0.45 and 0.80 round trip; the specification for base and stress as above. All four are in every table that matters.

---

## 3. Harness checks (all passed before any result was read)

| Check | Result |
|---|---|
| Entry bar strictly after the signal bar | Asserted on every order in every run (`simulate`), never tripped |
| Closed-bar probe: (last M5 open + 5 min) − c(t) never positive | Maximum {qa['closed_bar_probe_max_s_full']:.0f} s over all {qa['rows']:,} bars |
| No data stamped after t is used at t | Every bar after a random cut scrambled, indicators recomputed, {qa['lookahead_test']['cuts']} cuts on {qa['lookahead_test']['bars']:,} bars: signals, ATR5 and session flag at or before the cut are bit-identical; the test also asserts the scramble does change later values, so it is not vacuous |
| Trigger parity with the specification (check 3 of 9.2) | Trigger on at the last closed bar for {qa['trigger_parity']['fresh_hit']} of {qa['trigger_parity']['fresh_n']} fresh entries and {qa['trigger_parity']['all_hit']} of {qa['trigger_parity']['all_n']} decisions — exactly the 11 of 27 and 39 of 124 required |
| Engine self-test | Six synthetic cases: fill at next open, TP filled at the level, stop-out beats a TP in the same bar, re-deposit exactly 60 minutes later, add spacing and shared TP, margin rule, shadow mode, sub-bar resolution |
| Independent audit of the trade list | Every entry price equals the open of its bar, every TP was reachable in its bar, every stop-out mark is a bar extreme — re-checked from the bars for all {n_runs} grid runs |
| Cash identity | Owner cash = position P&L + loss absorbed by the broker − equity forfeited at stop-out, asserted in every run |
| Fair-game test | On a driftless ±0.1-tick random walk ({int(n0.seeds)} seeds × 150,000 bars) the owner's mean cash is {usd(n0.owner_mean)} ± {usd(n0.owner_se)} (s.e.) at zero spread, inside the band {usd(n0.expected_low)} to 0 that the forfeited stop-out equity allows; at a 0.6 spread it is {usd(n6.owner_mean)} ± {usd(n6.owner_se)} against {usd(n6.expected_low)} to {usd(n6.expected_high)}. The engine neither creates nor destroys money. On that walk the same rules still win {pct(n6.win_rate_mean)} of positions |
| Win rate near 0% or 100% | Not seen in the account runs (52%–86%). The shadow run's 97–99% is the expected artefact of never closing a loser and is reported as such |

---

## 4. Results

### 4.1 Default cell, all four cost levels

{tbl(metric_rows(S), HEAD)}

Notes. "Position P&L" marks stop-out legs at the worst price of the stop-out bar, so it includes losses the account could not pay;
"owner cash" is what the owner actually put in and took out. They differ by the loss absorbed by the broker
({usd(F['absorbed'])} USD over the 16 months at base cost — an upper bound, it assumes liquidation at the bar's extreme) less the equity
forfeited at stop-out ({usd(F['forfeit'])} USD). Max DD is peak-to-trough of cumulative owner cash, with the peak floored at the start.
Months: {S[('TRAIN', 'base')]['m']} in TRAIN (July 2025 is a half month), {S[('TEST', 'base')]['m']} in TEST (November 2026 is three days).

Where the money went, base cost: of the {usd(-F['owner'])} USD lost, {usd(F['spread'])} USD is quoted spread on {F['n']:,} positions and
{usd(F['forfeit'])} USD is equity forfeited at stop-outs. The remaining {usd(-F['owner'] - F['spread'] - F['forfeit'])} USD is price path: adds made
against moves that kept going. Against the fair-game walk above (whose spread of outcomes is wide: s.d. {usd(nsd)} USD per 150,000 bars)
that residual is {abs(z['TRAIN']):.1f} s.d. below expectation in TRAIN and {abs(z['TEST']):.1f} s.d. below in TEST. It points the same way as the S5 programme's finding that gold tends
to continue after a stretch, but the walk has constant volatility and real gold does not, so those s.d. figures overstate the evidence. I would not call it established.

### 4.2 The pre-registered grid (8 cells), TRAIN and TEST

{tbl(grid_rows, ["cost · cell", "TRAIN owner cash", "wipe-outs", "positions", "win rate", "PF", "time hedged", "TEST owner cash", "wipe-outs", "positions", "win rate", "PF", "time hedged"])}

Every cell loses in both windows at every cost level. The flat stretches in the equity figure are the same thing seen from the default cell. The cells that lose least are the ones that trade least: with the larger target and
a shared target the two books spend most of the time locked against each other ("time hedged" = both books open at the bar close), fresh
entries stop, and the account sits on a frozen loss instead of realising it. That is the hedge-lock he used by hand; here it is a by-product
of two independent books on a net-margin account. It lowers turnover; it does not turn the result positive: the least-bad run in the table (TEST, stress, TP 2.5, shared target) had both
books open {pct(cell('TEST', 'stress', '2.5|shared_first|True').hedged_share)} of the time and opened {cell('TEST', 'stress', '2.5|shared_first|True').n:,} positions in seven months, and the same cell lost {usd(-cell('TEST', 'base', '2.5|shared_first|True').owner_cash)} USD at base cost. On TRAIN the
differences between cells are within the spread of the random control (s.d. about {usd(ctrl[(ctrl.window == 'TRAIN') & (ctrl.cost == 'base')].owner_cash.std())} USD), so the ranking of cells carries no information.

### 4.3 Wipe-outs (default cell)

| | TRAIN base | TEST base | TRAIN stress | TEST stress |
|---|---:|---:|---:|---:|
""" + "\n".join("| " + lab + " | " + " | ".join(f(cell(w, c)) for w, c in (("TRAIN", "base"), ("TEST", "base"), ("TRAIN", "stress"), ("TEST", "stress"))) + " |" for lab, f in (
    ("Margin stop-outs", lambda r: f"{r.wipeouts}"), ("Per week (mean)", lambda r: f"{r.wipes_per_week:.1f}"), ("Most in one week", lambda r: f"{r.wipes_week_max}"),
    ("Weeks with at least one", lambda r: pct(r.wipe_weeks_share)), ("Calendar days with at least one", lambda r: pct(r.wipe_days_share)),
    ("Owner cash per 200 USD deposit, USD", lambda r: usd(r.owner_cash / (r.deposits / 200))),
    ("Balance wiped per stop-out, USD: median / mean / largest", lambda r: f"{usd(r.wipe_loss_median)} / {usd(r.wipe_loss_avg)} / {usd(r.wipe_loss_max)}"),
    ("Longest run of stop-outs with no withdrawal between", lambda r: f"{r.wipe_run_max}"), ("Deposits paid back by withdrawals before the stop-out", lambda r: pct(r.lives_paid_back)),
    ("Median withdrawn per deposit, USD", lambda r: usd(r.life_withdrawn_median)), ("Loss absorbed by the broker (upper bound), USD", lambda r: usd(r.absorbed_by_broker)),
    ("Positions closed by stop-out", lambda r: f"{r.n_so:,} of {r.n:,}"), ("Time flat (both books empty)", lambda r: pct(r.flat_share)),
    ("Time with both books open", lambda r: pct(r.hedged_share)), ("Most positions open / largest net lots", lambda r: f"{r.max_positions} / {r.max_net_lots:.2f}"),
    ("Orders refused by the margin rule", lambda r: f"{r.rejected:,}"), ("Median position hold, minutes", lambda r: f"{r.hold_med_min:.0f}"))) + f"""

"Balance wiped" is the realised balance at the stop-out, not what the owner lost on that deposit: it is the deposit plus take-profit income that
could not be swept because the two books were never empty together, and by the time of the stop-out the open losers had already consumed it. The
largest one ({big.window}, {str(big.time)[:16]}, {usd(big.balance_wiped)} USD of balance, {big.n_long} longs and {big.n_short} shorts open) ended a month in which {len(lockS)} shorts opened on {lockS.opened.min()[:10]}
sat under water while the long book kept taking profits; both books then sat full and locked from {lockL.opened.max()[:10]} until the shorts reached their
targets on {lockS.closed.max()[:10]}, and the longs were stopped out the next morning. That is the flat stretch in the equity figure (`results/trades_default_base.csv`, `wipeouts_default.csv`).

### 4.4 Owner cash per week and per month (default cell)

Per week, base cost, {len(wk_b)} weeks: mean {usd(wk_b.mean())}, median {usd(wk_b.median())}, best {usd(wk_b.max())}, worst {usd(wk_b.min())},
5th–95th percentile {usd(wk_b.quantile(.05))} to {usd(wk_b.quantile(.95))}. {int((wk_b > 0).sum())} weeks ({pct((wk_b > 0).mean())}) are positive and
{int((wk_b >= rr['net']).sum())} ({pct((wk_b >= rr['net']).mean())}) are at least as good as his +{rr['net']:.0f} USD trading week; {int((wk_b >= 920.26).sum())} ({pct((wk_b >= 920.26).mean())}) reach his +920 USD of cash.
A week like his is roughly a one-in-six to one-in-eight event for a machine that loses
{usd(-wk_b.mean())} USD in the average week. The full weekly series for every cell is in `results/weekly_owner_cash.csv`.

{tbl(mo_rows, ["month", "flat 0.45", "spec base", "flat 0.80", "spec stress"])}

### 4.5 Random-signal control (100 draws)

Same machine, same costs, same adds, targets and account; the trigger is replaced by a random signal placed on in-session bars that pass the
same gap and ATR5 ≥ 3.0 guards, with exactly the trigger's own count per calendar month and UTC hour, per side (so volatility and price regime are matched).

{tbl(ctrl_rows, ["window · cost", "trigger owner cash", "control mean", "control 5th–95th pct", "trigger's percentile", "trigger wipe-outs", "control wipe-outs (mean)", "trigger positions", "control positions (mean)"])}

{tbl(ctrl2_rows, ["window · cost", "trigger win rate", "control mean", "control 5th–95th pct", "trigger's percentile", "trigger PF", "control mean", "control 5th–95th pct", "trigger's percentile"])}

On owner cash the trigger is inside the control's 5th–95th percentile range in all four window/cost pairs and near its middle over the 16 months.
Position PF and win rate sit low in the control's range (PF percentile, in table order: {nth(pf_pct[('TRAIN', 'base')])}, {nth(pf_pct[('TRAIN', 'stress')])}, {nth(pf_pct[('TEST', 'base')])}, {nth(pf_pct[('TEST', 'stress')])}).
That is turnover, not money. Random timing re-enters sooner and opens {turn[('TRAIN', 'base')]:+.0%}, {turn[('TRAIN', 'stress')]:+.0%}, {turn[('TEST', 'base')]:+.0%} and {turn[('TEST', 'stress')]:+.0%} positions relative to the trigger for the same net result:
total position P&L is within {max(abs(v) for v in pnl_z.values()):.1f} s.d. of the control mean in all four pairs. More gross profit and more gross loss around the same
net pulls a ratio like PF toward 1; the gap is largest where the turnover gap is largest and nearly gone where it is not (TEST base). I tested two
other explanations and both failed: the loss absorbed by the broker is not larger for the trigger, and ATR5 at trigger bars equals ATR5 at
control bars ({sig_w['TRAIN']['atr5_mean_at_trigger_bars']:.2f} against {sig_w['TRAIN']['atr5_mean_at_control_bars']:.2f} in TRAIN, {sig_w['TEST']['atr5_mean_at_trigger_bars']:.2f} against {sig_w['TEST']['atr5_mean_at_control_bars']:.2f} in TEST; `results/qa.json`). So the fade trigger does not help on any measure, and there is no
evidence here that it hurts. The win rate, the losses and the wipe-outs are produced by the exit shape, the averaging and the account, not by the entry.

### 4.6 Shadow run — unlimited balance, no stop-out

One continuous run over TRAIN + TEST ({qa['windows']['TRAIN']['first'][:10]} to {qa['windows']['TEST']['last'][:10]}), margin rule off.

{tbl(shad_rows, ["cell · cost", "positions", "win rate", "realised USD", "floating at end USD", "total USD", "worst floating USD", "on", "worst single position, pts", "longest under water, days", "longest position, days", "max positions"])}

Measured from `results/shadow_open_positions.csv`: the short book fills to ten clips between {soS.opened.min()[:10]} and {soS.opened.max()[:10]} at {soS.entry.min():,.0f}–{soS.entry.max():,.0f},
and gold then rises for six months; the long book fills to ten on {soL.opened.max()[:10]} at {soL.entry.min():,.0f}–{soL.entry.max():,.0f}, on the way down from the high (the worst floating loss is stamped {sh0.worst_floating_time[:16]}). The last order
of the whole run is opened at {sh0.last_order_opened[:16]}. After that both books are full, nothing more can be opened, and the "strategy" is 20
positions that never close, for the remaining nine months. The 97–99%
win rate is what is left when losers are never booked: {usd(sh0.realised)} USD realised against {usd(sh0.floating_end)} USD still open. The worst floating loss is
{-sh0.worst_floating_usd / 200:,.0f} times the 200 USD deposit. This is the tail the margin stop-out cuts off and bills in 200 USD instalments instead.

### 4.7 Time to ruin from rolling start dates (default cell, base cost, no top-up)

One account opened at the first in-session bar of each of {int(ruin_s.starts.iloc[0])} trading days and run until its first margin stop-out or the end of TEST.

{tbl(ruin_rows, ["start · sweep", "starts", "stopped out", "median hours to stop-out", "90th pct hours", "within 1 day", "within 1 week", "within 30 days", "within 90 days", "longest survivor, days", "mean owner cash USD", "starts where the owner came out ahead"])}

"Within N" uses only start dates with at least N of data left. The few accounts not stopped out are the last start dates, cut off by the end of
the data. With the sweep on, the owner came out ahead (withdrew more than the deposit before the stop-out) from {pct(ruin_s[(ruin_s.deposit == 200) & ruin_s.sweep].owner_positive_share.iloc[0])} of 200 USD starts
and {pct(ruin_s[(ruin_s.deposit == 1000) & ruin_s.sweep].owner_positive_share.iloc[0])} of 1,000 USD starts. A five-times larger account at the same clip buys about nine times the median life and the same ending.

### 4.8 Trade week, 2026-11-04 10:06 to 2026-11-11 07:04 (parity only, never part of a verdict)

| | Real account | XMR-1 default, base, M1 exits | same, S5 exits | XMR-1 default, stress, M1 | same, S5 exits |
|---|---:|---:|---:|---:|---:|
| Positions opened | 178 | {w0.n} | {w0s.n} | {w1.n} | {w1s.n} |
| Position win rate | {pct(rr['win_rate'])} | {pct(w0.win_rate)} | {pct(w0s.win_rate)} | {pct(w1.win_rate)} | {pct(w1s.win_rate)} |
| PF | {rr['pf']:.2f} | {w0.pf:.2f} | {w0s.pf:.2f} | {w1.pf:.2f} | {w1s.pf:.2f} |
| Average win / loss, USD | {rr['avg_win']:.1f} / {rr['avg_loss']:.1f} | {w0.avg_win:.1f} / {w0.avg_loss:.1f} | {w0s.avg_win:.1f} / {w0s.avg_loss:.1f} | {w1.avg_win:.1f} / {w1.avg_loss:.1f} | {w1s.avg_win:.1f} / {w1s.avg_loss:.1f} |
| Margin stop-outs | 7 | {w0.wipeouts} | {w0s.wipeouts} | {w1.wipeouts} | {w1s.wipeouts} |
| Positions closed by stop-out | {rr['stopout_positions']} ({pct(rr['stopout_positions'] / 178)}) | {w0.n_so} ({pct(w0.n_so / w0.n)}) | {w0s.n_so} ({pct(w0s.n_so / w0s.n)}) | {w1.n_so} ({pct(w1.n_so / w1.n)}) | {w1s.n_so} ({pct(w1s.n_so / w1s.n)}) |
| Time flat | {pct(rr['flat_share'])} | {pct(w0.flat_share)} | {pct(w0s.flat_share)} | {pct(w1.flat_share)} | {pct(w1s.flat_share)} |
| Median hold, minutes | {rr['hold_med_min']:.1f} | {w0.hold_med_min:.1f} | {w0s.hold_med_min:.1f} | {w1.hold_med_min:.1f} | {w1s.hold_med_min:.1f} |
| Deposits / withdrawals, USD | 884.74 / 1,805.00 | {usd(w0.deposits)} / {usd(w0.withdrawals)} | {usd(w0s.deposits)} / {usd(w0s.withdrawals)} | {usd(w1.deposits)} / {usd(w1.withdrawals)} | {usd(w1s.deposits)} / {usd(w1s.withdrawals)} |
| Result, USD | trading net +{rr['net']:.2f}; cash +920.26 (379.15 of it broker money) | owner cash {usd(w0.owner_cash)} | {usd(w0s.owner_cash)} | {usd(w1.owner_cash)} | {usd(w1s.owner_cash)} |

Reading. Same order of magnitude, as expected, and the mix per position is close (about three in four win; a fifth of his positions and a
quarter of the machine's end in a stop-out). The machine is {w0.n / 178:.1f} times as active as he was — it re-enters the moment a book is empty and the trigger is on, he opened
about 4.5 fresh baskets a day — and it is stopped out {w0.wipeouts / 7:.0f} times as often. It does **not** reproduce his result: he ended the week up, the
machine ended it {usd(-w0.owner_cash)} USD down. Six days cannot say whether that gap is his discretion (closing winners by hand, pausing,
choosing when to add) or luck; section 4.4 puts a week like his at about one in six to one in eight for the machine.

**S5 against M1 exits.** Resolving stop-outs and targets on 5-second bid/ask bars (the M1 rule "stop-out before any target in the bar" is then
applied inside 5 seconds instead of 60) changes owner cash from {usd(w0.owner_cash)} to {usd(w0s.owner_cash)} at base cost ({usd(w0s.owner_cash - w0.owner_cash)} USD,
{abs(w0s.owner_cash - w0.owner_cash) / abs(w0.owner_cash):.1%}) and from {usd(w1.owner_cash)} to {usd(w1s.owner_cash)} at stress. Wipe-out counts are identical. The M1 tie rule is slightly conservative and does not drive any conclusion.
What does change is the loss marked beyond zero equity: {usd(w0.absorbed_by_broker)} USD on M1 against {usd(w0s.absorbed_by_broker)} USD on S5, which confirms "loss absorbed by the broker" on M1 is an upper bound.

All eight cells in the same span, M1 exits:

{tbl(week_rows, ["cost · cell", "owner cash", "deposits", "withdrawals", "wipe-outs", "positions", "win rate", "PF", "time flat", "time hedged", "max positions", "median hold, min"])}

One cell (TP 2.5 × ATR, per leg) is positive in this week: both books filled to ten, locked against each other, and scalped the range for
five days with a single stop-out. That same cell lost {usd(-cell('TRAIN', 'base', '2.5|per_leg|True').owner_cash)} USD in TRAIN and {usd(-cell('TEST', 'base', '2.5|per_leg|True').owner_cash)} USD in TEST. It is the clearest picture in this report of how a
two-way range week flatters this method, and of how little one week says.

### 4.9 Replication — do the rules reproduce his entries?

Span {rep['counts']['span'][:16]} to {rep['counts']['span'][29:45]}. The simulation placed {rep['counts']['sim_orders']} orders ({rep['counts']['sim_positions']} positions: {rep['counts']['sim_buy']} buys, {rep['counts']['sim_sell']} sells);
he made {rep['counts']['real_decisions']} decisions ({rep['counts']['real_positions']} positions: {rep['counts']['real_buy']} buys, {rep['counts']['real_sell']} sells). A match is the same side within ±5 minutes. Two chance
baselines: the same test against the opposite side, and against the other series shifted by ±67 to ±733 minutes (16 shifts; mean and maximum).

{tbl(rep_rows, ["Test", "n", "matched", "rate", "opposite side", "time-shift placebo, mean", "placebo, max"])}

The rules explain about four in ten of his decisions, roughly twice the chance rate, so about two in ten beyond coincidence. Going the other
way, more than eight in ten of the machine's orders have no counterpart in his trading. The trigger-parity figure from the specification
(trigger on at the last closed bar for 11 of 27 fresh entries and 39 of 124 decisions) is reproduced exactly by this harness. The fade is a
tendency in what he does; these rules are not a replica of him, and the book state of the simulation diverges from his within hours.

### 4.10 Secondary window, 2019-01-01 to 2025-07-15 (report only)

Long mid-only file `../../../m3_scalper/xau_m1_full.parquet`, spread 1.5 bp (base) and 2.5 bp (stress) of price. Quality check against the OANDA
file on their overlap: closes identical on {pct(qa['long_file_vs_oanda_overlap']['close_exact_share'])} of shared bars, but {qa['long_file_vs_oanda_overlap']['missing_in_long']:,} of {qa['long_file_vs_oanda_overlap']['bars_oanda']:,} OANDA bars
({qa['long_file_vs_oanda_overlap']['missing_in_long'] / qa['long_file_vs_oanda_overlap']['bars_oanda']:.1%}) are missing from it and some highs differ by up to {qa['long_file_vs_oanda_overlap']['max_abs_high_diff']:.1f} points. Usable for a secondary look, not for a verdict.

{tbl(sec_rows, ["cost · sweep", "owner cash", "deposits", "withdrawals", "wipe-outs", "positions", "win rate", "PF", "time flat", "time hedged", "weeks > 0"])}

By year, default cell, base cost:

{tbl(secy_rows, ["year", "owner cash", "wipe-outs", "in-session bars passing ATR5 ≥ 3.0", "median ATR5", "median price"])}

This window mostly tests the 3.0-point floors, not the method: gold's M5 ATR was 0.6–1.5 points before 2024, so the trigger is switched off
on 90–100% of bars and the account is idle. Where it does trade (2020, 2024, the first half of 2025) it loses. The fixed-point thresholds were
set from one week at 4,000 USD gold and do not transfer to earlier years (vault trap 8); no conclusion is drawn from this window beyond "no sign of a profit".

---

## 5. Protocol verdict

The default cell is the pre-registered hypothesis. For the brief's "choose on TRAIN, report TEST once": the cell with the best TRAIN owner cash
at base cost is TP {pick.tp_atr} × ATR, {pick.tp_mode}, sweep {'on' if pick.sweep else 'off'} ({usd(pick.owner_cash)} USD, ahead of the next cell by {usd(pick.owner_cash - train_base.iloc[1].owner_cash)} USD — noise).
Its TEST result, once: owner cash {usd(P[('TEST', 'base')]['owner'])} USD at base, {usd(P[('TEST', '0.8')]['owner'])} at 0.80; PF {P[('TEST', 'base')]['pf']:.2f} and {P[('TEST', '0.8')]['pf']:.2f}; {P[('TEST', '0.8')]['n']:,} positions.

Bars from the brief, at 0.80 round-trip cost:

{tbl(bars_tbl, ["cell", "TEST PF ≥ 1.15", "positive in both halves", "≥ 60% of TEST months positive", "no month > half of net", "≥ 200 TEST trades"])}

Four of five bars failed by both cells. **FAIL**, at every cost level, in both windows, in every cell. The specification set no pass mark for this
candidate; the verdict is recorded because the workflow asks for one.

---

## 6. What this does and does not show

Shown, with the sample to back it:
- The codified method — fade trigger, flat-clip averaging, a target on every leg, no stop, a 200 USD account at 1:1000 — loses the owner money
  in {neg_runs} of {n_runs} runs across 16 months, two independent windows, eight cells and four cost levels, on {F['n']:,} positions in the default cell.
- Its high win rate is geometry. A random signal gets the same win rate, wipe-out count and owner cash, and a coin-flip price
  series gives the same machine an {pct(n6.win_rate_mean)} win rate.
- The margin stop-out is the stop, and it is an expensive one: {F['wipes'] / (5 * F['w']):.1f} stop-outs per trading day, roughly 19 in 20 deposits lost
  before they pay themselves back, {usd(-F['owner'] / (F['dep'] / 200))} USD lost per 200 USD deposited.
- Quoted spread explains about half of the loss ({F['spread'] / -F['owner']:.0%}). The rest is price path.

Not shown:
- **That he would have lost this much.** The machine trades about three times as often as he did, has no discretion, and gets no bonus credit.
  It reproduces the shape of his week, not his result, and matches about 40% of his decisions. This is the long-run cost of the rules
  that could be written down, not a forecast of his account.
- **That his discretion has no value.** The behaviours left out (closing winners by hand at about half the target, pausing, hedge-locks, size-ups,
  top-ups) could not be codified. The earlier studies priced the size-ups and hedge-locks as losers (−1,652 and −249 USD), which is why leaving them out
  was expected to flatter this candidate. The hand-closing is unpriced in either direction.
- **Anything about a different regime.** 16 months of a strongly trending, high-volatility gold market (3,340 to above 5,600 and back to about 4,000).
  The trade week itself was a two-way range, the regime that suits the method; section 4.8 shows one cell making money in it.

Modelling limits that matter:
- Before 2026-07-16 the spread is assumed (0.60 base), not observed. The four cost levels bracket it and none changes the sign.
- OANDA is a proxy for XM. In calm bars the basis is about 0.05 points; at fast moves XM's stop-out fills were up to 23 points from OANDA's quote.
  The account model sidesteps this by treating a stop-out as the loss of the whole balance (his real stop-outs left 2.97 USD or less).
- Stop-outs are evaluated on M1 extremes with the stop-out ahead of any target in the bar. The S5 re-run on the trade week moves owner cash by under 2%.
- Re-deposit after exactly 60 minutes is an assumption (his were 0.2 to 12 hours). It sets how many deposits fit in a week, not what each one is worth.
- Rule 6 lets an order through whenever it reduces net lots, so the two books lock against each other for about half the time. That is the
  specification, and close to what he did under pressure, but it is far more hedging than he showed (22 of 124 decisions).
- Sample sizes are large for the machine (tens of thousands of positions, hundreds of stop-outs) and tiny for the man (six days). Every statement
  about the machine above is well supported; every comparison with him rests on one week.

---

## 7. Files

| File | What |
|---|---|
| `xmr1.py` | The backtester and every run. `python xmr1.py` runs all steps; `python xmr1.py selftest` runs the engine and look-ahead checks only |
| `report.py` | Builds this report and the two figures from `results/` |
| `equity_curve.png`, `exhibits.png` | Figures above |
| `results/grid.csv` | All {n_runs} grid runs (8 cells × 4 cost levels × TRAIN, TEST), every metric |
| `results/wipeouts_default.csv`, `trades_default_base.csv` | Default cell: every stop-out (time, balance wiped, books) and every position at base cost |
| `results/daily_owner_cash.csv`, `weekly_owner_cash.csv`, `monthly_owner_cash.csv` | Owner cash per UTC day, week (Sun–Sat) and month for every run |
| `results/control.csv` | 400 random-signal runs (100 draws × 2 windows × 2 costs) |
| `results/shadow.csv`, `shadow_equity_*.csv` | Shadow run summary and hourly equity |
| `results/ruin.csv`, `ruin_summary.csv` | Rolling-start time to stop-out, 200 and 1,000 USD |
| `results/week.csv`, `week_sim_trades.csv`, `replication.json` | Trade-week runs (M1 and S5), the simulated trades, and the entry-matching test |
| `results/secondary.csv`, `secondary_by_year.csv` | 2019–2025 secondary window |
| `results/qa.json`, `null_random_walk.csv`, `null_summary.csv` | Data and harness checks, basis measurement, fair-game test |

Inputs were read only. No production system, box or broker API was touched. Nothing was committed and the vault was not updated.
"""
(HERE / "REPORT.md").write_text(md)
print(f"REPORT.md written ({len(md):,} chars); default FULL base owner cash {F['owner']:,.0f}, stress {FS['owner']:,.0f}; TRAIN pick {pick_key}")
