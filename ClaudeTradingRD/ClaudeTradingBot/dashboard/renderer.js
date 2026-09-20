/* Renderer: candlestick chart + account header + position/levels panels.
   Data comes from data.json via the preload bridge (window.api.readData),
   refreshed every 30 seconds. */

const START_BALANCE = 5002.40;  // FundingPips demo start (2026-06-25)
const TARGET_BALANCE = 5500;    // goal
const REFRESH_MS = 30000;
const BETS_REFRESH_MS = 5000; // fast, broker-free poll for live 5-min bet prices

let currentTf = 'H1';
let currentSymbol = 'XAUUSD';
let chart = null;
let series = null;
let priceLines = [];
let seriesMarkers = null; // v5 markers primitive (created lazily on first use)
let lastBars = [];        // bars currently in the series (for incremental updates)
let lastSeriesKey = null; // `${symbol}|${tf}` the series is currently seeded with
let lastData = null;
let levels = null;
let betsData = null; // from bets.json (fast feed); falls back to data.json bets
let live5mData = null; // from live5m.json (per-second feed)
let lastSpot = null;

const $ = (id) => document.getElementById(id);
const fmt = (n, d = 2) =>
  n == null || isNaN(n) ? '—' : Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

/* ---------- chart setup ---------- */

function lineStyleOf(name) {
  const LS = LightweightCharts.LineStyle;
  return name === 'dashed' ? LS.Dashed : name === 'dotted' ? LS.Dotted : LS.Solid;
}

function createChart() {
  const el = $('chart');
  chart = LightweightCharts.createChart(el, {
    layout: { background: { color: '#131722' }, textColor: '#d1d4dc' },
    grid: {
      vertLines: { color: '#1e222d' },
      horzLines: { color: '#1e222d' },
    },
    rightPriceScale: { borderColor: '#2a2e39' },
    timeScale: { borderColor: '#2a2e39', timeVisible: true, secondsVisible: false },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  });

  const opts = {
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderUpColor: '#26a69a',
    borderDownColor: '#ef5350',
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350',
    priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
  };

  // v4 API: addCandlestickSeries; v5 API: addSeries(CandlestickSeries, opts)
  if (typeof chart.addCandlestickSeries === 'function') {
    series = chart.addCandlestickSeries(opts);
  } else {
    series = chart.addSeries(LightweightCharts.CandlestickSeries, opts);
  }

  new ResizeObserver(() => {
    chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
  }).observe(el);
}

function candlesFor(symbol) {
  if (lastData && lastData.symbols && lastData.symbols[symbol]) {
    return lastData.symbols[symbol].candles;
  }
  return symbol === 'XAUUSD' && lastData ? lastData.candles : null; // legacy data.json
}

function levelsFor(symbol) {
  if (!levels) return null;
  if (levels[symbol] && Array.isArray(levels[symbol].levels)) return levels[symbol].levels;
  return symbol === 'XAUUSD' && Array.isArray(levels.levels) ? levels.levels : null; // legacy
}

let lastBarCount = 0;

function setCandles(tf, fit = false) {
  const all = candlesFor(currentSymbol);
  if (!all || !all[tf]) return;
  const bars = all[tf]
    .map((c) => ({
      time: Math.floor(new Date(c.time).getTime() / 1000),
      open: c.o,
      high: c.h,
      low: c.l,
      close: c.c,
    }))
    .sort((a, b) => a.time - b.time);
  if (!bars.length) return;

  const ts = chart.timeScale();
  const key = currentSymbol + '|' + tf;

  // Full (re)seed ONLY when the symbol/timeframe changed, on first load, or when
  // an explicit fit is requested. A periodic 30s refresh must NOT call setData on
  // the same series — that re-seeds every candle and visibly flashes/jumps the
  // chart. Instead we diff and update just the moving/new bars below.
  if (fit || key !== lastSeriesKey || !lastBars.length) {
    series.setData(bars);
    lastBars = bars;
    lastSeriesKey = key;
    lastBarCount = bars.length;
    ts.fitContent();
    return;
  }

  // Incremental refresh (same symbol+tf): update the last existing bar in place
  // (its OHLC may have moved) and append any genuinely new bars. series.update()
  // touches only the tail, so the user's zoom/scroll is preserved untouched.
  const prevLastTime = lastBars[lastBars.length - 1].time;
  const range = ts.getVisibleLogicalRange();
  const wasAtRightEdge = range && lastBarCount > 0 && range.to >= lastBarCount - 1.5;
  let appended = false;
  for (const b of bars) {
    if (b.time >= prevLastTime) {
      series.update(b);
      if (b.time > prevLastTime) appended = true;
    }
  }
  lastBars = bars;
  lastBarCount = bars.length;
  if (appended && wasAtRightEdge) ts.scrollToRealTime(); // keep following live candles
}

/* ---------- on-chart position markers (entry arrows for this bot's trades) ---------- */

function setMarkers(markers) {
  // v5 moved markers off the series onto a primitive created via the global
  // helper; v4 had series.setMarkers. Support whichever the bundle exposes.
  if (series && typeof series.setMarkers === 'function') {
    series.setMarkers(markers);
    return;
  }
  if (typeof LightweightCharts !== 'undefined' &&
      typeof LightweightCharts.createSeriesMarkers === 'function') {
    if (!seriesMarkers) seriesMarkers = LightweightCharts.createSeriesMarkers(series, markers);
    else seriesMarkers.setMarkers(markers);
  }
}

function redrawPositionMarkers() {
  if (!series) return;
  const positions = (lastData && lastData.positions) || [];
  const markers = positions
    .filter((p) => !p.symbol || p.symbol === currentSymbol)
    .map((pos) => {
      const isSell = String(pos.type || '').includes('SELL');
      const t = pos.time ? Math.floor(new Date(pos.time).getTime() / 1000) : null;
      if (t == null || isNaN(t)) return null;
      return {
        time: t,
        position: isSell ? 'aboveBar' : 'belowBar',
        color: isSell ? '#ef5350' : '#26a69a',
        shape: isSell ? 'arrowDown' : 'arrowUp',
        text: (isSell ? 'SELL ' : 'BUY ') + fmt(pos.openPrice) + '  ' + fmt(pos.volume) + ' lot',
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.time - b.time); // lightweight-charts requires ascending time
  setMarkers(markers);
}

function redrawPriceLines() {
  priceLines.forEach((pl) => series.removePriceLine(pl));
  priceLines = [];

  const add = (price, title, color, style) => {
    if (price == null || isNaN(price) || Number(price) === 0) return;
    priceLines.push(
      series.createPriceLine({
        price: Number(price),
        title,
        color,
        lineWidth: 1,
        lineStyle: lineStyleOf(style),
        axisLabelVisible: true,
      })
    );
  };

  const lvls = levelsFor(currentSymbol);
  if (lvls) {
    lvls.forEach((lv) => add(lv.price, lv.label, lv.color || '#787b86', lv.style || 'dashed'));
  }

  const positions = (lastData && lastData.positions) || [];
  positions
    .filter((p) => !p.symbol || p.symbol === currentSymbol)
    .forEach((pos) => {
      add(pos.openPrice, 'ENTRY', '#42a5f5', 'solid');
      add(pos.stopLoss, 'SL', '#ef5350', 'solid');
      add(pos.takeProfit, 'TP', '#26a69a', 'solid');
    });
}

/* ---------- panels ---------- */

function renderHeader(d) {
  const a = d.account || {};
  $('balance').textContent = '$' + fmt(a.balance);
  $('equity').textContent = '$' + fmt(a.equity);
  $('margin').textContent = '$' + fmt(a.margin);
  $('freeMargin').textContent = '$' + fmt(a.freeMargin);

  // Live P&L: Float = sum of open-position profit; Day = equity vs session start.
  const positions = (d.positions || []);
  const floatPnl = positions.reduce((s, p) => s + (p.profit != null ? p.profit : (p.unrealizedProfit || 0)), 0);
  const dayPnl = (a.equity != null ? a.equity : a.balance) - START_BALANCE;
  const fpEl = $('floatPnl'), dpEl = $('dayPnl');
  if (fpEl) {
    fpEl.textContent = (floatPnl >= 0 ? '+$' : '-$') + fmt(Math.abs(floatPnl));
    fpEl.classList.toggle('pos', floatPnl > 0); fpEl.classList.toggle('neg', floatPnl < 0);
  }
  if (dpEl) {
    dpEl.textContent = (dayPnl >= 0 ? '+$' : '-$') + fmt(Math.abs(dayPnl));
    dpEl.classList.toggle('pos', dayPnl > 0); dpEl.classList.toggle('neg', dayPnl < 0);
  }

  const eq = a.equity != null ? a.equity : a.balance;
  const pct = eq != null
    ? Math.max(0, Math.min(100, ((eq - START_BALANCE) / (TARGET_BALANCE - START_BALANCE)) * 100))
    : 0;
  $('progressFill').style.width = pct.toFixed(1) + '%';
  $('progressPct').textContent = pct.toFixed(1) + '%';

  const eqEl = $('equity');
  eqEl.classList.toggle('pos', a.equity > a.balance);
  eqEl.classList.toggle('neg', a.equity < a.balance);

  $('updated').textContent = d.generated_at
    ? 'updated ' + new Date(d.generated_at).toLocaleTimeString()
    : 'no data yet';

  const sym = (d.symbols && d.symbols[currentSymbol]) || {};
  const p = sym.price || (currentSymbol === 'XAUUSD' ? d.price : null) || {};
  $('price-tag').textContent = p.mid != null ? currentSymbol + '  ' + fmt(p.mid) : '—';

  const xau = d.symbols && d.symbols.XAUUSD && d.symbols.XAUUSD.price;
  const btc = d.symbols && d.symbols.BTCUSDT && d.symbols.BTCUSDT.price;
  $('xauMini').textContent = xau && xau.mid != null ? fmt(xau.mid) : '—';
  $('btcMini').textContent = btc && btc.mid != null ? fmt(btc.mid, 0) : '—';
}

function renderPosition(d) {
  const positions = (d && d.positions) || [];
  const html = positions.length
    ? positions
        .map((pos) => {
          const side = String(pos.type || '').includes('SELL') ? 'sell' : 'buy';
          const pnl = pos.profit != null ? pos.profit : pos.unrealizedProfit;
          const pnlCls = pnl >= 0 ? 'pos' : 'neg';
          return `
        <div class="pos-cell" style="margin-bottom:10px">
          <span class="side-badge ${side}">${side}</span>
          <span style="font-size:12px;font-weight:700;margin-left:6px">${pos.symbol || ''}</span>
          <span style="float:right;font-weight:600">${fmt(pos.volume)} lots</span>
          <div class="row"><span class="k">Entry</span><span class="v">${fmt(pos.openPrice)}</span></div>
          <div class="row"><span class="k">SL</span><span class="v" style="color:var(--red)">${fmt(pos.stopLoss)}</span></div>
          <div class="row"><span class="k">TP</span><span class="v" style="color:var(--green)">${fmt(pos.takeProfit)}</span></div>
          <div class="row"><span class="k">Current</span><span class="v">${fmt(pos.currentPrice)}</span></div>
          <div class="pnl-big ${pnlCls}">${pnl >= 0 ? '+' : ''}$${fmt(pnl)}</div>
        </div>`;
        })
        .join('')
    : '<div class="empty">No open position</div>';
  ['positionBody', 'positionBodyFull'].forEach((id) => {
    const el = $(id);
    if (el) el.innerHTML = html;
  });
}

function renderOrders(d) {
  const body = $('ordersBody');
  const orders = d.orders || [];
  if (!orders.length) {
    body.innerHTML = '<div class="empty">No pending orders</div>';
    return;
  }
  body.innerHTML = orders
    .map((o) => {
      const side = String(o.type || '').includes('SELL') ? 'sell' : 'buy';
      return `
        <div style="margin-bottom:10px">
          <span class="side-badge ${side}">${(o.type || '').replace('ORDER_TYPE_', '').replace(/_/g, ' ').toLowerCase()}</span>
          <span style="float:right;font-weight:600">${fmt(o.volume)} lots</span>
          <div class="row"><span class="k">Price</span><span class="v">${fmt(o.openPrice)}</span></div>
          <div class="row"><span class="k">SL</span><span class="v">${fmt(o.stopLoss)}</span></div>
          <div class="row"><span class="k">TP</span><span class="v">${fmt(o.takeProfit)}</span></div>
        </div>`;
    })
    .join('');
}

/* ---------- trade history (the trades this bot took, per symbol) ---------- */

// orders.csv timestamps are "YYYY-MM-DD HH:MM:SS" in UTC (no zone marker).
// Normalise to ISO-UTC so the browser renders them in the user's local time.
function fmtTradeTime(s) {
  if (!s) return '—';
  const d = new Date(String(s).replace(' ', 'T') + 'Z');
  return isNaN(d.getTime()) ? String(s) : d.toLocaleString();
}

function renderHistorySummary(el, s) {
  if (!el) return;
  if (!s) { el.innerHTML = ''; return; }
  const netCls = (s.net_pnl || 0) >= 0 ? 'pos' : 'neg';
  const money = (v) => (v >= 0 ? '+$' : '-$') + Math.abs(Number(v || 0)).toFixed(2);
  const stat = (h, v, colour) =>
    `<div class="hist-stat"><span class="cmp-h">${h}</span>
       <span class="v" ${colour ? `style="color:${colour}"` : ''}>${v}</span></div>`;
  el.innerHTML = `<div class="hist-summary">
      ${stat('Net P&amp;L', money(s.net_pnl), netCls === 'pos' ? 'var(--green)' : 'var(--red)')}
      ${stat('Closed', s.closed)}
      ${stat('Win rate', s.win_rate != null ? s.win_rate + '%' : '—')}
      ${stat('Wins / Losses', (s.wins || 0) + ' / ' + (s.losses || 0))}
      ${stat('Open', s.open)}
      ${stat('Cancelled', s.cancelled)}
    </div>`;
}

function renderTradeTable(el, trades) {
  if (!el) return;
  if (!trades || !trades.length) {
    el.innerHTML = '<div class="empty">no trades recorded yet</div>';
    return;
  }
  const rows = trades.map((t) => {
    const side = String(t.side || '').includes('sell') ? 'sell' : 'buy';
    const pnl = t.profit_usd;
    const pnlCol = pnl == null ? 'var(--muted)' : (pnl >= 0 ? 'var(--green)' : 'var(--red)');
    const pnlStr = pnl == null ? '—' : ((pnl >= 0 ? '+$' : '-$') + Math.abs(Number(pnl)).toFixed(2));
    return `<tr>
        <td>${fmtTradeTime(t.entry_time)}</td>
        <td><span class="side-badge ${side}">${side}</span></td>
        <td>${fmt(t.lots)}</td>
        <td>${fmt(t.entry_price)}</td>
        <td>${t.exit_price != null ? fmt(t.exit_price) : '—'}</td>
        <td style="color:${pnlCol};font-weight:700">${pnlStr}</td>
        <td><span class="pill ${t.status}">${t.status}</span></td>
        <td class="pm-purpose">${t.notes || ''}</td>
      </tr>`;
  }).join('');
  el.innerHTML = `<table class="pm-tbl"><thead><tr>
      <th>Entry (local)</th><th>Side</th><th>Lots</th><th>Entry</th><th>Exit</th>
      <th>P&amp;L</th><th>Status</th><th>Intent &mdash; why taken</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
}

function renderHistory(d) {
  const tr = (d && d.trades) || {};
  const summ = tr.summary || {};
  renderHistorySummary($('histXauSummary'), summ.XAUUSD);
  renderTradeTable($('histXauBody'), tr.XAUUSD);
  renderHistorySummary($('histBtcSummary'), summ.BTCUSDT);
  renderTradeTable($('histBtcBody'), tr.BTCUSDT);
}

function renderLevels() {
  const body = $('levelsBody');
  const lvls = levelsFor(currentSymbol);
  if (!lvls) {
    body.innerHTML = '<div class="empty">levels.json not found</div>';
    return;
  }
  body.innerHTML = lvls
    .map(
      (lv) => `
      <div class="row">
        <span class="k"><span style="color:${lv.color || '#787b86'}">&#9644;</span> ${lv.label}</span>
        <span class="v">${fmt(lv.price)}</span>
      </div>`
    )
    .join('');
}

function probBar(pct, color) {
  const w = Math.max(0, Math.min(100, pct));
  return `<div style="flex:1;height:8px;background:var(--border);border-radius:4px;overflow:hidden;margin:0 6px">
            <div style="height:100%;width:${w}%;background:${color}"></div>
          </div>`;
}

function renderBetVenue(name, cdf, spotBtc) {
  if (!cdf || !cdf.levels || !cdf.levels.length) return '';
  const pivot = cdf.implied_pivot;
  const kfmt = (t) => {
    const k = t / 1000;
    return '$' + (Number.isInteger(k) ? k.toFixed(0) : k.toFixed(1)) + 'k';
  };
  const rows = cdf.levels
    .filter((l) => l.prob_above > 0.02 && l.prob_above < 0.98) // keep the informative band
    .map((l) => {
      const pct = l.prob_above * 100;
      const col = pct >= 50 ? 'var(--green)' : 'var(--red)';
      return `<div style="display:flex;align-items:center;font-size:11px;padding:1px 0">
                <span style="color:var(--muted);width:54px">${kfmt(l.threshold)}</span>
                ${probBar(pct, col)}
                <span style="width:34px;text-align:right;font-variant-numeric:tabular-nums">${pct.toFixed(0)}%</span>
              </div>`;
    })
    .join('');
  const pivotLine = pivot
    ? `<div style="font-size:11px;color:var(--accent);margin:4px 0 2px">implied fair value &asymp; $${fmt(pivot, 0)}${
        spotBtc ? `  (spot ${fmt(spotBtc, 0)})` : ''
      }</div>`
    : '';
  const live = cdf.price_source === 'clob' || (cdf.levels[0] && cdf.levels[0].trade_time);
  const liveBadge = live
    ? '<span style="color:var(--green);font-size:9px">&#9679; LIVE</span>'
    : '';
  const settles = cdf.settles
    ? `<div style="font-size:9px;color:var(--muted)">settles ${new Date(cdf.settles).toLocaleString()}</div>`
    : '';
  return `<div style="margin-bottom:8px">
            <div style="font-size:11px;font-weight:700;color:var(--text);text-transform:uppercase">${name} ${liveBadge}</div>
            ${settles}${pivotLine}${rows || '<div class="empty" style="font-size:11px">no near-money strikes</div>'}
          </div>`;
}

function fmtClock(secs) {
  if (secs == null || secs < 0) return '--:--';
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

// Independent 1s ticker: keeps every 5-min countdown accurate regardless of
// how often bets.json is re-read (the window_end is absolute time).
function tickCountdowns() {
  document.querySelectorAll('.cd[data-end]').forEach((el) => {
    const end = new Date(el.dataset.end).getTime();
    const left = Math.max(0, Math.round((end - Date.now()) / 1000));
    el.textContent = fmtClock(left);
    el.style.color = left <= 30 ? 'var(--red)' : left <= 60 ? 'var(--accent)' : 'var(--text)';
  });
}

function renderUpDown5m(updown) {
  const wins = (updown && updown.windows) || [];
  if (!wins.length) return '';
  const rowFor = (w) => {
    const up = w.up_prob != null ? Math.round(w.up_prob * 100) : null;
    const dn = up != null ? 100 - up : null;
    const tag = w.current ? 'NOW' : 'NEXT';
    const tagCol = w.current ? 'var(--accent)' : 'var(--muted)';
    const upBig = up != null && up >= dn;
    return `<div style="margin:3px 0;padding:4px 6px;background:var(--bg);border:1px solid var(--border);border-radius:6px">
              <div style="display:flex;align-items:center;font-size:10px">
                <span style="font-weight:700;color:${tagCol}">${tag}</span>
                <span class="cd" data-end="${w.window_end}" style="margin-left:6px;font-variant-numeric:tabular-nums;font-weight:700">--:--</span>
                <span style="margin-left:auto;color:var(--muted)">closes ${
                  w.window_end ? new Date(w.window_end).toLocaleTimeString() : '—'
                }</span>
              </div>
              <div style="display:flex;align-items:center;gap:6px;margin-top:3px">
                <span style="font-size:12px;font-weight:700;color:var(--green);width:74px">UP ${
                  up != null ? up + '%' : '—'
                }</span>
                <div style="flex:1;height:7px;background:rgba(239,83,80,.35);border-radius:4px;overflow:hidden">
                  <div style="height:100%;width:${up || 0}%;background:var(--green)"></div>
                </div>
                <span style="font-size:12px;font-weight:700;color:var(--red);width:74px;text-align:right">${
                  dn != null ? dn + '%' : '—'
                } DN</span>
              </div>
            </div>`;
  };
  const liveDot = wins[0].live ? '<span style="color:var(--green);font-size:9px">&#9679; LIVE</span>' : '';
  return `<div style="margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border)">
            <div style="font-size:11px;font-weight:700;color:var(--text);text-transform:uppercase">BTC 5-min Up/Down ${liveDot}</div>
            <div style="font-size:9px;color:var(--muted);margin-bottom:2px">Polymarket rolling 5-minute market</div>
            ${wins.map(rowFor).join('')}
          </div>`;
}

// Implied P(BTC > spot) interpolated from a venue's threshold CDF.
function probAbove(levels, spot) {
  if (!levels || !levels.length || spot == null) return null;
  const L = levels.slice().sort((a, b) => a.threshold - b.threshold);
  if (spot <= L[0].threshold) return L[0].prob_above;
  if (spot >= L[L.length - 1].threshold) return L[L.length - 1].prob_above;
  for (let i = 0; i < L.length - 1; i++) {
    if (spot >= L[i].threshold && spot <= L[i + 1].threshold) {
      const f = (spot - L[i].threshold) / (L[i + 1].threshold - L[i].threshold);
      return L[i].prob_above + f * (L[i + 1].prob_above - L[i].prob_above);
    }
  }
  return null;
}

// Side-by-side: live BTC spot vs each venue's implied fair value + P(>spot).
function renderCompare() {
  const body = $('compareBody');
  if (!body) return;
  const spot = live5mData && live5mData.btc_spot != null ? live5mData.btc_spot : lastSpot;
  const poly = betsData && betsData.polymarket && betsData.polymarket.btc_cdf;
  const kal = betsData && betsData.kalshi && betsData.kalshi.btc_cdf;
  const col = (h, big, sub, accent) =>
    `<div class="cmp-col"><div class="cmp-h">${h}</div>
       <div class="cmp-big" style="color:${accent}">${big}</div>
       <div class="cmp-sub">${sub}</div></div>`;

  const spotStr = spot != null ? '$' + fmt(spot, 0) : '—';

  let polyBig = '—', polySub = 'no data';
  if (poly) {
    const pa = probAbove(poly.levels, spot);
    polyBig = poly.implied_pivot != null ? '$' + fmt(poly.implied_pivot, 0) : '—';
    polySub = (pa != null ? `P(&gt;spot) <b>${Math.round(pa * 100)}%</b>` : '') +
              (poly.title ? `<br>${poly.title}` : '');
  }

  let kalBig = '—', kalSub = 'no live quotes';
  if (kal && kal.levels && kal.levels.length) {
    const pa = probAbove(kal.levels, spot);
    kalBig = kal.implied_pivot != null ? '$' + fmt(kal.implied_pivot, 0) : '—';
    kalSub = (pa != null ? `P(&gt;spot) <b>${Math.round(pa * 100)}%</b>` : '') +
             (kal.settles ? `<br>settles ${new Date(kal.settles).toLocaleTimeString()}` : '');
  }

  body.innerHTML = `<div class="cmp">
    ${col('BTC Spot &middot; Binance (live)', spotStr, 'updates every second', '#42a5f5')}
    ${col('Polymarket &middot; implied fair value', polyBig, polySub, '#b07cff')}
    ${col('Kalshi &middot; implied fair value', kalBig, kalSub, '#26a69a')}
  </div>`;
}

// Dedicated PM paper account: balance/equity/progress + readable order log.
function renderPM(pm) {
  const body = $('pmBody');
  if (!body) return;
  if (!pm || !pm.summary) {
    body.innerHTML = '<div class="empty">no paper account yet</div>';
    return;
  }
  const s = pm.summary;
  const pnlCol = s.realized_pnl >= 0 ? 'var(--green)' : 'var(--red)';
  const prog = Math.max(0, Math.min(100, s.progress_pct));
  const stat = (h, v, c) =>
    `<div class="pm-stat"><div class="cmp-h">${h}</div>
       <div style="font-size:19px;font-weight:800;${c ? 'color:' + c : ''}">${v}</div></div>`;
  let html = `<div style="display:flex;flex-wrap:wrap;gap:22px;align-items:center;margin-bottom:12px">
      ${stat('Balance', '$' + fmt(s.balance))}
      ${stat('Equity', '$' + fmt(s.equity))}
      ${stat('Realized P&amp;L', (s.realized_pnl >= 0 ? '+' : '') + '$' + fmt(s.realized_pnl), pnlCol)}
      ${stat('Fees paid', '$' + fmt(s.total_fees), 'var(--red)')}
      ${stat('Trades', s.settled_trades + (s.win_rate != null ? ' · ' + s.win_rate + '% win' : ''))}
      ${stat('Outcomes', `${pm.normals || 0} win${pm.windfalls ? ' · ' + pm.windfalls + '&times;2' : ''} · <span style="color:var(--red)">${pm.breaks || 0} basis break</span>`)}
      <div style="flex:1;min-width:220px">
        <div class="progress-label"><span>$${fmt(s.start, 0)} start</span><span>${s.progress_pct}%</span><span>$${fmt(s.target, 0)}</span></div>
        <div class="progress-bar"><div class="progress-fill" style="width:${prog}%"></div></div>
      </div>
    </div>`;

  if (pm.open && pm.open.length) {
    html += '<div style="font-size:11px;font-weight:700;color:var(--text);margin:6px 0 4px">Open</div>';
    html += pm.open.map((p) =>
      `<div style="font-size:11px;padding:7px 9px;background:var(--bg);border:1px solid var(--border);border-radius:6px;margin-bottom:5px">
         <b>${p.side} &times;${p.shares} @ ${Math.round(p.price * 100)}&cent;</b>
         &middot; cost $${fmt(p.cost)} &middot; fee $${fmt(p.fee)}
         &middot; settles <span class="cd" data-end="${p.settles}">${p.settles ? new Date(p.settles).toLocaleTimeString() : '—'}</span>
         <div class="pm-purpose">${p.purpose || ''}</div>
       </div>`).join('');
  }

  html += '<div style="font-size:11px;font-weight:700;color:var(--text);margin:12px 0 4px">Order History &mdash; why each trade was taken</div>';
  if (pm.history && pm.history.length) {
    html += `<table class="pm-tbl"><thead><tr>
        <th>Closed</th><th>Trade</th><th>Purpose</th><th>Stake</th><th>Fee</th><th>Result</th><th>P&amp;L</th>
      </tr></thead><tbody>`;
    html += pm.history.map((h) => {
      const won = h.won;
      const ppu = h.payout_per_unit;
      const pc = (h.pnl || 0) >= 0 ? 'var(--green)' : 'var(--red)';
      // Real-settlement result: 0 = basis break (both legs lost), 2 = windfall, 1 = normal.
      const result = ppu === 0 ? 'BASIS BREAK' : (ppu === 2 ? 'WIN &times;2' : (won ? 'WON' : 'LOST'));
      const rcol = ppu === 0 ? 'var(--red)' : (won || ppu === 2 ? 'var(--green)' : 'var(--red)');
      const note = h.settle_note ? `<br><span class="pm-purpose">${h.settle_note}</span>` : '';
      return `<tr${ppu === 0 ? ' style="background:rgba(255,80,80,0.08)"' : ''}>
          <td>${h.closed_at ? new Date(h.closed_at).toLocaleTimeString() : '—'}</td>
          <td>${h.side} &times;${h.shares}<br><span class="pm-purpose">@ ${Math.round(h.price * 100)}&cent;</span></td>
          <td class="pm-purpose">${h.purpose || h.tag || ''}</td>
          <td>$${fmt(h.cost)}</td>
          <td style="color:var(--red)">$${fmt(h.fee)}</td>
          <td style="color:${rcol};font-weight:700">${result}${note}</td>
          <td style="color:${pc};font-weight:700">${(h.pnl || 0) >= 0 ? '+' : ''}$${fmt(h.pnl)}</td>
        </tr>`;
    }).join('');
    html += '</tbody></table>';
  } else {
    html += '<div class="empty" style="font-size:11px">no settled trades yet — the strategy only enters when net edge after fees is positive</div>';
  }
  // Forward edge-test panel (the only not-yet-killed candidate, scored on real data).
  const r = (typeof live5mData !== 'undefined' && live5mData) ? live5mData.research : null;
  if (r && r.n > 0) {
    const mc = r.mean_net_per_ct > 0 ? 'var(--green)' : 'var(--red)';
    html += `<div style="margin-top:12px;padding:9px 11px;background:var(--bg);border:1px solid var(--border);border-radius:6px">
        <div style="font-size:11px;font-weight:700">Forward edge test — Kalshi-only momentum, scored on REAL executable asks + true settlements</div>
        <div style="font-size:12px;margin-top:3px">n=${r.n}/${r.need} windows &middot; favorite win ${r.fav_win_pct}% &middot;
          mean net <span style="color:${mc};font-weight:700">${r.mean_net_per_ct >= 0 ? '+' : ''}$${r.mean_net_per_ct.toFixed(4)}/contract</span>
          &middot; basis-break ${r.basis_break_pct}%</div>
        <div class="pm-purpose">a real edge needs mean clearly &gt; 0 over ~${r.need} windows; still accumulating</div>
      </div>`;
  } else if (r) {
    html += `<div style="margin-top:12px;padding:9px 11px;background:var(--bg);border:1px solid var(--border);border-radius:6px;font-size:12px">
        <b>Forward edge test</b> — ${r.note || 'accumulating'}</div>`;
  }
  html += '<div class="ud-foot">Separate paper account. Now settled on EACH venue\'s ACTUAL resolution — a pair pays $1 per leg that won, so 0 = basis break (both legs lose the stake), 1 = normal, 2 = windfall. This account therefore reflects the real basis-risk tail, not the old optimistic "every lock pays $1" model.</div>';
  body.innerHTML = html;
}

// One venue's Up/Down block (Polymarket 5-min or Kalshi hourly).
function udBlock(venue, horizon, w, accent) {
  if (!w) {
    return `<div class="ud-venue"><div class="ud-vh" style="color:${accent}">${venue}
              <span style="color:var(--muted);font-weight:400">· ${horizon}</span></div>
            <div class="empty" style="font-size:12px">no live market</div></div>`;
  }
  const cents = (v) => (v == null ? '—' : (v * 100).toFixed(0) + '¢');
  const ret = (v) => (v == null || v <= 0 || v >= 1 ? '' : '+' + Math.round((1 / v - 1) * 100) + '%');
  const end = w.window_end || w.settles;
  const sub = w.label && /\$/.test(w.label) ? w.label : '';
  const head = `<div class="ud-head">
      <span class="ud-vh" style="color:${accent}">${venue}
        <span style="color:var(--muted);font-weight:400">· ${horizon}${sub ? ' · ' + sub : ''}</span></span>
      <span class="cd ud-cd" data-end="${end}">--:--</span>
    </div>`;
  if (w.up_cost == null) {
    return `<div class="ud-venue">${head}
        <div class="empty" style="font-size:12px;padding:10px 0">waiting for first trade this window…</div></div>`;
  }
  const upPct = (w.up_mid != null ? w.up_mid : w.up_cost) * 100;
  return `<div class="ud-venue">${head}
      <div class="ud-wrap">
        <div class="ud-btn ud-up">
          <div class="ud-side" style="color:var(--green)">&#9650; UP</div>
          <div class="ud-cost" style="color:var(--green)">${cents(w.up_cost)}</div>
          <div class="ud-ret">${ret(w.up_cost)}</div>
        </div>
        <div class="ud-btn ud-down">
          <div class="ud-side" style="color:var(--red)">&#9660; DOWN</div>
          <div class="ud-cost" style="color:var(--red)">${cents(w.down_cost)}</div>
          <div class="ud-ret">${ret(w.down_cost)}</div>
        </div>
      </div>
      <div class="ud-bar"><div class="up" style="width:${upPct}%"></div><div class="dn" style="width:${100 - upPct}%"></div></div>
    </div>`;
}

// Cross-venue 15m arb economics block — shared by the markets view and the
// Live Account tab so both show the same lock cost -> gross -> net analysis.
function arbBlock(arb) {
  if (!arb || arb.status !== 'evaluated') return '';
  const gross = arb.gross_edge, net = arb.net_edge_after_fees;
  const good = arb.actionable;
  const brd = good ? 'rgba(38,166,154,.55)' : 'var(--border)';
  const bg = good ? 'rgba(38,166,154,.10)' : 'var(--bg)';
  const gc = (v) => (v > 0 ? 'var(--green)' : 'var(--red)');
  return `<div style="margin-top:14px;padding:11px 13px;border:1px solid ${brd};border-radius:8px;background:${bg}">
      <div style="font-size:12px;font-weight:700;color:${good ? 'var(--green)' : 'var(--muted)'}">
        ${good ? '&#9889; CROSS-VENUE 15m ARB (Poly &harr; Kalshi, same window)' : 'Cross-venue 15m &middot; no net edge right now'}</div>
      <div style="font-size:12px;margin-top:5px">lock cost <b>${Math.round(arb.lock_cost * 100)}&cent;</b>
        &rarr; gross <b style="color:${gc(gross)}">${(gross * 100).toFixed(1)}&cent;</b>
        &middot; net after ~3.5% fees <b style="color:${gc(net)}">${(net * 100).toFixed(1)}&cent;</b></div>
      <div style="font-size:11px;color:var(--text);margin-top:3px">${arb.legs || ''}</div>
      <div style="font-size:10px;color:var(--accent);margin-top:3px">&#9888; basis risk: Polymarket (Chainlink) vs Kalshi (index) open reference can differ &middot; paper-validate (logging to journal/arb15m_log.csv)</div>
    </div>`;
}

// Live Up/Down — Polymarket (5-min, per-second) vs Kalshi (hourly) side by side.
function renderLive5m() {
  const body = $('live5mBody');
  if (!body) return;
  const p5 = live5mData && live5mData.poly_5m;
  const p15 = live5mData && live5mData.poly_15m;
  const k15 = (live5mData && live5mData.kalshi_15m) ||
              (betsData && betsData.kalshi && betsData.kalshi.updown);
  const arb = live5mData && live5mData.arb15m;
  const arbHtml = arbBlock(arb);
  body.innerHTML = `
    <div class="ud-venues">
      ${udBlock('Polymarket', '5-min', p5, '#b07cff')}
      ${udBlock('Polymarket', '15-min', p15, '#b07cff')}
      ${udBlock('Kalshi', '15-min', k15, '#26a69a')}
    </div>
    ${arbHtml}
    <div class="ud-foot">Cost = price to buy 1 share (pays $1.00 if correct). Polymarket 5m &amp; 15m CLOB ask &middot; Kalshi 15m last trade &middot; all per-second. Polymarket 15m and Kalshi 15m share the same window.</div>`;
  tickCountdowns();
}

function renderLiveAccount() {
  const acc = live5mData && live5mData.live;
  const banner = $('liveBanner');
  const bal = $('liveBalBody');
  const p15 = live5mData && live5mData.poly_15m;
  const k15 = (live5mData && live5mData.kalshi_15m) ||
              (betsData && betsData.kalshi && betsData.kalshi.updown);

  const px = $('live15mBody');
  if (px) {
    // Same cross-venue 15m arb analysis the markets view shows (lock cost ->
    // gross -> net after fees), so the live tab makes the trade decision visible.
    const arb = live5mData && live5mData.arb15m;
    px.innerHTML = `<div class="ud-venues">
        ${udBlock('Polymarket', '15-min', p15, '#b07cff')}
        ${udBlock('Kalshi', '15-min', k15, '#26a69a')}
      </div>
      ${arbBlock(arb)}
      <div class="ud-foot">The two legs the live account locks: buy UP on the cheaper venue + DOWN on the dearer so one leg pays $1.00 at settle. Cost = price for 1 share.</div>`;
  }

  if (!acc) {
    if (banner) banner.innerHTML = '';
    if (bal) bal.innerHTML = '<div class="empty">live account feed not running — start dashboard/refresh_live5m.py</div>';
    tickCountdowns();
    return;
  }

  if (banner) {
    banner.className = '';
    let bhtml = '';
    // Highest priority: a NAKED leg (one venue holding without the other). The
    // execution layer auto-flattens these, but if one ever slips through, scream.
    const naked = acc.naked_alert || acc.naked_live;
    if (naked) {
      const d = acc.naked_alert
        ? `window ${String(acc.naked_alert.window || '').slice(11, 16)} — Kalshi ${acc.naked_alert.kalshi} vs Poly ${acc.naked_alert.poly} contracts`
        : (acc.naked_live && acc.naked_live.detail) || 'one leg unmatched';
      bhtml += `<div class="live-banner stop" style="margin-bottom:6px;animation:none">
          &#9888; <b>NAKED POSITION DETECTED</b> — ${d}. A leg is UNHEDGED (directional risk). Flatten it immediately.</div>`;
    }
    if (acc.killed) {
      bhtml += '<div class="live-banner stop">&#9632; KILL SWITCH ON — no new orders (remove journal/STOP to resume)</div>';
    } else if (acc.dry_run) {
      bhtml += '<div class="live-banner dry">&#9888; DRY-RUN — orders are SIMULATED (no real money). Balances below are LIVE where credentials are present. Set DRY_RUN=false to place real orders.</div>';
    } else {
      bhtml += '<div class="live-banner real">&#9679; LIVE — REAL MONEY. Orders are sent to Polymarket + Kalshi. Every fill auto-reconciles so a leg is never left naked.</div>';
    }
    banner.innerHTML = bhtml;
  }

  const killBtn = $('killBtn');
  if (killBtn) {
    if (acc.killed) {
      killBtn.innerHTML = '&#9654; Resume trading';
      killBtn.style.color = 'var(--green)';
      killBtn.style.borderColor = 'var(--green)';
    } else {
      killBtn.innerHTML = '&#9211; Stop trading';
      killBtn.style.color = 'var(--red)';
      killBtn.style.borderColor = 'var(--red)';
    }
  }

  const fmtBal = (v) => (v == null ? '—' : '$' + Number(v).toFixed(2));
  const cap = acc.max_notional || 10;
  const srcTag = (real, note) => real
    ? `<span style="color:var(--green)">&#9679; live${note ? ' ' + note : ''}</span>`
    : `<span style="color:var(--muted)">&#9888; sim${note ? ' &middot; ' + note : ''}</span>`;
  // Per-lock spend is capped by the SMALLER funded account (and the $10 cap),
  // since each venue holds one leg.
  const pb = acc.poly_balance, kb = acc.kalshi_balance;
  const perLock = [pb, kb, cap].filter((x) => x != null).reduce((m, x) => Math.min(m, x), cap);
  const bothFunded = pb > 0.5 && kb > 0.5;
  if (bal) {
    bal.innerHTML = `<div class="cmp">
        <div class="cmp-col"><div class="cmp-h">Polymarket (pUSD)</div>
          <div class="cmp-big" style="color:#b07cff">${fmtBal(acc.poly_balance)}</div>
          <div class="cmp-sub">${srcTag(acc.poly_real, acc.poly_note)} &middot; cap $${cap.toFixed(0)}/lock</div></div>
        <div class="cmp-col"><div class="cmp-h">Kalshi</div>
          <div class="cmp-big" style="color:var(--green)">${fmtBal(acc.kalshi_balance)}</div>
          <div class="cmp-sub">${srcTag(acc.kalshi_real, acc.kalshi_note)} &middot; cap $${cap.toFixed(0)}/lock</div></div>
        <div class="cmp-col"><div class="cmp-h">Locks recorded</div>
          <div class="cmp-big">${acc.n_locks}</div>
          <div class="cmp-sub">${acc.pairs_total} pairs total</div></div>
      </div>
      <div class="ud-foot" style="margin-top:10px">
        ${bothFunded
          ? `&#9679; Both legs funded &middot; <b>max ~$${perLock.toFixed(2)}/lock</b> (capped by the smaller account)`
          : '&#9888; One leg unfunded &mdash; a cross-venue lock needs USDC/pUSD on BOTH venues'}</div>`;
  }

  const venueTag = (v) => v === 'Kalshi'
    ? '<span style="color:var(--green)">Kalshi</span>'
    : '<span style="color:#b07cff">Polymarket</span>';
  const pct = (v) => (v == null ? '—' : Math.round(Number(v) * 100) + '¢');
  const usd = (v) => (v == null ? '—' : '$' + Number(v).toFixed(2));

  const signed = (v) => (v == null ? '—'
    : (v >= 0 ? '+$' : '−$') + Math.abs(Number(v)).toFixed(2));
  const posBody = $('livePositionsBody');
  if (posBody) {
    const ps = acc.positions || [];
    // A meaningful live leg = >=1 share AND >=25c value (ignore unsellable dust).
    const meaningful = (p) => (p.size || 0) >= 1 && (p.value || 0) >= 0.25 && !p.redeemable;
    const liveK = ps.filter((p) => p.venue === 'Kalshi' && meaningful(p)).length;
    const liveP = ps.filter((p) => p.venue === 'Polymarket' && meaningful(p)).length;
    if (!ps.length) {
      posBody.innerHTML = '<div class="empty">no open positions — flat on both venues</div>';
    } else {
      const rows = ps.map((p) => {
        const cost = (p.size != null && p.avg != null) ? p.size * p.avg : null;
        const pnl = (p.value != null && cost != null) ? p.value - cost : null;
        const pnlCol = pnl == null ? 'var(--muted)' : (pnl >= 0 ? 'var(--green)' : 'var(--red)');
        // Hedge state: settled/dust is fine; a meaningful live leg with no
        // opposite venue is NAKED.
        let hedge;
        if (p.redeemable || !meaningful(p)) {
          hedge = '<span style="color:var(--muted)">settled</span>';
        } else {
          const otherSide = p.venue === 'Kalshi' ? liveP : liveK;
          hedge = otherSide > 0
            ? '<span style="color:var(--green)">&#9679; hedged</span>'
            : '<span style="color:var(--red);font-weight:700">&#9888; NAKED</span>';
        }
        const red = p.redeemable ? ' <span style="color:var(--accent)">REDEEMABLE</span>' : '';
        return `<tr><td>${venueTag(p.venue)}</td>
          <td>${String(p.title || '').slice(0, 40)}</td>
          <td>${p.outcome || ''}</td><td>${p.size != null ? Number(p.size).toFixed(0) : '—'}</td>
          <td>${pct(p.avg)}</td><td>${pct(p.cur)}</td>
          <td>${usd(cost)}</td>
          <td><b>${usd(p.value)}</b>${red}</td>
          <td style="color:${pnlCol};font-weight:700">${signed(pnl)}</td>
          <td>${hedge}</td></tr>`;
      }).join('');
      posBody.innerHTML = `<table class="pm-tbl"><thead><tr>
        <th>Venue</th><th>Market</th><th>Side</th><th>Size</th><th>Avg</th><th>Cur</th>
        <th>Cost</th><th>Value</th><th>P&amp;L</th><th>Hedge</th>
        </tr></thead><tbody>${rows}</tbody></table>
        <div class="ud-foot">Value &amp; P&amp;L update live. <b>Hedge</b> shows whether each live leg is offset on the other venue — a red NAKED flag means directional risk that should be flattened.</div>`;
    }
  }

  const ordBody = $('liveOrdersBody');
  if (ordBody) {
    const os = acc.orders || [];
    if (!os.length) {
      ordBody.innerHTML = '<div class="empty">no open orders (none resting)</div>';
    } else {
      const rows = os.map((o) => `<tr><td>${venueTag(o.venue)}</td>
        <td>${o.side || ''}</td><td>${pct(o.price)}</td>
        <td>${o.size != null ? Number(o.size).toFixed(2) : '—'}</td>
        <td>${o.filled != null ? Number(o.filled).toFixed(2) : '—'}</td>
        <td>${String(o.market || '').slice(0, 28)}</td></tr>`).join('');
      ordBody.innerHTML = `<table class="pm-tbl"><thead><tr>
        <th>Venue</th><th>Side</th><th>Price</th><th>Size</th><th>Filled</th><th>Market</th>
        </tr></thead><tbody>${rows}</tbody></table>`;
    }
  }

  const lb = $('liveLocksBody');
  if (lb) {
    const locks = acc.locks || [];
    if (!locks.length) {
      lb.innerHTML = '<div class="empty">no locks yet — the live account only enters when net edge after fees is positive AND both legs fill at quoted prices</div>';
    } else {
      const rows = locks.map((l) => {
        const kl = l.kalshi ? `${l.kalshi.side} Kalshi@${Math.round(l.kalshi.px * 100)}&cent;` : '';
        const pl = l.poly ? `${l.poly.side} Poly@${Math.round(l.poly.px * 100)}&cent;` : '';
        const lockc = Math.round((l.lock_cost || 0) * 100);
        const mode = l.dry
          ? '<span style="color:var(--accent);font-weight:700">DRY</span>'
          : '<span style="color:var(--red);font-weight:700">LIVE</span>';
        const purpose = `Cross-venue 15m lock: BUY ${kl} + ${pl} = ${lockc}&cent; ` +
          `&rarr; collect $1.00/pair at settlement (one leg always wins). ~${l.gross_cents}&cent; gross.`;
        // Status + result, mirroring the paper account's order history.
        const settled = l.status === 'settled';
        const status = settled
          ? '<span style="color:var(--green);font-weight:700">SETTLED &middot; WON</span>'
          : '<span style="color:var(--accent)">OPEN</span>';
        const pnl = l.pnl;
        const pnlCol = pnl == null ? 'var(--muted)' : (pnl >= 0 ? 'var(--green)' : 'var(--red)');
        const pnlStr = pnl == null ? '—' : ((pnl >= 0 ? '+$' : '−$') + Math.abs(pnl).toFixed(2));
        return `<tr>
            <td>${(l.opened || '').slice(11, 19)}</td>
            <td>${l.kalshi ? l.kalshi.side : ''}/${l.poly ? l.poly.side : ''} &times;${l.pairs}
                <br><span class="pm-purpose">${kl} + ${pl}</span></td>
            <td class="pm-purpose">${purpose}</td>
            <td>$${(l.cost != null ? l.cost : 0).toFixed(2)}</td>
            <td style="color:var(--red)">$${(l.fee != null ? l.fee : 0).toFixed(2)}</td>
            <td>${status}<br><span class="pm-purpose">settles ${(l.window || '').slice(11, 16)}</span></td>
            <td style="color:${pnlCol};font-weight:700">${pnlStr}</td>
            <td>${mode}</td>
          </tr>`;
      }).join('');
      const realized = acc.realized_pnl;
      const rCol = (realized || 0) >= 0 ? 'var(--green)' : 'var(--red)';
      const summary = realized != null
        ? `<div class="ud-foot">Realized P&amp;L (settled locks): <b style="color:${rCol}">${(realized >= 0 ? '+$' : '−$') + Math.abs(realized).toFixed(2)}</b> &middot; a lock pays $1.00/pair at settlement (one leg always wins). LIVE locks carry basis risk; DRY are simulated.</div>`
        : '';
      lb.innerHTML = `<table class="pm-tbl"><thead><tr>
          <th>Opened</th><th>Trade</th><th>Purpose &mdash; why this lock</th><th>Stake</th><th>Fee</th><th>Status &amp; Result</th><th>P&amp;L</th><th>Mode</th>
        </tr></thead><tbody>${rows}</tbody></table>${summary}`;
    }
  }
  tickCountdowns();
}

function renderBets(bets, spot) {
  const body = $('betsBody');
  bets = bets || {};
  const poly = (bets.polymarket || {}).btc_cdf;
  const kal = (bets.kalshi || {}).btc_cdf;

  let html = renderBetVenue('Polymarket — ' + ((poly && poly.title) || 'BTC'), poly, spot);

  if (kal && kal.levels && kal.levels.length) {
    html += renderBetVenue('Kalshi — BTC daily', kal, spot);
  } else {
    const note = (bets.kalshi || {}).note;
    html += `<div style="font-size:11px;color:var(--muted)"><b style="color:var(--text)">KALSHI</b><br>${
      note || 'no live quotes'
    }</div>`;
  }

  const iran = (bets.polymarket || {}).iran_deal;
  if (iran && iran.prob_yes != null) {
    const pct = (iran.prob_yes * 100).toFixed(0);
    html =
      `<div style="font-size:11px;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid var(--border)">
         <span style="color:var(--muted)">Iran peace deal</span>
         <span style="float:right;font-weight:700;color:var(--accent)">${pct}% YES</span>
         <div style="color:var(--muted);font-size:10px;margin-top:2px">risk-on if YES &rarr; gold&darr; / BTC&uarr;</div>
       </div>` + html;
  }

  body.innerHTML = html || '<div class="empty">no odds yet</div>';
}

function renderSignals(bets) {
  const body = $('signalsBody');
  if (!body) return;
  bets = bets || {};
  const sig = bets.signals || {};
  const fund = (bets.funding || {}).positioning;
  const xspread = (bets.funding || {}).cross_exchange && (bets.funding || {}).cross_exchange.spread;
  let html = '';

  // 1) 5-min stale-book model vs market
  const ud = sig.updown_5m;
  if (ud && ud.market_up_prob != null) {
    const mkt = Math.round(ud.market_up_prob * 100);
    const mdl = ud.model_up_prob != null ? Math.round(ud.model_up_prob * 100) : null;
    const flag = ud.flag && ud.flag !== 'none' ? ud.flag : null;
    const flagHtml = flag
      ? `<span style="color:var(--accent);font-weight:700">&#9888; ${flag.replace('_', ' ')}</span>`
      : '<span style="color:var(--muted)">no edge</span>';
    html += `<div style="font-size:11px;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid var(--border)">
               <div style="font-weight:700;color:var(--text)">5-min model vs market</div>
               <div class="row"><span class="k">market UP</span><span class="v">${mkt}%</span></div>
               ${mdl != null ? `<div class="row"><span class="k">model UP (Bachelier)</span><span class="v">${mdl}%</span></div>` : ''}
               ${ud.edge_up != null ? `<div class="row"><span class="k">edge</span><span class="v">${(ud.edge_up * 100).toFixed(1)}%</span></div>` : ''}
               <div style="margin-top:3px">${flagHtml}</div>
             </div>`;
  }

  // 2) Funding / positioning
  if (fund && fund.score != null) {
    const s = fund.score;
    const col = s > 0.5 ? 'var(--red)' : s < -0.5 ? 'var(--green)' : 'var(--muted)';
    html += `<div style="font-size:11px;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid var(--border)">
               <div style="font-weight:700;color:var(--text)">Perp funding / positioning</div>
               <div class="row"><span class="k">squeeze score</span><span class="v" style="color:${col}">${s.toFixed(2)}</span></div>
               <div style="color:var(--muted);font-size:10px;margin-top:2px">${fund.label}</div>
               ${xspread ? `<div style="color:var(--muted);font-size:10px">x-exch spread ${xspread.high_venue}&minus;${xspread.low_venue}: $${fmt(xspread.spread_usd, 0)} (${xspread.spread_bps}bps)</div>` : ''}
             </div>`;
  }

  // 3) Cross-venue PM divergences (watch)
  const cv = sig.cross_venue_pm;
  if (cv && cv.divergences && cv.divergences.length) {
    const rows = cv.divergences
      .map((d) => `<div class="row"><span class="k">$${(d.strike / 1000).toFixed(0)}k Poly ${(d.poly_prob * 100).toFixed(0)}% / Kalshi ${(d.kalshi_prob * 100).toFixed(0)}%</span>
                     <span class="v" style="color:var(--accent)">${(d.gross_gap * 100).toFixed(0)}c</span></div>`)
      .join('');
    html += `<div style="font-size:11px">
               <div style="font-weight:700;color:var(--text)">Cross-venue divergence <span style="color:var(--muted);font-weight:400">(WATCH &mdash; basis risk)</span></div>
               ${rows}
             </div>`;
  } else if (cv) {
    html += `<div style="font-size:10px;color:var(--muted)">cross-venue: no divergence past threshold (${cv.matched_strikes || 0} matched strikes)</div>`;
  }

  body.innerHTML = html || '<div class="empty">no signals yet</div>';
}

/* ---------- refresh loop ---------- */

async function refresh() {
  if (!window.api) {
    $('updated').textContent = 'preload bridge missing';
    return;
  }
  const d = await window.api.readData();
  levels = await window.api.readLevels();
  renderLevels();
  if (!d) {
    $('updated').textContent = 'data.json not found — run refresh_data.py';
    return;
  }
  lastData = d;
  const btc = d.symbols && d.symbols.BTCUSDT && d.symbols.BTCUSDT.price;
  lastSpot = (btc && btc.mid) || lastSpot;
  renderHeader(d);
  renderPosition(d);
  renderOrders(d);
  renderHistory(d);
  renderBets(betsData || d.bets, lastSpot);
  if (series) {
    setCandles(currentTf);
    redrawPriceLines();
    redrawPositionMarkers();
  }
}

document.querySelectorAll('.tf-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tf-btn').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    currentTf = btn.dataset.tf;
    setCandles(currentTf, true);
    redrawPriceLines();
    redrawPositionMarkers();
  });
});

document.querySelectorAll('.sym-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.sym-btn').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    currentSymbol = btn.dataset.sym;
    renderLevels();
    if (lastData) {
      renderHeader(lastData);
      setCandles(currentTf, true);
      redrawPriceLines();
      redrawPositionMarkers();
    }
  });
});

// Tab switching: Chart (chart + sidebar) vs Markets & Bets (full window)
document.querySelectorAll('.tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    const view = btn.dataset.view;
    document.querySelectorAll('.tab').forEach((b) => b.classList.toggle('active', b === btn));
    document.getElementById('view-chart').classList.toggle('active', view === 'chart');
    document.getElementById('view-history').classList.toggle('active', view === 'history');
    document.getElementById('view-markets').classList.toggle('active', view === 'markets');
    document.getElementById('view-live').classList.toggle('active', view === 'live');
    if (view === 'chart' && chart) {
      // The chart may have been sized while hidden — refit on return.
      requestAnimationFrame(() => {
        const el = $('chart');
        chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
        setCandles(currentTf, true);
        redrawPriceLines();
        redrawPositionMarkers();
      });
    } else if (view === 'history') {
      if (lastData) renderHistory(lastData);
    } else if (view === 'markets') {
      renderBets(betsData || (lastData && lastData.bets), lastSpot);
      renderSignals(betsData);
      renderLive5m();
      renderCompare();
      if (live5mData) renderPM(live5mData.pm);
      if (lastData) renderPosition(lastData);
    } else if (view === 'live') {
      renderLiveAccount();
    }
  });
});

// Kill-switch button: toggles journal/STOP via the main process. The same file
// halts livearb.py's loop, so this genuinely stops/resumes live order placement.
const killBtnEl = document.getElementById('killBtn');
if (killBtnEl) {
  killBtnEl.addEventListener('click', async () => {
    if (!window.api || !window.api.setKill) return;
    const currentlyKilled = !!(live5mData && live5mData.live && live5mData.live.killed);
    const turnOn = !currentlyKilled;
    killBtnEl.disabled = true;
    try {
      await window.api.setKill(turnOn);
      if (live5mData && live5mData.live) live5mData.live.killed = turnOn; // optimistic
      renderLiveAccount();
      await refreshLive5m();
    } finally {
      killBtnEl.disabled = false;
    }
  });
}

try {
  createChart();
} catch (e) {
  // chart library failed to load — keep stats panels alive
  $('chart').innerHTML =
    '<div style="padding:30px;color:#787b86">chart failed: ' + e.message + '</div>';
}
// Fast, broker-free poll of bets.json so the 5-min market price stays live
// without waiting on the 30s full refresh. Falls back silently if absent.
async function refreshBets() {
  if (!window.api || !window.api.readBets) return;
  try {
    const b = await window.api.readBets();
    if (b) {
      betsData = b;
      renderBets(betsData, lastSpot);
      renderSignals(betsData);
      renderLive5m(); // refresh the Kalshi hourly side
      renderCompare();
    }
  } catch (e) {
    /* keep last good render */
  }
}

// Per-second live 5-min bet price (Polymarket-style cost UI).
async function refreshLive5m() {
  if (!window.api || !window.api.readLive5m) return;
  try {
    const l = await window.api.readLive5m();
    if (l) {
      live5mData = l;
      renderLive5m();
      renderCompare(); // tick spot (and the comparison) every second
      renderPM(l.pm);
      renderLiveAccount();
    }
  } catch (e) {
    /* keep last good render */
  }
}

// Fast real-time path: live.json (price + equity + floating PnL) every ~2s.
// Moves the last chart candle with the live mid and updates PnL/equity/progress
// without waiting for the 30s full refresh. The slow refresh re-syncs candle
// history + history tabs; this just keeps the tape and PnL alive.
async function refreshLive() {
  if (!window.api || !window.api.readLive) return;
  let lv;
  try { lv = await window.api.readLive(); } catch (e) { return; }
  if (!lv || !lastData) return;
  lastData.account = Object.assign({}, lastData.account, lv.account || {});
  if (lv.positions) lastData.positions = lv.positions;
  if (lv.orders) lastData.orders = lv.orders;
  if (lv.price) {
    lastData.price = Object.assign({}, lastData.price, lv.price);
    if (lastData.symbols && lastData.symbols.XAUUSD)
      lastData.symbols.XAUUSD.price = lastData.price;
  }
  lastData.generated_at = lv.t || lastData.generated_at;
  try {
    renderHeader(lastData);
    renderPosition(lastData);
    renderOrders(lastData);
  } catch (e) { /* keep last good render */ }

  // Live candle: push the live mid into the last bar so the chart ticks in real time.
  if (series && currentSymbol === 'XAUUSD' && lv.price && lv.price.mid != null && lastBars.length) {
    const last = lastBars[lastBars.length - 1];
    const m = lv.price.mid;
    const upd = { time: last.time, open: last.open,
                  high: Math.max(last.high, m), low: Math.min(last.low, m), close: m };
    lastBars[lastBars.length - 1] = upd;
    try { series.update(upd); } catch (e) { /* series not ready */ }
  }
}

refresh();
refreshBets();
refreshLive5m();
refreshLive();
setInterval(refresh, REFRESH_MS);
setInterval(refreshBets, BETS_REFRESH_MS);
setInterval(refreshLive5m, 1000); // tick the bet price every second
setInterval(refreshLive, 2000); // real-time chart candle + PnL/equity
setInterval(tickCountdowns, 1000); // smooth per-second countdown
