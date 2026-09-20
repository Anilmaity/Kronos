const { app, BrowserWindow, ipcMain } = require('electron');
const fs = require('fs');
const path = require('path');

// File reads live in the main process: sandboxed preloads (Electron 20+
// default) have no fs access, so the renderer asks via IPC instead.
const READABLE = new Set(['data.json', 'levels.json', 'bets.json', 'live5m.json', 'live.json']);

function readJson(file) {
  if (!READABLE.has(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(path.join(__dirname, file), 'utf-8'));
  } catch (e) {
    return null;
  }
}

ipcMain.handle('read-json', (_event, file) => readJson(file));

// Kill switch: create/remove journal/STOP at the repo root (one level up from
// dashboard/). The same file is read by livearb.py's loop, so toggling it here
// genuinely halts/resumes live order placement.
ipcMain.handle('set-kill', (_event, on) => {
  try {
    const p = path.join(__dirname, '..', 'journal', 'STOP');
    if (on) {
      fs.mkdirSync(path.dirname(p), { recursive: true });
      fs.writeFileSync(p, '');
    } else if (fs.existsSync(p)) {
      fs.unlinkSync(p);
    }
    return { ok: true, killed: !!on };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
});

function createWindow() {
  const win = new BrowserWindow({
    width: 1500,
    height: 950,
    backgroundColor: '#131722',
    title: 'XAUUSD Paper Bot Dashboard',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });
  win.removeMenu();
  win.loadFile('index.html');
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
