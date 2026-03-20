import { useState, useEffect, useRef } from 'react'
import {
  FolderOpen, Settings, ArrowRight, X, Check,
  Loader2, ChevronDown, ChevronUp, MoveRight, Copy
} from 'lucide-react'
import SettingsModal from './components/SettingsModal'
import ActivityLog from './components/ActivityLog'
import type { Config, ProgressData, TransferResult, AppState } from './types'

// ─── FolderPicker ─────────────────────────────────────────────────────────────

function FolderPicker({
  label,
  subtitle,
  value,
  onChange,
  onBrowse,
  disabled
}: {
  label: string
  subtitle: string
  value: string
  onChange: (v: string) => void
  onBrowse: () => void
  disabled: boolean
}) {
  return (
    <div className="group">
      <div className="mb-1.5">
        <p className="text-[13px] font-medium text-zinc-200">{label}</p>
        <p className="text-[11px] text-zinc-500">{subtitle}</p>
      </div>
      <div className="flex items-center gap-2">
        <div className={`
          flex-1 flex items-center h-9 px-3 rounded-lg border text-[13px] font-mono
          transition-colors truncate
          ${disabled
            ? 'bg-zinc-900/40 border-zinc-800 text-zinc-500 cursor-not-allowed'
            : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700 text-zinc-300 cursor-text focus-within:border-zinc-600'}
        `}>
          <input
            type="text"
            value={value}
            onChange={e => onChange(e.target.value)}
            disabled={disabled}
            placeholder="Select a folder..."
            className="w-full bg-transparent outline-none text-zinc-300 placeholder:text-zinc-600 disabled:cursor-not-allowed"
          />
        </div>
        <button
          onClick={onBrowse}
          disabled={disabled}
          className="flex items-center justify-center h-9 w-9 rounded-lg border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 hover:border-zinc-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-zinc-400 hover:text-zinc-200"
        >
          <FolderOpen size={15} />
        </button>
      </div>
    </div>
  )
}

// ─── Progress Bar ─────────────────────────────────────────────────────────────

function ProgressSection({ progress }: { progress: ProgressData }) {
  const pct = progress.total > 0
    ? Math.round((progress.transferred / progress.total) * 100)
    : 0

  const fmtBytes = (b: number) => {
    if (b < 1024) return `${b} B`
    if (b < 1024 ** 2) return `${(b / 1024).toFixed(1)} KB`
    if (b < 1024 ** 3) return `${(b / 1024 ** 2).toFixed(1)} MB`
    return `${(b / 1024 ** 3).toFixed(2)} GB`
  }

  return (
    <div className="space-y-2 py-1">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-zinc-500 truncate max-w-[55%]">
          {progress.currentFile}
        </span>
        <span className="text-[11px] text-zinc-500 shrink-0 ml-2">
          {progress.transferred}/{progress.total} · {fmtBytes(progress.bytesTransferred)} · {pct}%
        </span>
      </div>
      <div className="h-[3px] w-full bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all duration-200 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex gap-1.5">
        {(['JPEG', 'RAW', 'VIDEO'] as const).map(t => (
          <span
            key={t}
            className={`text-[10px] px-1.5 py-0.5 rounded font-medium
              ${progress.type === t
                ? 'bg-blue-500/15 text-blue-400'
                : 'bg-zinc-800/60 text-zinc-600'
              }`}
          >
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}

// ─── App ─────────────────────────────────────────────────────────────────────

export default function App() {
  const [src, setSrc] = useState('')
  const [dest, setDest] = useState('')
  const [moveMode, setMoveMode] = useState(false)
  const [appState, setAppState] = useState<AppState>('idle')
  const [progress, setProgress] = useState<ProgressData | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [showLog, setShowLog] = useState(false)
  const [config, setConfig] = useState<Config>({
    defaultDest: '',
    theme: 'dark',
    organizeMode: 'classic'
  })
  const [showSettings, setShowSettings] = useState(false)
  const [lastResult, setLastResult] = useState<TransferResult | null>(null)
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    window.api.loadConfig().then(cfg => {
      setConfig(cfg)
      if (cfg.defaultDest) setDest(cfg.defaultDest)
    })

    const offProgress = window.api.onProgress(setProgress)
    const offLog = window.api.onLog(msg => setLogs(prev => [...prev, msg]))
    const offComplete = window.api.onComplete(result => {
      setLastResult(result)
      setAppState(result.cancelled ? 'cancelled' : result.errors > 0 ? 'error' : 'done')
      resetTimer.current = setTimeout(() => setAppState('idle'), 3500)
    })

    return () => {
      offProgress()
      offLog()
      offComplete()
      if (resetTimer.current) clearTimeout(resetTimer.current)
    }
  }, [])

  const selectSrc = async () => {
    const folder = await window.api.selectFolder()
    if (folder) setSrc(folder)
  }

  const selectDest = async () => {
    const folder = await window.api.selectFolder()
    if (folder) {
      setDest(folder)
      await window.api.saveConfig({ ...config, defaultDest: folder })
    }
  }

  const handleOrganize = async () => {
    if (appState === 'transferring') {
      window.api.cancelTransfer()
      return
    }
    if (!src || !dest) return

    if (resetTimer.current) clearTimeout(resetTimer.current)
    setAppState('transferring')
    setProgress(null)
    setLogs([])

    await window.api.startTransfer({
      src,
      dest,
      move: moveMode,
      mode: config.organizeMode
    })
  }

  const handleSaveConfig = async (newConfig: Config) => {
    setConfig(newConfig)
    await window.api.saveConfig(newConfig)
  }

  const isTransferring = appState === 'transferring'
  const canOrganize = !!src && !!dest && (appState === 'idle' || appState === 'transferring')

  return (
    <div className="h-screen flex flex-col bg-[#0c0c0e] select-none overflow-hidden">

      {/* ── Header ── */}
      <header className="flex items-center justify-between px-5 py-3.5 border-b border-zinc-900 drag-region">
        <div className="flex items-center gap-2.5 no-drag">
          <div className="w-2 h-2 rounded-full bg-blue-500 shadow-[0_0_6px_theme(colors.blue.500)]" />
          <span className="text-[15px] font-semibold tracking-tight text-zinc-100">Archivium</span>
        </div>
        <button
          onClick={() => setShowSettings(true)}
          className="no-drag p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/60 transition-colors"
        >
          <Settings size={15} />
        </button>
      </header>

      {/* ── Main ── */}
      <main className="flex-1 flex flex-col gap-4 px-5 py-4 overflow-y-auto min-h-0">

        {/* Destination */}
        <FolderPicker
          label="Destination"
          subtitle="Default output folder for organized media"
          value={dest}
          onChange={setDest}
          onBrowse={selectDest}
          disabled={isTransferring}
        />

        {/* Source */}
        <FolderPicker
          label="Source"
          subtitle="SD card or folder to import from"
          value={src}
          onChange={setSrc}
          onBrowse={selectSrc}
          disabled={isTransferring}
        />

        {/* Divider */}
        <div className="border-t border-zinc-900" />

        {/* Transfer mode */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => !isTransferring && setMoveMode(false)}
            className={`flex items-center gap-2 text-[12px] font-medium px-3 py-1.5 rounded-md border transition-all
              ${!moveMode
                ? 'border-blue-500/40 bg-blue-500/10 text-blue-400'
                : 'border-zinc-800 bg-transparent text-zinc-500 hover:text-zinc-300 hover:border-zinc-700'
              } ${isTransferring ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
          >
            <Copy size={12} />
            Copy
          </button>
          <button
            onClick={() => !isTransferring && setMoveMode(true)}
            className={`flex items-center gap-2 text-[12px] font-medium px-3 py-1.5 rounded-md border transition-all
              ${moveMode
                ? 'border-orange-500/40 bg-orange-500/10 text-orange-400'
                : 'border-zinc-800 bg-transparent text-zinc-500 hover:text-zinc-300 hover:border-zinc-700'
              } ${isTransferring ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
          >
            <MoveRight size={12} />
            Move
          </button>
          {moveMode && (
            <span className="text-[11px] text-zinc-600">
              Originals will be deleted from source
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowLog(v => !v)}
            className="flex items-center gap-1.5 text-[12px] text-zinc-500 hover:text-zinc-300 transition-colors py-1"
          >
            {showLog ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            Activity log
          </button>

          <div className="flex-1" />

          <button
            onClick={handleOrganize}
            disabled={!canOrganize}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition-all duration-150
              ${isTransferring
                ? 'bg-zinc-900 border border-zinc-700 text-zinc-400 hover:text-red-400 hover:border-red-900/60 hover:bg-red-950/20'
                : appState === 'done'
                ? 'bg-emerald-950/50 border border-emerald-800/50 text-emerald-400 cursor-default'
                : appState === 'cancelled'
                ? 'bg-zinc-900 border border-zinc-700 text-zinc-400 cursor-default'
                : appState === 'error'
                ? 'bg-red-950/30 border border-red-900/40 text-red-400'
                : 'bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_12px_theme(colors.blue.600)/30] disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none'
              }
            `}
          >
            {isTransferring && <Loader2 size={13} className="animate-spin" />}
            {appState === 'done' && <Check size={13} />}
            {appState === 'idle' && <ArrowRight size={13} />}
            {(appState === 'cancelled' || appState === 'error') && <X size={13} />}

            {isTransferring
              ? 'Cancel'
              : appState === 'done'
              ? `Done · ${lastResult?.transferred ?? 0} files`
              : appState === 'cancelled'
              ? 'Cancelled'
              : appState === 'error'
              ? `${lastResult?.errors ?? 0} error${(lastResult?.errors ?? 0) !== 1 ? 's' : ''} · Retry?`
              : 'Organize Files'
            }
          </button>
        </div>

        {/* Progress */}
        {isTransferring && progress && (
          <ProgressSection progress={progress} />
        )}

        {/* Activity log */}
        {showLog && (
          <ActivityLog logs={logs} isTransferring={isTransferring} />
        )}
      </main>

      {/* Settings modal */}
      {showSettings && (
        <SettingsModal
          config={config}
          onSave={handleSaveConfig}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  )
}
