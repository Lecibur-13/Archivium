export interface Config {
  defaultDest: string
  theme: 'light' | 'dark' | 'system'
  organizeMode: 'classic' | 'date_then_type' | 'type_then_date'
}

export interface ProgressData {
  transferred: number
  total: number
  currentFile: string
  type: string
  bytesTransferred: number
  totalBytes: number
}

export interface TransferResult {
  transferred: number
  errors: number
  cancelled: boolean
}

export interface TransferOptions {
  src: string
  dest: string
  move: boolean
  mode: string
}

export type AppState = 'idle' | 'transferring' | 'done' | 'cancelled' | 'error'

declare global {
  interface Window {
    api: {
      selectFolder: () => Promise<string | null>
      loadConfig: () => Promise<Config>
      saveConfig: (config: Config) => Promise<void>
      startTransfer: (options: TransferOptions) => Promise<TransferResult>
      cancelTransfer: () => void
      openPath: (p: string) => Promise<void>
      onProgress: (callback: (data: ProgressData) => void) => () => void
      onLog: (callback: (msg: string) => void) => () => void
      onComplete: (callback: (result: TransferResult) => void) => () => void
    }
  }
}
