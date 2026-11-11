"""Step 6 - markdown-formatted result tables (no prose), generated from trade_excursions.csv and results/*.csv
so that whoever writes the study up can paste them without retyping numbers.
Run: python 06_tables.py   (after 01..03)  -> results/06_tables.txt
"""
import numpy as np
import pandas as pd

from common import HERE, RES

x = pd.read_csv(HERE / "trade_excursions.csv")
grid = pd.read_csv(RES / "cf_grid.csv")
allr = pd.read_csv(RES / "cf_all.csv")
drift = pd.read_csv(RES / "cf_drift.csv")
byday = pd.read_csv(RES / "cf_by_day.csv", index_col=0)
byday_de = pd.read_csv(RES / "cf_by_day_de.csv", index_col=0)


def md(df, fmt=None):
    """DataFrame -> markdown table. fmt: {column: format string}; default ints plain, floats 1 decimal."""
    fmt = fmt or {}

    def cell(c, v):
        if isinstance(v, str):
            return v
        if v != v:
            return ""
        if c in fmt:
            return fmt[c].format(v)
        return f"{int(v):,}" if float(v).is_integer() else f"{v:,.1f}"

    def clean(c, v):
        out = cell(c, v)
        return "0" if out in ("-0", "+0") else out
    num = [pd.api.types.is_numeric_dtype(df[c]) for c in df.columns]
    out = ["| " + " | ".join(str(c) for c in df.columns) + " |", "|" + "|".join("---:" if n else "---" for n in num) + "|"]
    out += ["| " + " | ".join(clean(c, v) for c, v in zip(df.columns, r)) + " |" for r in df.itertuples(index=False)]
    return "\n".join(out)


S = "{:+,.0f}"
x["kind"] = np.where(x.closeby, "Hedge lock, netted off (close-by)", x.reason.map({"MOBILE": "Closed by hand", "TP": "Take-profit hit", "SO": "Margin stop-out"}))
x["outcome"] = np.where(x.pts_real > 0, "Winners", np.where(x.pts_real < 0, "Losers", "flat"))

# T1 how positions ended
g = x.groupby("kind").agg(Positions=("pts_real", "size"), Win=("pts_real", lambda s: 100 * (s > 0).mean()), Points=("pts_real", "sum"),
                          USD_real=("usd_actual", "sum"), USD_flat=("usd_flat004", "sum"), Hold=("hold_s", lambda s: s.median() / 60),
                          MFE=("mfe_pts", "median"), MAE=("mae_pts", "median")).reset_index()
g = g.set_index("kind").loc[["Closed by hand", "Take-profit hit", "Margin stop-out", "Hedge lock, netted off (close-by)"]].reset_index()
tot = pd.DataFrame([dict(kind="**All**", Positions=len(x), Win=100 * (x.pts_real > 0).mean(), Points=x.pts_real.sum(), USD_real=x.usd_actual.sum(),
                         USD_flat=x.usd_flat004.sum(), Hold=x.hold_s.median() / 60, MFE=x.mfe_pts.median(), MAE=x.mae_pts.median())])
g = pd.concat([g, tot])
g.columns = ["How it ended", "Positions", "Win %", "Points", "USD, real lots", "USD at 0.04", "Median hold (min)", "Median MFE", "Median MAE"]
T1 = md(g, {"Points": "{:+,.1f}", "USD, real lots": S, "USD at 0.04": S, "Win %": "{:.1f}"})

# T2 excursions by outcome
rows = []
for o in ("Winners", "Losers"):
    s = x[x.outcome == o]
    q = lambda c, p: s[c].quantile(p)
    rows.append({"": o, "n": len(s), "MFE median": q("mfe_pts", .5), "MFE 25-75%": f"{q('mfe_pts', .25):.1f} to {q('mfe_pts', .75):.1f}",
                 "MAE median": q("mae_pts", .5), "MAE 25-75%": f"{q('mae_pts', .25):.1f} to {q('mae_pts', .75):.1f}", "MAE 5th pct": q("mae_pts", .05),
                 "MAE worst": s.mae_pts.min(), "Median min to MFE": q("t_mfe_s", .5) / 60, "Median min to MAE": q("t_mae_s", .5) / 60,
                 "Median hold (min)": q("hold_s", .5) / 60, "Mean hold (min)": s.hold_s.mean() / 60})
T2 = md(pd.DataFrame(rows))

# T3 take-profit distance
tp = x[x.tp.notna()]
h = pd.cut(tp.tp_dist, [0, 4.5, 5.6, 9, 12, 13.5, 14.6, 22, 50]).value_counts().sort_index()
T3 = md(pd.DataFrame({"TP distance (points)": [f"{i.left:g} to {i.right:g}" for i in h.index], "Positions": h.values,
                      "Share %": 100 * h.values / len(tp)}), {"Share %": "{:.0f}"})

# T5 adds / hedges / fresh (economic points: a close-by pair's loss sits on the leg opened first)
x["grp"] = np.where(x.add_to_loser, "Add to a loser", np.where(x.hedge_vs_loser, "Hedge against a loser", "Fresh entry"))
g = x.groupby("grp").agg(Positions=("pts_econ", "size"), Decisions=("burst_id", "nunique"), Win=("pts_econ", lambda s: 100 * (s > 0).mean()),
                         Points=("pts_econ", "sum"), USD=("usd_actual", "sum"), SO=("reason", lambda s: (s == "SO").sum()), MAE=("mae_pts", "median"),
                         Worst=("pts_econ", "min")).loc[["Fresh entry", "Add to a loser", "Hedge against a loser"]].reset_index()
g.columns = ["Entry type", "Positions", "Decisions", "Win %", "Points", "USD, real lots", "Ended in stop-out", "Median MAE", "Worst position"]
T5 = md(g, {"Points": "{:+,.1f}", "USD, real lots": S, "Win %": "{:.1f}"})

# T6 drift after entry
d = drift[drift.subset == "ALL"]
d2 = drift[drift.subset == "FRESH"].set_index("T_min")
T6 = md(pd.DataFrame({"Closed after": [f"{t} min" if t < 60 else f"{t // 60} h" for t in d.T_min], "In profit %": d.in_profit_pct.values,
                      "Mean per decision": d.burst_mean.values, "Std error": d.burst_se.values, "t vs -0.60": d.t_vs_minus_spread.values,
                      "Total, 178 positions": (d.mean_pts * d.n).values, "Fresh only: mean per decision": d2.burst_mean.reindex(d.T_min).values,
                      "Fresh: std error": d2.burst_se.reindex(d.T_min).values}),
        {"Mean per decision": "{:+.2f}", "Std error": "{:.2f}", "t vs -0.60": "{:+.2f}", "Total, 178 positions": S, "Fresh only: mean per decision": "{:+.2f}", "Fresh: std error": "{:.2f}"})


def matrix(sub, col="total_pts", f=S):
    p = grid[grid.subset == sub].pivot(index="tp", columns="sl", values=col)
    p.columns = [f"SL {c:g}" for c in p.columns]
    p = p.reset_index().rename(columns={"tp": "TP"})
    p["TP"] = p.TP.map(lambda v: f"**{v:g}**")
    return md(p, {c: f for c in p.columns if c != "TP"})


T7, T8, T8b, T10 = matrix("ALL"), matrix("EX_ADDS"), matrix("FRESH"), matrix("ALL", "real_pctile_vs_same", "{:.0f}")

# T9 representative cells, full metrics
rows = []
for tpv, slv in ((3, 30), (4, 25), (5, 10), (5, 20), (10, 10), (10, 20), (15, 15), (15, 30)):
    for sub, lab in (("ALL", "all 178"), ("EX_ADDS", "no adds, 107")):
        r = grid[(grid.subset == sub) & (grid.tp == tpv) & (grid.sl == slv)].iloc[0]
        rows.append({"TP / SL": f"{tpv} / {slv}", "Entries": lab, "Points": r.total_pts, "USD at 0.04": r.usd_004, "Win %": r.win_pct, "PF": r.pf,
                     "Worst trade": r.worst_trade, "Worst floating USD": r.min_float_usd, "Max drawdown USD": r.max_dd_usd, "Open at end": r.n_open,
                     "Random-time control": f"{r.ctrl_same_mean:+.0f} ± {r.ctrl_same_sd:.0f}", "Percentile": r.real_pctile_vs_same, "Faded": r.flip_real_pts})
T9 = md(pd.DataFrame(rows), {"Points": S, "USD at 0.04": S, "Win %": "{:.1f}", "PF": "{:.2f}", "Worst trade": "{:.1f}", "Worst floating USD": S,
                             "Max drawdown USD": "{:,.0f}", "Percentile": "{:.0f}", "Faded": S, "Open at end": "{:.0f}"})

# T11 time stop
fam = lambda f, sub="ALL": allr[(allr.family == f) & (allr.subset == sub)]
a, b, c, e = fam("b_time_only").set_index("tmax_min"), fam("b_actualTP_time").set_index("tmax_min"), fam("b_TP5_time").set_index("tmax_min"), fam("b_time_only", "EX_ADDS").set_index("tmax_min")
T11 = md(pd.DataFrame({"Time stop": [f"{int(t)} min" if t < 60 else f"{int(t) // 60} h" for t in a.index], "Points": a.total_pts.values, "USD at 0.04": a.usd_004.values,
                       "Win %": a.win_pct.values, "PF": a.pf.values, "Worst trade": a.worst_trade.values, "Max drawdown USD": a.max_dd_usd.values,
                       "No adds: points": e.total_pts.values, "With his own TP: points": b.total_pts.values, "his TP: win %": b.win_pct.values,
                       "With TP 5: points": c.total_pts.values, "TP 5: win %": c.win_pct.values}),
         {"Points": S, "USD at 0.04": S, "Win %": "{:.1f}", "PF": "{:.2f}", "Worst trade": "{:.1f}", "Max drawdown USD": "{:,.0f}", "No adds: points": S,
          "With his own TP: points": S, "his TP: win %": "{:.1f}", "With TP 5: points": S, "TP 5: win %": "{:.1f}"})

# T12 break-even
rows = []
for f, lab in (("c_actualTP_noSL", "His TP, no stop"), ("c_actualTP_SL15", "His TP, SL 15"), ("c_TP5_SL15", "TP 5, SL 15"), ("c_TP10_SL15", "TP 10, SL 15"), ("c_TP15_SL30", "TP 15, SL 30")):
    for sub, sl in (("ALL", "all 178"), ("EX_ADDS", "no adds, 107")):
        r = fam(f, sub).set_index("be")
        rows.append({"Base exit": lab, "Entries": sl, **{("no BE" if k == 0 else f"BE at +{k:g}"): r.total_pts[k] for k in (0.0, 1.0, 2.0, 3.0, 5.0, 8.0)},
                     "Win % at +3": r.win_pct[3.0], "Worst trade at +3": r.worst_trade[3.0], "Max DD USD at +3": r.max_dd_usd[3.0]})
T12 = md(pd.DataFrame(rows), {**{k: S for k in ("no BE", "BE at +1", "BE at +2", "BE at +3", "BE at +5", "BE at +8")}, "Win % at +3": "{:.1f}",
                              "Worst trade at +3": "{:.1f}", "Max DD USD at +3": "{:,.0f}"})


def sl_table(f, extra=None):
    a, e, fr = fam(f).sort_values("sl"), fam(f, "EX_ADDS").sort_values("sl"), fam(f, "FRESH").sort_values("sl")
    t = pd.DataFrame({"Hard stop": ["none" if np.isinf(v) else f"{v:g}" for v in a.sl], "Stopped": a.n_stop.values, "Points": a.total_pts.values, "USD at 0.04": a.usd_004.values})
    if extra:
        t["USD, real lots"] = a[extra].values
    t = t.assign(**{"Win %": a.win_pct.values, "PF": a.pf.values, "Worst trade": a.worst_trade.values, "Worst floating USD": a.min_float_usd.values,
                    "Max drawdown USD": a.max_dd_usd.values, "Open at end": a.n_open.values, "No adds: points": e.total_pts.values, "Fresh: points": fr.total_pts.values})
    return md(t, {"Points": S, "USD at 0.04": S, "USD, real lots": S, "Win %": "{:.1f}", "PF": "{:.2f}", "Worst trade": "{:.1f}", "Worst floating USD": S,
                  "Max drawdown USD": "{:,.0f}", "No adds: points": S, "Fresh: points": S})


T13, T14 = sl_table("d_actualTP_SL_tpset141"), sl_table("e_actual_exits_plus_SL", "usd_real_lots")
bd = pd.concat([byday_de.loc[["actual (n=178)"]], byday.loc[["TP4/SL25", "TP5/SL10", "TP10/SL20", "TP15/SL30"]], byday_de.loc[["(e) real exits + SL 10", "(e) real exits + SL 25",
               "(d) own TP, SL 20.0 (n=141)", "(d) own TP, SL none (n=141)"]]])
bd.index = ["His real exits", "(a) TP 4 / SL 25", "(a) TP 5 / SL 10", "(a) TP 10 / SL 20", "(a) TP 15 / SL 30", "(e) real exits + SL 10", "(e) real exits + SL 25",
            "(d) his TP + SL 20 (141 positions)", "(d) his TP, no stop (141 positions)"]
bd.columns = [f"Nov {c[-2:].lstrip('0')}" for c in bd.columns]
bd["Week"] = bd.sum(axis=1)
T15 = md(bd.reset_index().rename(columns={"index": "Exit rule"}), {c: S for c in bd.columns})

TITLES = dict(
    T1="How positions ended (points = broker-booked, each close-by pair once)", T2="MFE / MAE by outcome (points, exit-side quote)",
    T3="Take-profit distance set (141 positions with a TP)", T5="Entry type (points with a close-by pair's loss on the leg opened first)",
    T6="Drift after entry: every position closed T minutes later, no TP/SL (spread paid at entry averages 0.60)",
    T7="(a) TP x SL grid, total points, all 178 entries (real exits +402)", T8="(a) TP x SL grid, total points, without the 71 adds to a loser (107 entries; real exits +155)",
    T8b="(a) TP x SL grid, total points, fresh entries only (59 entries; real exits +229)", T9="(a) representative cells, full measures (control = same side, random bar within +-60 min, 200 draws; faded = opposite side at the same instant)",
    T10="(a) percentile of the real entries inside the random-time control, all 178 (50 = same as random timing)",
    T11="(b) time stop: alone, with his own TP, with TP 5", T12="(c) break-even after +X on five base exits (his TP = median 12.3 imputed where he set none)",
    T13="(d) his own TP + hard stop, the 141 positions with a TP (real exits on these: +410 all, +179 no adds, +238 fresh)",
    T14="(e) his real exits with a hard stop laid over them (real: +402 points, +$494 at real lots)", T15="Points by entry day")
TABLES = dict(T1=T1, T2=T2, T3=T3, T5=T5, T6=T6, T7=T7, T8=T8, T8b=T8b, T9=T9, T10=T10, T11=T11, T12=T12, T13=T13, T14=T14, T15=T15)
(RES / "06_tables.txt").write_text("\n\n".join(f"## {TITLES[k]}\n\n{v}" for k, v in TABLES.items()) + "\n")
print("wrote results/06_tables.txt")
