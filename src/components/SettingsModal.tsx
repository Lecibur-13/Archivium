import { useState } from 'react'
import { X, Palette, FolderTree } from 'lucide-react'
import type { Config } from '../types'

interface Props {
  config: Config
  onSave: (config: Config) => Promise<void>
  onClose: () => void
}

const THEMES = [
  { value: 'dark', label: 'Dark' },
  { value: 'light', label: 'Light' },
  { value: 'system', label: 'System' }
] as const

const ORGANIZE_MODES = [
  {
    value: 'classic',
    label: 'Classic Session',
    description: 'Groups everything into a dated session folder · 2024-10-22_01/JPEG/'
  },
  {
    value: 'date_then_type',
    label: 'Chronological',
    description: 'Organized by capture date, then file type · 22-10-2024/JPEG/'
  },
  {
    value: 'type_then_date',
    label: 'Collections',
    description: 'Organized by file type, then capture date · JPEG/22-10-2024/'
  }
] as const

export default function SettingsModal({ config, onSave, onClose }: Props) {
  const [local, setLocal] = useState<Config>({ ...config })
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    await onSave(local)
    setSaving(false)
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="w-[440px] rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800/60">
          <span className="text-[14px] font-semibold text-zinc-100">Settings</span>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        <div className="p-5 space-y-6">

          {/* Appearance */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Palette size={13} className="text-zinc-500" />
              <span className="text-[12px] font-medium text-zinc-400 uppercase tracking-wider">
                Appearance
              </span>
            </div>
            <div className="flex gap-2">
              {THEMES.map(t => (
                <button
                  key={t.value}
                  onClick={() => setLocal(c => ({ ...c, theme: t.value }))}
                  className={`flex-1 py-2 rounded-lg text-[12px] font-medium border transition-all
                    ${local.theme === t.value
                      ? 'border-blue-500/50 bg-blue-500/10 text-blue-400'
                      : 'border-zinc-800 text-zinc-500 hover:text-zinc-300 hover:border-zinc-700'
                    }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </section>

          {/* Folder Organization */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <FolderTree size={13} className="text-zinc-500" />
              <span className="text-[12px] font-medium text-zinc-400 uppercase tracking-wider">
                Folder Structure
              </span>
            </div>
            <div className="space-y-2">
              {ORGANIZE_MODES.map(m => (
                <button
                  key={m.value}
                  onClick={() => setLocal(c => ({ ...c, organizeMode: m.value }))}
                  className={`w-full text-left px-4 py-3 rounded-lg border transition-all
                    ${local.organizeMode === m.value
                      ? 'border-blue-500/40 bg-blue-500/8 text-blue-400'
                      : 'border-zinc-800 hover:border-zinc-700 text-zinc-500 hover:text-zinc-300'
                    }`}
                >
                  <p className={`text-[13px] font-medium mb-0.5 ${local.organizeMode === m.value ? 'text-blue-300' : 'text-zinc-300'}`}>
                    {m.label}
                  </p>
                  <p className="text-[11px] font-mono opacity-70">{m.description}</p>
                </button>
              ))}
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-zinc-800/60">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg text-[13px] text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-1.5 rounded-lg text-[13px] font-medium bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
