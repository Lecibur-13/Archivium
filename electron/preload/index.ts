import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('api', {
  selectFolder: (): Promise<string | null> =>
    ipcRenderer.invoke('dialog:selectFolder'),

  loadConfig: () =>
    ipcRenderer.invoke('config:load'),

  saveConfig: (config: unknown) =>
    ipcRenderer.invoke('config:save', config),

  startTransfer: (options: unknown) =>
    ipcRenderer.invoke('transfer:start', options),

  cancelTransfer: () =>
    ipcRenderer.send('transfer:cancel'),

  openPath: (p: string) =>
    ipcRenderer.invoke('shell:openPath', p),

  onProgress: (callback: (data: unknown) => void) => {
    const handler = (_: unknown, data: unknown) => callback(data)
    ipcRenderer.on('transfer:progress', handler)
    return () => ipcRenderer.removeListener('transfer:progress', handler)
  },

  onLog: (callback: (msg: string) => void) => {
    const handler = (_: unknown, msg: string) => callback(msg)
    ipcRenderer.on('transfer:log', handler)
    return () => ipcRenderer.removeListener('transfer:log', handler)
  },

  onComplete: (callback: (result: unknown) => void) => {
    const handler = (_: unknown, result: unknown) => callback(result)
    ipcRenderer.on('transfer:complete', handler)
    return () => ipcRenderer.removeListener('transfer:complete', handler)
  }
})
