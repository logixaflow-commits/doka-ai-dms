const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('dokaDesktop', {
  isDesktop: true,
  selectDirectory: () => ipcRenderer.invoke('dialog:openDirectory'),
  selectFiles: () => ipcRenderer.invoke('dialog:openFiles'),
  getWorkspacePaths: () => ipcRenderer.invoke('workspace:getPaths'),
  showNotification: (title, body) => ipcRenderer.invoke('notification:show', { title, body }),
  openExternalUrl: (url) => ipcRenderer.invoke('shell:openExternal', url)
});
