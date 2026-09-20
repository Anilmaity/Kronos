const { contextBridge, ipcRenderer } = require('electron');

// Sandboxed preload: no fs here — file reads go through main via IPC.
contextBridge.exposeInMainWorld('api', {
  readData: () => ipcRenderer.invoke('read-json', 'data.json'),
  readLevels: () => ipcRenderer.invoke('read-json', 'levels.json'),
  readBets: () => ipcRenderer.invoke('read-json', 'bets.json'),
  readLive5m: () => ipcRenderer.invoke('read-json', 'live5m.json'),
  readLive: () => ipcRenderer.invoke('read-json', 'live.json'),
  setKill: (on) => ipcRenderer.invoke('set-kill', !!on),
});
