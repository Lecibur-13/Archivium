import { useEffect, useRef } from 'react'
import { Terminal } from 'lucide-react'

interface Props {
  logs: string[]
  isTransferring: boolean
}

export default function ActivityLog({ logs, isTransferring }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div className="rounded-lg border border-zinc-800/60 bg-zinc-950/80 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-800/60">
        <Terminal size={11} className="text-zinc-600" />
        <span className="text-[11px] font-medium text-zinc-500 uppercase tracking-wider">
          Activity Log
        </span>
        {isTransferring && (
          <span className="ml-auto flex items-center gap-1 text-[10px] text-blue-400">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            Live
          </span>
        )}
      </div>
      <div className="h-36 overflow-y-auto px-3 py-2 font-mono text-[11px] leading-5">
        {logs.length === 0 ? (
          <p className="text-zinc-700 italic">Waiting for transfer to start...</p>
        ) : (
          logs.map((line, i) => (
            <p key={i} className="text-zinc-400">
              <span className="text-zinc-700 mr-2">›</span>
              {line}
            </p>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
