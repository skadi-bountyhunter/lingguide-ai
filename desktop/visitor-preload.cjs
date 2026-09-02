'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('lingguideDesktop', Object.freeze({
  runtime: 'desktop',
  openAdmin: () => ipcRenderer.invoke('desktop:open-admin'),
}));
