"""Chart the Dynamic Range Scalper: gold candles with every clip and exit, account value underneath. Last 14 days, IST."""
import sys
import numpy as np, pandas as pd, plotly.graph_objects as go
from plotly.subplots import make_subplots
from data import load_m1
from range_scalp import prep
from range_dyn import P, run

TF = sys.argv[1] if len(sys.argv) > 1 else "5min"      # candle interval: 1min, 5min, 15min
IST = "Asia/Kolkata"; UP, DOWN, BG, WIN, LOSS = "#089981", "#000000", "#DBDBDB", "#1565C0", "#C62828"
raw = load_m1(); d = prep(raw); d = d[d.index >= d.index[-1] - pd.Timedelta(days=14)]
t, dd = run(d, P(K=4, step=1.5, tpa=2.0, decay=0.7, er_exit=9))
c5 = raw[raw.index >= d.index[0]].resample(TF).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
ist = lambda x: pd.DatetimeIndex(x).tz_convert(IST).tz_localize(None)

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.03)
fig.add_trace(go.Candlestick(x=ist(c5.index), open=c5.open, high=c5.high, low=c5.low, close=c5.close, name=f"XAUUSD {TF}",
                             increasing=dict(line=dict(color=UP, width=1), fillcolor=UP), decreasing=dict(line=dict(color=DOWN, width=1), fillcolor=DOWN)), 1, 1)
for win, col, nm in ((True, WIN, "winning basket"), (False, LOSS, "losing basket")):      # one line per clip: fill -> exit
    xs, ys = [], []
    for r in t[(t.pnl > 0) == win].itertuples():
        for ft, fp in zip(r.fill_t, r.fills):
            xs += [ft.tz_convert(IST).tz_localize(None), r.exit_t.tz_convert(IST).tz_localize(None), None]; ys += [fp, r.exit_px, None]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=col, width=1.4), name=nm, hoverinfo="skip"), 1, 1)
f = pd.DataFrame([dict(x=ft, y=fp, side=r.side, k=k + 1, lot=r.lot, pnl=r.pnl, why=r.why, n=r.clips)
                  for r in t.itertuples() for k, (ft, fp) in enumerate(zip(r.fill_t, r.fills))])
for side, sym, nm in ((1, "triangle-up", "buy clip"), (-1, "triangle-down", "sell clip")):
    g = f[f.side == side]
    fig.add_trace(go.Scatter(x=ist(g.x), y=g.y, mode="markers", name=nm,
                             marker=dict(symbol=sym, size=9, color=np.where(g.pnl > 0, WIN, LOSS), line=dict(color="white", width=0.8)),
                             customdata=np.stack([g.k, g.n, g.lot, g.pnl.round(2), g.why], axis=1),
                             hovertemplate=nm + " %{customdata[0]} of %{customdata[1]} · %{customdata[2]} lots @ %{y:.2f}<br>basket $%{customdata[3]} · exit: %{customdata[4]}<extra></extra>"), 1, 1)
for why, sym, nm in (("tp", "circle", "exit: target"), ("stop", "x", "exit: hard stop"), ("time", "square", "exit: time stop"), ("flat", "diamond", "exit: news / end of day")):
    g = t[t.why == why]
    fig.add_trace(go.Scatter(x=ist(g.exit_t), y=g.exit_px, mode="markers", name=nm,
                             marker=dict(symbol=sym, size=7 if why == "tp" else 10, color=np.where(g.pnl > 0, WIN, LOSS), line=dict(color="white", width=0.8)),
                             customdata=np.stack([g.clips, g.pnl.round(2), g.mins], axis=1),
                             hovertemplate=nm + " @ %{y:.2f}<br>%{customdata[0]} clips · $%{customdata[1]} · %{customdata[2]} min<extra></extra>"), 1, 1)
eqx = [ist([d.index[0]])[0]] + list(ist(t.exit_t)); eqy = [10_000.0] + list(t["eq"])
fig.add_trace(go.Scatter(x=eqx, y=eqy, mode="lines", line=dict(color="#1565C0", width=2, shape="hv"), name="account value",
                         hovertemplate="$%{y:,.2f}<extra></extra>"), 2, 1)
fig.add_hline(y=10_000, line=dict(color="#666", width=1, dash="dot"), row=2, col=1)
w = t.pnl[t.pnl > 0]; lo = t.pnl[t.pnl <= 0]
fig.update_layout(title=f"Dynamic Range Scalper on XAUUSD · {TF} candles · last 14 days · 10,000 USD account · cost 0.25 pt<br><sup>{len(t)} baskets · {len(w)/len(t):.0%} wins · "
                        f"profit factor {w.sum()/-lo.sum():.2f} · net {t.pnl.sum():+,.0f} USD · worst day {dd.pct.min():+.2f}% · times in IST</sup>",
                  plot_bgcolor=BG, paper_bgcolor=BG, font=dict(color="#111"), hovermode="closest", dragmode="pan", height=900,
                  legend=dict(orientation="h", y=1.0, yanchor="bottom", x=1, xanchor="right"), margin=dict(l=60, r=30, t=90, b=40), xaxis_rangeslider_visible=False)
gaps = c5.index.to_series().diff(); br = [dict(bounds=[(a - g).tz_convert(IST).tz_localize(None) + pd.Timedelta(TF), a.tz_convert(IST).tz_localize(None)]) for a, g in gaps.items() if g > pd.Timedelta(minutes=30)]
fig.update_xaxes(showgrid=False, rangebreaks=br)
if TF == "1min":                                         # open on the last trading day, scaled to it; pan/zoom for the rest
    v = c5[c5.index >= c5.index[-1] - pd.Timedelta(hours=14)]; e = t[t.exit_t >= v.index[0]]["eq"]
    fig.update_xaxes(range=[ist([v.index[0]])[0], ist([v.index[-1]])[0]])
    fig.update_yaxes(range=[v.low.min() - 2, v.high.max() + 2], row=1, col=1)
    fig.update_yaxes(range=[e.min() - 20, e.max() + 20], row=2, col=1)
fig.update_yaxes(showgrid=False)
fig.update_yaxes(title_text="gold (USD)", row=1, col=1); fig.update_yaxes(title_text="account ($)", tickformat=",.0f", row=2, col=1)
fig.write_html(f"dyn_scalper_chart_{TF}.html", include_plotlyjs="cdn", config=dict(scrollZoom=True, displaylogo=False))
fig.write_image(f"dyn_scalper_chart_{TF}.png", width=2200, height=1100, scale=1)
print(len(t), "baskets", round(t.pnl.sum(), 2), "| breaks", len(br))
