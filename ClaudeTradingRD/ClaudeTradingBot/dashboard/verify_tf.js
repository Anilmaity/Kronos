// Clicks each timeframe button and reports how many bars rendered + console errors.
const { app, BrowserWindow, ipcMain } = require('electron');
const fs = require('fs');
const path = require('path');
const READABLE = new Set(['data.json', 'levels.json', 'bets.json', 'live5m.json', 'live.json']);
ipcMain.handle('read-json', (_e, f) => {
  if (!READABLE.has(f)) return null;
  try { return JSON.parse(fs.readFileSync(path.join(__dirname, f), 'utf-8')); } catch { return null; }
});
ipcMain.handle('set-kill', () => ({ ok: true }));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

app.whenReady().then(async () => {
  const win = new BrowserWindow({ width: 1400, height: 900, show: false,
    webPreferences: { preload: path.join(__dirname, 'preload.js'),
                      contextIsolation: true, nodeIntegration: false } });
  win.removeMenu();
  const errors = [];
  win.webContents.on('console-message', (_e, lvl, msg) => { if (lvl >= 2) errors.push(msg); });
  await win.loadFile('index.html');
  await sleep(2500);
  const tfs = ['M1', 'M3', 'M5', 'M15', 'H1', 'H4', 'D'];
  const out = {};
  for (const tf of tfs) {
    await win.webContents.executeJavaScript(`document.querySelector('[data-tf="${tf}"]').click(); true;`);
    await sleep(500);
    out[tf] = await win.webContents.executeJavaScript(`(lastBars ? lastBars.length : -1)`);
  }
  console.log('TF_BARS ' + JSON.stringify(out));
  console.log('CONSOLE_ERRORS ' + JSON.stringify(errors));
  app.quit();
});
