// Headless-ish screenshot harness: loads the dashboard with the real preload +
// IPC, switches to the Live Account tab, scrolls to the Locks card, and saves a
// PNG via Electron's capturePage(). Run: node_modules/.bin/electron screenshot_dash.js
const { app, BrowserWindow, ipcMain } = require('electron');
const fs = require('fs');
const path = require('path');

const READABLE = new Set(['data.json', 'levels.json', 'bets.json', 'live5m.json']);
ipcMain.handle('read-json', (_e, f) => {
  if (!READABLE.has(f)) return null;
  try { return JSON.parse(fs.readFileSync(path.join(__dirname, f), 'utf-8')); }
  catch { return null; }
});
ipcMain.handle('set-kill', () => ({ ok: true }));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

app.whenReady().then(async () => {
  const win = new BrowserWindow({
    width: 1500, height: 1050, show: true, backgroundColor: '#131722',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, nodeIntegration: false,
    },
  });
  win.removeMenu();
  await win.loadFile('index.html');
  await sleep(4000); // let the 1s live5m polls populate the account + locks
  // Switch to the Live Account tab.
  await win.webContents.executeJavaScript(
    `(document.querySelector('[data-view="live"]')||{click(){}}).click(); true;`);
  await sleep(1500);
  // Bring the Locks card into view.
  await win.webContents.executeJavaScript(
    `var c=document.getElementById('liveLocksCard'); if(c) c.scrollIntoView({block:'start'}); true;`);
  await sleep(1000);
  const img = await win.webContents.capturePage();
  fs.writeFileSync(path.join(__dirname, 'locks_shot.png'), img.toPNG());
  // Capture the top of the Live tab (banner + balances + positions).
  await win.webContents.executeJavaScript(
    `var b=document.getElementById('liveBanner'); if(b) b.scrollIntoView({block:'start'}); document.scrollingElement.scrollTop=0; true;`);
  await sleep(600);
  const bannerText = await win.webContents.executeJavaScript(
    `(document.getElementById('liveBanner')||{}).innerText || ''`);
  console.log('BANNER:', JSON.stringify(bannerText));
  const top = await win.webContents.capturePage();
  fs.writeFileSync(path.join(__dirname, 'live_top_shot.png'), top.toPNG());
  console.log('shots written');
  app.quit();
});
