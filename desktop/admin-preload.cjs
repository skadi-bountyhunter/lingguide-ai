'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('lingguideDesktop', Object.freeze({
  runtime: 'desktop',
  getAdminToken: () => ipcRenderer.invoke('desktop:get-admin-token'),
  openLogs: () => ipcRenderer.invoke('desktop:open-logs'),
  restartBackend: () => ipcRenderer.invoke('desktop:restart-backend'),
}));
