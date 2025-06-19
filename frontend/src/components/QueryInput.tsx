import { useState } from 'react'
import { Send } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { cn } from '../lib/utils'

interface QueryInputProps {
  onSubmit: (query: string) => void
}

const EXAMPLE_QUERIES = [
  "Show me issues from the last 24 hours",
  "What happened yesterday in support?",
  "Summarize today's conversations",
  "Show me bugs reported this week",
]

export function QueryInput({ onSubmit }: QueryInputProps) {
  const { currentQuery, setCurrentQuery, isLoading, maxConversations, setMaxConversations } = useAppStore()
  const [localQuery, setLocalQuery] = useState(currentQuery)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!localQuery.trim() || isLoading) return
    
    setCurrentQuery(localQuery)
    onSubmit(localQuery)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter submits (without Ctrl/Cmd)
    if (e.key === 'Enter' && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as any)
    }
    // Ctrl+Enter or Cmd+Enter inserts new line
    else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      const textarea = e.target as HTMLTextAreaElement
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const value = textarea.value
      const newValue = value.substring(0, start) + '\n' + value.substring(end)
      setLocalQuery(newValue)
      // Restore cursor position after React re-render
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 1
      }, 0)
    }
  }

  const handleExampleClick = (example: string) => {
    setLocalQuery(example)
    setCurrentQuery(example)
    // Auto-submit when clicking example
    onSubmit(example)
  }

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="query" className="block text-sm font-medium mb-2">
            Ask about your Intercom conversations
          </label>
          <textarea
            id="query"
            value={localQuery}
            onChange={(e) => setLocalQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g., What are the top customer complaints this month?"
            rows={3}
            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm resize-none focus:ring-2 focus:ring-ring focus:border-transparent"
            disabled={isLoading}
          />
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
            Press Enter to submit • Ctrl+Enter for new line
          </p>
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <label htmlFor="max-conversations" className="text-sm text-gray-600 dark:text-gray-400">
                Max conversations:
              </label>
              <input
                id="max-conversations"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                value={maxConversations}
                onChange={(e) => {
                  const value = e.target.value.replace(/[^0-9]/g, '')
                  if (value === '') {
                    setMaxConversations(50)
                  } else {
                    const num = parseInt(value)
                    if (num >= 10 && num <= 200) {
                      setMaxConversations(num)
                    } else if (num < 10) {
                      setMaxConversations(10)
                    } else if (num > 200) {
                      setMaxConversations(200)
                    }
                  }
                }}
                className="w-20 px-2 py-1 border border-input rounded text-sm bg-background text-center"
                disabled={isLoading}
                placeholder="50"
              />
            </div>
          </div>
          
          <button
            type="submit"
            disabled={!localQuery.trim() || isLoading}
            className={cn(
              "px-6 py-2 rounded-md font-medium text-sm transition-all duration-200",
              "bg-primary text-primary-foreground hover:bg-primary/90",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "hover:shadow-lg hover:shadow-primary/25 dark:hover:shadow-primary/20",
              isLoading && "cursor-wait"
            )}
          >
            {isLoading ? (
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                <span>Analyzing...</span>
              </div>
            ) : (
              "Analyze"
            )}
          </button>
        </div>
      </form>
      
      <div className="space-y-2">
        <p className="text-sm text-gray-600 dark:text-gray-400">Try these examples:</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUERIES.map((example, index) => (
            <button
              key={index}
              onClick={() => handleExampleClick(example)}
              disabled={isLoading}
              className="text-xs px-3 py-1.5 bg-secondary text-secondary-foreground rounded-full hover:bg-secondary/80 transition-all disabled:opacity-50 flex items-center space-x-1.5 group"
              title="Click to submit this query"
            >
              <span>{example}</span>
              <Send className="w-3 h-3 opacity-50 group-hover:opacity-100 transition-opacity" />
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
