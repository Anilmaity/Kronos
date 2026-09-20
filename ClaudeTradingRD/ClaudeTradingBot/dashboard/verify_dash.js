// Verification harness for the trade-history + chart-marker work.
// Captures the Chart tab (position marker + ENTRY/SL/TP lines on the live SELL
// position) and the Trade History tab, and reports any renderer console errors.
// Run: node_modules/.bin/electron verify_dash.js
const { app, BrowserWindow, ipcMain } = require('electron');
const fs = require('fs');
const path = require('path');

const READABLE = new Set(['data.json', 'levels.json', 'bets.json', 'live5m.json', 'live.json']);
ipcMain.handle('read-json', (_e, f) => {
  if (!READABLE.has(f)) return null;
  try { return JSON.parse(fs.readFileSync(path.join(__dirname, f), 'utf-8')); }
  catch { return null; }
});
ipcMain.handle('set-kill', () => ({ ok: true }));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

app.whenReady().then(async () => {
  const win = new BrowserWindow({
    width: 1500, height: 1050, show: false, backgroundColor: '#131722',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, nodeIntegration: false,
    },
  });
  win.removeMenu();

  const errors = [];
  win.webContents.on('console-message', (_e, level, message) => {
    if (level >= 2) errors.push(message); // 2=warning,3=error
  });

  await win.loadFile('index.html');
  await sleep(2500); // first refresh() populates the chart + history from data.json

  // --- Chart tab: the default view. Confirm the live position is on the chart. ---
  await win.webContents.executeJavaScript(
    `document.querySelector('[data-tf="M15"]').click(); true;`); // tighter TF -> marker visible
  await sleep(1200);
  fs.writeFileSync(path.join(__dirname, 'verify_chart_shot.png'),
                   (await win.webContents.capturePage()).toPNG());

  // --- Trade History tab. ---
  await win.webContents.executeJavaScript(
    `document.querySelector('[data-view="history"]').click(); true;`);
  await sleep(800);
  const histStats = await win.webContents.executeJavaScript(`(() => {
    const rows = (sel) => document.querySelectorAll(sel + ' table.pm-tbl tbody tr').length;
    return {
      xauRows: rows('#histXauBody'),
      btcRows: rows('#histBtcBody'),
      xauSummary: (document.getElementById('histXauSummary')||{}).innerText || '',
      btcSummary: (document.getElementById('histBtcSummary')||{}).innerText || '',
    };
  })();`);
  fs.writeFileSync(path.join(__dirname, 'verify_history_shot.png'),
                   (await win.webContents.capturePage()).toPNG());

  // --- Position-on-chart sanity (compute expected markers from the same data). ---
  const posInfo = await win.webContents.executeJavaScript(`(() => {
    const d = lastData || {};
    const ps = (d.positions || []).filter(p => !p.symbol || p.symbol === 'XAUUSD');
    return { count: ps.length, sample: ps[0] || null,
             markerFnExists: typeof redrawPositionMarkers === 'function' };
  })();`);

  console.log('HISTORY_STATS ' + JSON.stringify(histStats));
  console.log('POSITION_INFO ' + JSON.stringify(posInfo));
  console.log('CONSOLE_ERRORS ' + JSON.stringify(errors));
  console.log('shots: verify_chart_shot.png, verify_history_shot.png');
  app.quit();
});
