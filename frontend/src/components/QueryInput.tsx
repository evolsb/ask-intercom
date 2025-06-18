import { useState } from 'react'
import { useAppStore } from '../store/useAppStore'
import { cn } from '../lib/utils'

interface QueryInputProps {
  onSubmit: (query: string) => void
}

const EXAMPLE_QUERIES = [
  "What are the top customer complaints this month?",
  "Show me product feedback from the last week",
  "What features are customers requesting most?",
  "Summarize support issues from yesterday",
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

  const handleExampleClick = (example: string) => {
    setLocalQuery(example)
    setCurrentQuery(example)
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
            placeholder="e.g., What are the top customer complaints this month?"
            rows={3}
            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm resize-none focus:ring-2 focus:ring-ring focus:border-transparent"
            disabled={isLoading}
          />
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <label htmlFor="max-conversations" className="text-sm text-muted-foreground">
                Max conversations:
              </label>
              <input
                id="max-conversations"
                type="number"
                min="10"
                max="200"
                value={maxConversations}
                onChange={(e) => setMaxConversations(parseInt(e.target.value) || 50)}
                className="w-16 px-2 py-1 border border-input rounded text-sm bg-background"
                disabled={isLoading}
              />
            </div>
          </div>
          
          <button
            type="submit"
            disabled={!localQuery.trim() || isLoading}
            className={cn(
              "px-6 py-2 rounded-md font-medium text-sm transition-colors",
              "bg-primary text-primary-foreground hover:bg-primary/90",
              "disabled:opacity-50 disabled:cursor-not-allowed",
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
        <p className="text-sm text-muted-foreground">Try these examples:</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUERIES.map((example, index) => (
            <button
              key={index}
              onClick={() => handleExampleClick(example)}
              disabled={isLoading}
              className="text-xs px-3 py-1 bg-secondary text-secondary-foreground rounded-full hover:bg-secondary/80 transition-colors disabled:opacity-50"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
