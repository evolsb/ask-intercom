import { useState, useRef, useEffect } from 'react'
import { Terminal, Zap, Clock } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { cn } from '../lib/utils'

interface CLILog {
  id: string
  timestamp: number
  type: 'input' | 'output' | 'timing' | 'error'
  content: string
  duration?: number
}

interface CLIInterfaceProps {
  onSubmit: (query: string) => void
}

export function CLIInterface({ onSubmit }: CLIInterfaceProps) {
  const [cliLogs, setCLILogs] = useState<CLILog[]>([])
  const [currentCommand, setCurrentCommand] = useState('')
  const [commandHistory, setCommandHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const { isLoading, lastResult, error, progress } = useAppStore()

  // Auto-scroll to bottom when new logs are added
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [cliLogs])

  // Focus input when component mounts
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Add result to logs when query completes
  useEffect(() => {
    if (lastResult && !isLoading) {
      const duration = lastResult.processing_time_ms || 0
      const conversations = lastResult.conversation_count || 0
      const cost = lastResult.cost_info?.estimated_cost_usd || 0
      
      setCLILogs(prev => [
        ...prev,
        {
          id: `timing-${Date.now()}`,
          timestamp: Date.now(),
          type: 'timing',
          content: `✅ Complete! ${conversations} conversations analyzed in ${(duration/1000).toFixed(1)}s, cost: $${cost.toFixed(3)}`,
          duration
        },
        {
          id: `output-${Date.now()}`,
          timestamp: Date.now(),
          type: 'output',
          content: lastResult.summary || 'Analysis completed'
        }
      ])
    }
  }, [lastResult, isLoading])

  // Add error to logs
  useEffect(() => {
    if (error) {
      setCLILogs(prev => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          timestamp: Date.now(),
          type: 'error',
          content: `❌ Error: ${error.message}`
        }
      ])
    }
  }, [error])

  // Add progress updates to logs
  useEffect(() => {
    if (progress && isLoading) {
      setCLILogs(prev => {
        // Replace the last progress message if it exists
        const filtered = prev.filter(log => !(log.type === 'output' && log.content.includes('⏳')))
        return [
          ...filtered,
          {
            id: `progress-${Date.now()}`,
            timestamp: Date.now(),
            type: 'output',
            content: `⏳ ${progress.message} (${progress.percentage}%)`
          }
        ]
      })
    }
  }, [progress, isLoading])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentCommand.trim() || isLoading) return

    // Add command to logs
    setCLILogs(prev => [
      ...prev,
      {
        id: `input-${Date.now()}`,
        timestamp: Date.now(),
        type: 'input',
        content: `$ ${currentCommand.trim()}`
      }
    ])

    // Add to command history
    setCommandHistory(prev => [...prev, currentCommand.trim()])
    setHistoryIndex(-1)

    // Submit the query
    onSubmit(currentCommand.trim())
    setCurrentCommand('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (commandHistory.length > 0) {
        const newIndex = historyIndex === -1 ? commandHistory.length - 1 : Math.max(0, historyIndex - 1)
        setHistoryIndex(newIndex)
        setCurrentCommand(commandHistory[newIndex])
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIndex !== -1) {
        const newIndex = historyIndex + 1
        if (newIndex >= commandHistory.length) {
          setHistoryIndex(-1)
          setCurrentCommand('')
        } else {
          setHistoryIndex(newIndex)
          setCurrentCommand(commandHistory[newIndex])
        }
      }
    }
  }

  const clearLogs = () => {
    setCLILogs([])
  }

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  return (
    <div className="bg-gray-950 text-green-400 font-mono text-sm border rounded-lg overflow-hidden">
      {/* CLI Header */}
      <div className="bg-gray-900 px-4 py-2 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4" />
          <span className="text-gray-300">Ask Intercom CLI Testing Interface</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clearLogs}
            className="text-xs text-gray-400 hover:text-gray-200 px-2 py-1 border border-gray-700 rounded"
          >
            Clear
          </button>
          <div className="flex items-center gap-1 text-xs text-gray-400">
            <Clock className="w-3 h-3" />
            {formatTimestamp(Date.now())}
          </div>
        </div>
      </div>

      {/* CLI Output */}
      <div className="p-4 space-y-1 max-h-96 overflow-y-auto">
        {cliLogs.length === 0 && (
          <div className="text-gray-500 text-xs">
            Welcome to Ask Intercom CLI! Type a query to get started.
            <br />
            Example: "show me issues from the last 24 hours"
          </div>
        )}
        
        {cliLogs.map((log) => (
          <div key={log.id} className="flex items-start gap-2">
            <span className="text-gray-600 text-xs whitespace-nowrap">
              {formatTimestamp(log.timestamp)}
            </span>
            <div
              className={cn(
                "flex-1 leading-relaxed",
                log.type === 'input' && "text-blue-400",
                log.type === 'output' && "text-green-400",
                log.type === 'timing' && "text-yellow-400 font-bold",
                log.type === 'error' && "text-red-400"
              )}
            >
              {log.content}
            </div>
            {log.duration && (
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <Zap className="w-3 h-3" />
                {(log.duration/1000).toFixed(1)}s
              </div>
            )}
          </div>
        ))}
        
        <div ref={logsEndRef} />
      </div>

      {/* CLI Input */}
      <div className="bg-gray-900 border-t border-gray-800 p-4">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <span className="text-blue-400">$</span>
          <input
            ref={inputRef}
            type="text"
            value={currentCommand}
            onChange={(e) => setCurrentCommand(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter your query..."
            disabled={isLoading}
            className={cn(
              "flex-1 bg-transparent border-none outline-none text-green-400 placeholder-gray-600",
              "disabled:opacity-50"
            )}
          />
          {isLoading && (
            <div className="flex items-center gap-1 text-yellow-400">
              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-ping" />
              <span className="text-xs">Processing...</span>
            </div>
          )}
        </form>
        
        <div className="mt-2 text-xs text-gray-600">
          Use ↑/↓ for command history • Last {commandHistory.length} commands saved
        </div>
      </div>
    </div>
  )
}