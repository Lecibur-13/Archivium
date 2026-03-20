"use strict";
const electron = require("electron");
electron.contextBridge.exposeInMainWorld("api", {
  selectFolder: () => electron.ipcRenderer.invoke("dialog:selectFolder"),
  loadConfig: () => electron.ipcRenderer.invoke("config:load"),
  saveConfig: (config) => electron.ipcRenderer.invoke("config:save", config),
  startTransfer: (options) => electron.ipcRenderer.invoke("transfer:start", options),
  cancelTransfer: () => electron.ipcRenderer.send("transfer:cancel"),
  openPath: (p) => electron.ipcRenderer.invoke("shell:openPath", p),
  onProgress: (callback) => {
    const handler = (_, data) => callback(data);
    electron.ipcRenderer.on("transfer:progress", handler);
    return () => electron.ipcRenderer.removeListener("transfer:progress", handler);
  },
  onLog: (callback) => {
    const handler = (_, msg) => callback(msg);
    electron.ipcRenderer.on("transfer:log", handler);
    return () => electron.ipcRenderer.removeListener("transfer:log", handler);
  },
  onComplete: (callback) => {
    const handler = (_, result) => callback(result);
    electron.ipcRenderer.on("transfer:complete", handler);
    return () => electron.ipcRenderer.removeListener("transfer:complete", handler);
  }
});
