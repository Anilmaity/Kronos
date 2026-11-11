"""XM Real - trades on the gold candle chart, with account value and net open lots underneath.

Run:  ../../../.venv/bin/python 03_chart.py     (after 01_basis.py and 02_equity.py)
Writes xm_real_trades_equity.html (interactive), xm_real_week_overview.png, xm_real_day_<date>.png (6).

Conventions
- Time axis is IST (UTC+5:30); every hover also carries UTC. Closed-market gaps are cut out with rangebreaks.
- Candles: OANDA XAU_USD M1 *mid*, shifted by the measured XM-OANDA mid basis (basis.json), resampled with
  label=left (bar START) and drawn at the bar's CENTRE so a deal at 10:19 sits on the 10:15-10:20 candle.
- Markers are the broker's own deal prices and timestamps - nothing about them is modelled.
- A close-by pair (position A closed against opposite position B) is drawn as ONE round trip: A's entry to
  B's entry, which is the real market fill that locked the result. The broker's close-by "price" is not a
  market price (it is the other leg's open price) and would sit up to 10 USD off the candles.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IST = pd.Timedelta(hours=5, minutes=30)
BG, UP, INK = "#DBDBDB", "#089981", "#000000"  # house style (db_utils.format_chart)
# win / manual loss / stop-out. Checked with dataviz validate_palette.js against #DBDBDB together with the
# candle green, --pairs all: lightness, chroma, CVD separation and normal-vision floor all PASS.
COL = dict(win="#1E66D0", loss="#D9480F", so="#B5179E")
CLS_NAME = dict(win="Profit", loss="Loss (manual / close-by)", so="STOP-OUT (margin)")
TFS = {"1m": 1, "5m": 5, "15m": 15}
ENTRY_SYM = {"BUY": "triangle-up", "SELL": "triangle-down"}
EXIT_SYM = {"manual": "circle", "TP": "diamond", "STOP-OUT": "x", "close-by": "square"}

ist = lambda ts: (ts + IST).tz_localize(None)  # one Timestamp
ist_s = lambda s: (s + IST).dt.tz_localize(None)  # a Series
iso = lambda s: [x.isoformat() for x in s]
money = lambda v: f"{'+' if v >= 0 else '−'}${abs(v):,.2f}"
stamp = lambda ts: f"{ist(ts):%d %b %H:%M:%S} IST · {ts:%d %b %H:%M:%S} UTC"


def hold_str(sec):
    h, r = divmod(int(sec), 3600)
    m, s = divmod(r, 60)
    return (f"{h}h " if h else "") + f"{m}m {s:02d}s"


# ------------------------------------------------------------------ data
basis = json.loads((HERE / "basis.json").read_text())
m1 = pd.read_parquet(ROOT / "xau_m1_2026-07-16_now_mba.parquet", columns=["time", "open", "high", "low", "close"])
m1 = m1[m1.time >= "2026-11-03 23:00"].set_index("time") + basis["mid_basis"]
DATA_END = m1.index[-1] + pd.Timedelta(minutes=1)


def candles(n):
    c = m1 if n == 1 else m1.resample(f"{n}min", label="left", closed="left").agg(
        dict(open="first", high="max", low="min", close="last")).dropna()
    return c.reset_index()


CANDLES = {k: candles(n) for k, n in TFS.items()}

# closed-market gaps, straight from the M1 data (22:00-23:00 UTC daily, Fri 22:00 - Sun 23:00)
_gap = m1.index.to_series().diff()
BREAKS, BREAK_TS = [], []
for end, g in _gap[_gap > pd.Timedelta(minutes=5)].items():
    lo, hi = (end - g + pd.Timedelta(minutes=1)).ceil("15min"), end.floor("15min")
    BREAKS.append(dict(bounds=[ist(lo).isoformat(), ist(hi).isoformat()]))
    BREAK_TS.append((lo, hi))

d = pd.read_csv(ROOT / "deals.csv")
d["time"] = pd.to_datetime(d["time"], utc=True, format="ISO8601")
d = d.sort_values(["time", "id"]).reset_index(drop=True)
d["cash"] = d.profit + d.swap.fillna(0) + d.commission.fillna(0)
t = pd.read_csv(ROOT / "trades.csv")
for c in ("open_time", "close_time"):
    t[c] = pd.to_datetime(t[c], utc=True, format="ISO8601")

# ---- round trips (what gets drawn)
KIND = {"DEAL_REASON_MOBILE": "manual", "DEAL_REASON_TP": "TP", "DEAL_REASON_SO": "STOP-OUT"}
cb = t.exit_entry_type == "DEAL_ENTRY_OUT_BY"
rows = [dict(ids=str(p.position_id), side=p.side, vol=p.volume, x0=p.open_time, y0=p.entry, x1=p.close_time, y1=p.exit,
             net=p.net, kind=KIND[p.exit_reason], tp=p.tp, sl=p.sl, note="") for p in t[~cb].itertuples()]
for _, g in t[cb].groupby("comment"):
    a, b = g.sort_values("open_time").itertuples()  # a = original position, b = the later opposite hedge
    assert a.side != b.side and a.volume == b.volume
    rows.append(dict(ids=f"{a.position_id} + #{b.position_id}", side=a.side, vol=a.volume, x0=a.open_time, y0=a.entry,
                     x1=b.open_time, y1=b.entry, net=g.net.sum(), kind="close-by", tp=a.tp, sl=a.sl,
                     note=f"<br>hedged by the opposite position, pair booked {stamp(a.close_time)}"))
rt = pd.DataFrame(rows).sort_values("x0").reset_index(drop=True)
rt["sgn"] = rt.side.map({"BUY": 1, "SELL": -1})
rt["pts"] = (rt.y1 - rt.y0) * rt.sgn
_noswap = np.isclose(rt.pts * rt.vol * 100, rt.net, atol=0.02)  # the rest carry overnight swap; hover shows the broker's net
assert (~_noswap).sum() <= (t.swap != 0).sum(), "points and booked net disagree on more positions than have swap"
rt["cls"] = np.where(rt.kind == "STOP-OUT", "so", np.where(rt.net > 0, "win", "loss"))
lvl = lambda v: "none" if pd.isna(v) else f"{v:.2f}"
rt["text"] = [
    f"<b>{r.side} {r.vol:g} lots</b> · #{r.ids}<br>entry {r.y0:.2f} · {stamp(r.x0)}<br>exit {r.y1:.2f} · {stamp(r.x1)}"
    f"<br><b>{r.pts:+.2f} pts · net {money(r.net)}</b><br>hold {hold_str((r.x1 - r.x0).total_seconds())} · exit: <b>{r.kind}</b>{r.note}"
    f"<br>TP {lvl(r.tp)} · SL {lvl(r.sl)}" for r in rt.itertuples()]

# ---- stop-out clusters (labels)
so = rt[rt.cls == "so"].sort_values("x1")
so = so.assign(cl=(so.x1.diff() > pd.Timedelta(minutes=5)).cumsum())
SO_CL = so.groupby("cl").agg(x=("x1", "max"), y=("y1", "mean"), n=("net", "size"), net=("net", "sum"), sgn=("sgn", "sum")).reset_index(drop=True)

# ---- account series
eq = pd.read_parquet(HERE / "equity_5s.parquet")
eq = eq[eq.time >= d.time.iloc[0]].set_index("time")
EQ1 = eq.resample("1min", label="right", closed="right").agg(
    equity=("equity", "last"), equity_mt5=("equity_mt5", "last"), lo=("equity", "min"), hi=("equity", "max"),
    floating=("floating", "last"), net_lots=("net_lots", "last")).dropna().reset_index()
bal = d[(d.type != "DEAL_TYPE_CREDIT") & (d.cash != 0)].copy()
bal["balance"] = bal.cash.cumsum()
bal["what"] = np.where(bal.symbol.notna(), "close #" + bal.positionId.fillna(0).astype("int64").astype(str), bal.comment.fillna(""))
BAL = pd.concat([bal[["time", "balance", "cash", "what"]],
                 pd.DataFrame([dict(time=DATA_END, balance=bal.balance.iloc[-1], cash=0.0, what="end of data")])], ignore_index=True)
BAL["time"] = pd.to_datetime(BAL.time, utc=True)

ev = pd.concat([pd.DataFrame(dict(time=t.open_time, dl=np.where(t.side == "BUY", 1, -1) * t.volume)),
                pd.DataFrame(dict(time=t.close_time, dl=-np.where(t.side == "BUY", 1, -1) * t.volume))]).sort_values("time")
ev["lots"] = ev.dl.cumsum().round(2)
LOTS = pd.concat([ev[["time", "lots"]], pd.DataFrame([dict(time=DATA_END, lots=0.0)])], ignore_index=True)
LOTS["time"] = pd.to_datetime(LOTS.time, utc=True)

# ---- cash events: deposits, withdrawals, bonus credit used to cover a negative balance
cf = d[d.type == "DEAL_TYPE_BALANCE"].copy()
cm = cf.comment.fillna("")
cf["kind"] = np.select(
    [cm.str.contains("ERR"), cm.str.startswith("CD-") | cm.str.startswith("Transfer") | cm.str.startswith("EXP05"),
     cm.str.startswith("CW-"), cm.str.startswith("EXP06") | cm.str.startswith("EXP01")],
    ["reversed", "deposit", "withdrawal", "bonus"], "other")
assert not (cf.kind == "other").any(), cf[cf.kind == "other"]
assert abs(cf[cf.kind == "reversed"].profit.sum()) < 0.01  # failed withdrawal attempts net to zero - not drawn
cf = cf[cf.kind != "reversed"]
cf["cl"] = ((cf.time.diff() > pd.Timedelta(seconds=60)) | (cf.kind != cf.kind.shift())).cumsum()
CASH = cf.groupby("cl").agg(time=("time", "max"), kind=("kind", "first"), amt=("profit", "sum"),
                            what=("comment", lambda s: " + ".join(s))).reset_index(drop=True)
CASH["bal_after"] = [BAL.balance[BAL.time <= x].iloc[-1] for x in CASH.time]


# ------------------------------------------------------------------ figure
def step_window(df, col, a, b):
    """Values a step series takes inside [a, b], including the level it enters the window at."""
    inside = df[(df.time >= a) & (df.time <= b)][col]
    before = df[df.time < a][col]
    return pd.concat([before.iloc[-1:], inside])


def pad(lo, hi, f):
    span = max(hi - lo, 1e-9)
    return [lo - f * span, hi + f * span]


def spread_labels(times, span, default, tiers):
    """Per-point choice from `tiers` so labels of events closer than 2.5% of the window do not sit on each other."""
    out, tier, prev = [], 0, None
    for x in times:
        tier = (tier + 1) % len(tiers) if prev is not None and (x - prev) < 0.025 * span else 0
        if tier == 1 and out:
            out[-1] = tiers[0] if out[-1] == default else out[-1]
        out.append(default if tier == 0 else tiers[tier])
        prev = x
    return out


def cash_labels(c, span, prefix):
    """One label per run of same-kind cash events closer than 0.8% of the window: the run's total, on its last marker."""
    run = (c.time.diff() > 0.008 * span).cumsum()
    tot, n, last = c.amt.groupby(run).transform("sum"), c.amt.groupby(run).transform("size"), ~run.duplicated(keep="last")
    return [(prefix + f"{'+' if v >= 0 else '−'}${abs(v):,.0f}" + (f" ×{m}" if m > 1 else "")) if z else "" for v, m, z in zip(tot, n, last)]


def ticks(a, b, step_h, datefmt):
    """Explicit IST ticks for the static charts: every step_h hours, none inside a closed-market gap,
    the date written under the first tick of each IST day."""
    g = pd.date_range(ist(a).ceil(f"{step_h}h"), ist(b), freq=f"{step_h}h")
    g = [x for x in g if not any(ist(lo) < x < ist(hi) for lo, hi in BREAK_TS)]
    txt, seen = [], set()
    for x in g:
        txt.append(f"{x:%H:%M}" + ("" if x.date() in seen else f"<br>{x:{datefmt}}"))
        seen.add(x.date())
    return dict(tickmode="array", tickvals=[x.isoformat() for x in g], ticktext=txt)


def build(tfs, a, b, k, title, static, label_bonus, tick=None):
    """tfs: candle timeframes to include (first one visible). [a, b] UTC window. k: size scale.
    Legend counts are for round trips that exit / cash events that fall inside [a, b]."""
    span = b - a
    fig = go.Figure()
    for i, tf in enumerate(tfs):
        c = CANDLES[tf]
        half = pd.Timedelta(minutes=TFS[tf]) / 2
        fig.add_trace(go.Candlestick(
            x=iso(ist_s(c.time + half)), open=c.open, high=c.high, low=c.low, close=c.close, name=f"candles {tf}",
            visible=i == 0, showlegend=False, yaxis="y",
            increasing=dict(line=dict(color=INK, width=0.8 * k), fillcolor=UP),
            decreasing=dict(line=dict(color=INK, width=0.8 * k), fillcolor=INK),
            customdata=[f"{tf} bar from {ist(x):%d %b %H:%M} IST · {x:%d %b %H:%M} UTC" for x in c.time],
            hovertemplate="<b>%{customdata}</b><br>O %{open:.2f}  H %{high:.2f}  L %{low:.2f}  C %{close:.2f}<extra></extra>"))
    n_candle = len(tfs)

    for cls in ("win", "loss", "so"):
        r = rt[rt.cls == cls]
        w = (2.6 if cls == "so" else 1.3) * k
        xs = np.column_stack([iso(ist_s(r.x0)), iso(ist_s(r.x1)), [None] * len(r)]).ravel().tolist()
        ys = np.column_stack([r.y0, r.y1, [np.nan] * len(r)]).ravel().tolist()
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=COL[cls], width=w), opacity=0.9,
                                 name=f"{CLS_NAME[cls]} · {((r.x1 >= a) & (r.x1 <= b)).sum()}", legendgroup=cls, hoverinfo="skip", yaxis="y"))
        fig.add_trace(go.Scatter(
            x=iso(ist_s(r.x0)), y=r.y0, mode="markers", legendgroup=cls, showlegend=False, yaxis="y", name="entry",
            marker=dict(symbol=r.side.map(ENTRY_SYM), size=10 * k, color=COL[cls], line=dict(color=INK, width=0.7 * k)),
            text=r.text, hovertemplate="%{text}<extra>entry</extra>"))
        fig.add_trace(go.Scatter(
            x=iso(ist_s(r.x1)), y=r.y1, mode="markers", legendgroup=cls, showlegend=False, yaxis="y", name="exit",
            marker=dict(symbol=r.kind.map(EXIT_SYM), size=np.where(r.kind == "STOP-OUT", 12, 7.5) * k, color=COL[cls],
                        line=dict(color=INK, width=0.7 * k)),
            text=r.text, hovertemplate="%{text}<extra>exit</extra>"))
    for name, sym in [("buy entry", "triangle-up"), ("sell entry", "triangle-down"), ("manual exit", "circle"),
                      ("TP exit", "diamond"), ("stop-out exit", "x"), ("close-by hedge", "square")]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=name, yaxis="y", hoverinfo="skip",
                                 marker=dict(symbol=sym, size=9 * k, color="#7a7a7a", line=dict(color=INK, width=0.7 * k))))

    # account value
    fig.add_trace(go.Scatter(
        x=iso(ist_s(EQ1.time)), y=EQ1.equity_mt5, mode="lines", name="Equity incl. bonus credit (MT5 “Equity”)",
        line=dict(color="#5a5a5a", width=1.1 * k, dash="dot"), yaxis="y2", legend="legend2",
        customdata=[f"{x:%d %b %H:%M} UTC" for x in EQ1.time], hovertemplate="MT5 equity incl. bonus <b>$%{y:,.2f}</b><br>%{customdata}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=iso(ist_s(EQ1.time)), y=EQ1.equity, mode="lines", name="Equity = balance + floating P&L", line=dict(color=UP, width=2 * k),
        yaxis="y2", legend="legend2",
        customdata=np.column_stack([[f"{x:%d %b %H:%M} UTC" for x in EQ1.time], EQ1.floating, EQ1.lo, EQ1.hi, EQ1.net_lots]),
        hovertemplate="equity <b>$%{y:,.2f}</b> · floating $%{customdata[1]:,.2f}<br>within the minute: $%{customdata[2]:,.2f} … $%{customdata[3]:,.2f}"
                      "<br>net %{customdata[4]} lots · %{customdata[0]}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=iso(ist_s(BAL.time)), y=BAL.balance, mode="lines", name="Balance (realised)", line=dict(color=INK, width=1.6 * k, shape="hv"),
        yaxis="y2", legend="legend2",
        customdata=np.column_stack([[f"{x:%d %b %H:%M:%S} UTC" for x in BAL.time], BAL.cash, BAL.what]),
        hovertemplate="balance <b>$%{y:,.2f}</b><br>%{customdata[2]}: $%{customdata[1]:,.2f}<br>%{customdata[0]}<extra></extra>"))
    for kind, name, sym, fill, pos, size in [
            ("deposit", "Deposit", "triangle-up", "#FFFFFF", "top", 13),
            ("withdrawal", "Withdrawal", "triangle-down", INK, "bottom", 13),
            ("bonus", "Bonus credit absorbs a negative balance", "diamond", "#8a8a8a", "bottom", 9)]:
        c = CASH[CASH.kind == kind]
        cw = c[(c.time >= a) & (c.time <= b)]
        fig.add_trace(go.Scatter(
            x=iso(ist_s(c.time)), y=c.bal_after, mode="markers+text" if (kind != "bonus" or label_bonus) else "markers",
            name=f"{name} · {len(cw)}" + (f" · {money(cw.amt.sum())}" if len(cw) else ""), yaxis="y2", legend="legend2",
            text=cash_labels(c, span, "bonus " if kind == "bonus" else ""),
            textposition=spread_labels(list(c.time), 1.6 * span, f"{pos} center", [f"{pos} left", f"{pos} right"]),
            textfont=dict(size=11 * k, color=INK), cliponaxis=False,
            marker=dict(symbol=sym, size=size * k, color=fill, line=dict(color=INK, width=1.2 * k)),
            customdata=np.column_stack([[stamp(x) for x in c.time], c.amt, c.what]),
            hovertemplate=f"<b>{name}</b> $%{{customdata[1]:,.2f}}<br>%{{customdata[2]}}<br>%{{customdata[0]}}<br>balance after $%{{y:,.2f}}<extra></extra>"))

    fig.add_trace(go.Scatter(
        x=iso(ist_s(LOTS.time)), y=LOTS.lots, mode="lines", name="net open lots", line=dict(color="#333333", width=1.1 * k, shape="hv"),
        fill="tozeroy", fillcolor="rgba(0,0,0,0.28)", yaxis="y3", showlegend=False,
        customdata=[f"{x:%d %b %H:%M:%S} UTC" for x in LOTS.time], hovertemplate="net <b>%{y:+.2f} lots</b><br>%{customdata}<extra></extra>"))

    socl = SO_CL[(SO_CL.x >= a) & (SO_CL.x <= b)]
    ann = [dict(x=ist(c.x).isoformat(), y=c.y, xref="x", yref="y", text=f"<b>STOP-OUT ×{c.n}</b>  −${abs(c.net):,.0f}",
                showarrow=True, arrowcolor=COL["so"], arrowwidth=1.4 * k, arrowhead=2, ax=0, ay=(1 if c.sgn > 0 else -1) * off * k,
                font=dict(size=11.5 * k, color=INK), bgcolor="rgba(255,255,255,0.85)", bordercolor=COL["so"], borderwidth=1.2 * k, borderpad=3)
           for c, off in zip(socl.itertuples(), spread_labels(list(socl.x), 3 * span, 46, [46, 100, 154]))]

    ax = dict(showgrid=False, showline=True, linecolor=INK, linewidth=1, ticks="outside", tickcolor=INK, side="right",
              fixedrange=True, automargin=True)
    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=INK, size=12 * k, family="Arial, Helvetica, sans-serif"),
        # &#36; : kaleido typesets any text holding two "$" as LaTeX
        title=dict(text=title.replace("$", "&#36;"), x=0.008, xanchor="left", y=1.0, yanchor="top", pad=dict(t=20 * k), font=dict(size=15 * k)),
        margin=dict(l=18 * k, r=70 * k, t=96 * k, b=46 * k), hovermode="closest", dragmode="pan", annotations=ann,
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=INK, font=dict(color=INK, size=12 * k), align="left"), spikedistance=-1,
        legend=dict(orientation="h", x=0, y=1.004, yanchor="bottom", bgcolor="rgba(0,0,0,0)", font=dict(size=11.5 * k)),
        legend2=dict(orientation="h", x=0, y=0.452, yanchor="bottom", bgcolor="rgba(0,0,0,0)", font=dict(size=11.5 * k)),
        xaxis=dict(anchor="y3", rangebreaks=BREAKS, range=[ist(a).isoformat(), ist(b).isoformat()], showgrid=False, showline=True,
                   linecolor=INK, ticks="outside", tickcolor=INK, tickformat="%H:%M\n%a %d %b", tickangle=0, rangeslider=dict(visible=False),
                   **(tick or {}),
                   showspikes=True, spikemode="across", spikesnap="cursor", spikethickness=1, spikecolor="#555555", spikedash="solid",
                   title=dict(text="November 2026 · IST (UTC+5:30) · closed-market hours cut out", font=dict(size=11 * k), standoff=4)),
        yaxis=dict(domain=[0.49, 1.0], zeroline=False, tickformat=",.0f", title=dict(text="GOLD · USD/oz", font=dict(size=11 * k)), **ax),
        yaxis2=dict(domain=[0.17, 0.445], zeroline=True, zerolinecolor="#9a9a9a", zerolinewidth=1, tickprefix="$", tickformat=",.0f",
                    title=dict(text="Account · USD", font=dict(size=11 * k)), **ax),
        yaxis3=dict(domain=[0.0, 0.13], zeroline=True, zerolinecolor="#6a6a6a", zerolinewidth=1, tickformat="+.2f",
                    title=dict(text="Net lots (+long / −short)", font=dict(size=11 * k)), **ax),
    )
    if static:  # no JS in a PNG: fit each panel to the window here
        c = CANDLES[tfs[0]]
        cw = c[(c.time >= a) & (c.time <= b)]
        e = EQ1[(EQ1.time >= a) & (EQ1.time <= b)]
        bw, lw = step_window(BAL, "balance", a, b), step_window(LOTS, "lots", a, b)
        fig.update_layout(
            yaxis_range=pad(cw.low.min(), cw.high.max(), 0.04),
            yaxis2_range=pad(min(bw.min(), e.equity.min() if len(e) else 0), max(bw.max(), e.equity_mt5.max() if len(e) else 0), 0.14),
            yaxis3_range=pad(min(lw.min(), 0), max(lw.max(), 0), 0.15))
    return fig, n_candle


# y-axes are fixed for the mouse (wheel / drag move time only) and refit to the visible window by this script
AUTOFIT_JS = """
(function () {
  var gd = document.getElementById('{plot_id}'), cache = {}, busy = false;
  function ms(v) { return typeof v === 'number' ? v : new Date(String(v).replace(' ', 'T')).getTime(); }
  function fit() {
    var xr = gd._fullLayout.xaxis.range.map(ms), lim = {};
    gd._fullData.forEach(function (tr) {
      if (tr.visible !== true || !tr.x || tr.x.length < 2) return;
      var xs = cache[tr.index] || (cache[tr.index] = Array.prototype.map.call(tr.x, function (v) { return v == null ? NaN : ms(v); }));
      var cs = tr.type === 'candlestick', lo = cs ? tr.low : tr.y, hi = cs ? tr.high : tr.y;
      var L = lim[tr.yaxis] || (lim[tr.yaxis] = [Infinity, -Infinity]);
      var step = tr.line && tr.line.shape === 'hv', prev = null;
      for (var i = 0; i < xs.length; i++) {
        var x = xs[i];
        if (isNaN(x) || lo[i] == null || isNaN(lo[i])) continue;
        if (x < xr[0]) { if (step) prev = i; continue; }
        if (x > xr[1]) continue;
        if (lo[i] < L[0]) L[0] = lo[i];
        if (hi[i] > L[1]) L[1] = hi[i];
      }
      if (prev !== null) { if (lo[prev] < L[0]) L[0] = lo[prev]; if (hi[prev] > L[1]) L[1] = hi[prev]; }
    });
    var upd = {};
    Object.keys(lim).forEach(function (k) {
      var L = lim[k];
      if (!isFinite(L[0])) return;
      if (k === 'y3') { L[0] = Math.min(L[0], 0); L[1] = Math.max(L[1], 0); }
      var p = Math.max(L[1] - L[0], 1e-6) * (k === 'y' ? 0.04 : 0.14);
      upd['yaxis' + k.slice(1) + '.range'] = [L[0] - p, L[1] + p];
    });
    return upd;
  }
  function refit() {
    if (busy) return;
    busy = true;
    Plotly.relayout(gd, fit()).then(function () { busy = false; }, function () { busy = false; });
  }
  gd.on('plotly_relayout', function (e) {
    if (Object.keys(e || {}).some(function (k) { return k.indexOf('xaxis') === 0; })) refit();
  });
  gd.on('plotly_restyle', refit);
  gd.on('plotly_update', refit);
  refit();
})();
"""


def session_window(day):
    """Active part of the broker session that ends on `day` (opens 23:00 UTC the evening before)."""
    lo, hi = pd.Timestamp(day, tz="UTC") - pd.Timedelta(hours=1), pd.Timestamp(day, tz="UTC") + pd.Timedelta(hours=22)
    act = d.time[(d.time >= lo) & (d.time < hi)]
    m = pd.Timedelta(minutes=45)
    return max(act.min() - m, lo), min(act.max() + m, hi, DATA_END), lo, hi


def summary(a, b):
    c = t[(t.close_time >= a) & (t.close_time < b)]
    s = c[c.exit_reason == "DEAL_REASON_SO"]
    return (f"{len(c)} positions closed · net {money(c.net.sum())} · {(c.net > 0).sum()} winners / {(c.net <= 0).sum()} losers"
            f" · stop-outs {len(s)} ({money(s.net.sum())})")


if __name__ == "__main__":
    # ---- check: do the markers sit on the candles that are drawn?
    c1 = CANDLES["1m"].set_index("time")
    pts_ = pd.concat([rt[["x0", "y0"]].set_axis(["x", "y"], axis=1).assign(what="entry"),
                      rt[["x1", "y1", "kind"]].set_axis(["x", "y", "what"], axis=1)], ignore_index=True)
    bar = c1.reindex(pts_.x.dt.floor("1min"))
    assert bar.low.notna().all(), "a deal has no M1 candle"
    pts_["off"] = np.maximum(np.maximum(bar.low.values - pts_.y.values, pts_.y.values - bar.high.values), 0)
    print(f"[marker check] {len(pts_)} markers vs their own 1m candle (drawn = OANDA mid {basis['mid_basis']:+.4f}):")
    print(f"  inside the candle's high-low range: {(pts_.off == 0).sum()}   outside by <=0.35 (half a spread): {((pts_.off > 0) & (pts_.off <= 0.35)).sum()}"
          f"   outside by >0.35: {(pts_.off > 0.35).sum()}   worst {pts_.off.max():.2f}")
    print(pts_[pts_.off > 0.35].sort_values("off", ascending=False).to_string(index=False))
    hidden = sum(((d.time > lo) & (d.time < hi)).sum() for lo, hi in BREAK_TS)
    assert hidden == 0, f"{hidden} deals fall inside a cut-out market gap"
    print(f"[rangebreaks] {len(BREAK_TS)} closed-market gaps cut out; deals hidden inside them: {hidden}")
    print(f"[round trips] {len(rt)} drawn from {len(t)} positions (4 close-by pairs merged): "
          + ", ".join(f"{CLS_NAME[k]} {v}" for k, v in rt.cls.value_counts().items()) + f" · net {money(rt.net.sum())}")
    print("[cash events]\n" + CASH[["time", "kind", "amt", "bal_after", "what"]].to_string(index=False))

    week_a, week_b = m1.index[0], DATA_END
    head = "XM Real · GOLD (XAUUSD) · every trade on the candles, account value and net open lots below"
    sub = lambda s: f"<br><span style='font-size:78%'>{s}</span>"

    # ---- interactive HTML
    order = ["15m", "5m", "1m"]  # trace order; the first is the one shown on load (week view)
    fig, nc = build(order, week_a, week_b, 1.0, head + sub(
        f"04–11 Nov 2026 · {summary(week_a, week_b)} · times IST · wheel = zoom time, drag = pan, panels refit themselves"), False, False)
    days = sorted({x.date() for x in t.close_time} | {x.date() for x in t.open_time})
    tf_btn = ("1m", "5m", "15m")

    def goto(label, a, b, tf):  # a jump button also picks a candle size that suits the span, and keeps the 1m/5m/15m highlight in step
        return dict(label=label, method="update", args=[
            {"visible": [o == tf for o in order]},
            {"xaxis.range": [ist(a).isoformat(), ist(b).isoformat()], "updatemenus[0].active": tf_btn.index(tf)}, list(range(nc))])

    jump = [goto("Week", week_a, week_b, "15m")] + [goto(f"{day:%a %d}", *session_window(day)[:2], "5m") for day in days]
    tfb = [dict(label=tf, method="restyle", args=[{"visible": [o == tf for o in order]}, list(range(nc))]) for tf in tf_btn]
    btn = dict(type="buttons", direction="right", bgcolor="#EDEDED", bordercolor=INK, borderwidth=1, font=dict(size=11, color=INK),
               pad=dict(t=0, b=78), showactive=True, yanchor="bottom", y=1.0, xanchor="right")  # sits in the top margin
    fig.update_layout(updatemenus=[dict(buttons=tfb, active=2, x=1.0, **btn), dict(buttons=jump, active=0, x=0.905, **btn)],
                      margin=dict(t=118))
    html = fig.to_html(include_plotlyjs=True, full_html=True, div_id="xmchart", default_height="100vh", default_width="100%",
                       config=dict(scrollZoom=True, displaylogo=False, responsive=True, modeBarButtonsToRemove=["lasso2d", "select2d", "autoScale2d"]),
                       post_script=AUTOFIT_JS)
    html = html.replace("<head>", "<head><title>XM Real - trades vs account value</title><style>html,body{margin:0;height:100%;background:#DBDBDB}</style>", 1)
    (HERE / "xm_real_trades_equity.html").write_text(html, encoding="utf-8")
    print(f"wrote xm_real_trades_equity.html  {len(html) / 1e6:.1f} MB")

    # ---- static PNGs
    K, W, H, S = 1.3, 2400, 1500, 2
    fig, _ = build(["15m"], week_a, week_b, K, head + sub(
        f"Week overview 04–11 Nov 2026 · 15m candles · {summary(week_a, week_b)} · times IST (UTC+5:30)"), True, False, tick=ticks(week_a, week_b, 6, "%a %d"))
    fig.write_image(HERE / "xm_real_week_overview.png", width=W, height=H, scale=S)
    print("wrote xm_real_week_overview.png")
    for day in days:
        a, b, lo, hi = session_window(day)
        tf = "1m" if (b - a) <= pd.Timedelta(hours=10) else "5m"
        utc_day = t[t.close_time.dt.date == day].net.sum()
        fig, _ = build([tf], a, b, K, head + sub(
            f"{day:%a %d %b %Y} · {tf} candles · {ist(a):%H:%M}–{ist(b):%H:%M} IST ({a:%H:%M}–{b:%H:%M} UTC) · {summary(lo, hi)}"), True, True, tick=ticks(a, b, 1, "%a %d %b"))
        fig.write_image(HERE / f"xm_real_day_{day}.png", width=W, height=H, scale=S)
        print(f"wrote xm_real_day_{day}.png  tf={tf}  window {a:%m-%d %H:%M}..{b:%m-%d %H:%M} UTC  session: {summary(lo, hi)}  | UTC-date net {utc_day:+.2f}")
