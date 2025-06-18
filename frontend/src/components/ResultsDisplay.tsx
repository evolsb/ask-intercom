import { useAppStore } from '../store/useAppStore'
import { formatCurrency, formatDuration } from '../lib/utils'

export function ResultsDisplay() {
  const { lastResult, error, isLoading, currentQuery } = useAppStore()

  if (isLoading) {
    return (
      <div className="bg-card border rounded-lg p-6">
        <div className="flex items-center space-x-3">
          <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <div>
            <h3 className="font-medium">Analyzing conversations...</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Processing: "{currentQuery}"
            </p>
          </div>
        </div>
        
        <div className="mt-4 space-y-2">
          <div className="flex space-x-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            <span className="text-sm text-muted-foreground">Fetching conversations from Intercom...</span>
          </div>
          <div className="flex space-x-2">
            <div className="w-2 h-2 bg-gray-300 rounded-full" />
            <span className="text-sm text-muted-foreground">Analyzing with AI...</span>
          </div>
          <div className="flex space-x-2">
            <div className="w-2 h-2 bg-gray-300 rounded-full" />
            <span className="text-sm text-muted-foreground">Generating insights...</span>
          </div>
        </div>
        
        <div className="mt-4 text-xs text-muted-foreground">
          This usually takes 10-30 seconds depending on conversation volume.
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="font-medium text-destructive mb-1">
              {error.error_category.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </h3>
            <span className="text-xs text-muted-foreground">Session: {error.session_id}</span>
          </div>
          {error.retryable && (
            <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
              Retryable
            </span>
          )}
        </div>
        
        <p className="text-sm text-destructive mb-3">{error.message}</p>
        <p className="text-sm text-blue-600 mb-4 font-medium">{error.user_action}</p>
        
        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            Support Information
          </summary>
          <div className="mt-2 space-y-1 text-muted-foreground">
            <p>• Session ID: {error.session_id}</p>
            <p>• Request ID: {error.request_id}</p>
            <p>• Timestamp: {new Date(error.timestamp).toLocaleString()}</p>
            <p>• Category: {error.error_category}</p>
          </div>
        </details>
        
        {error.retryable && (
          <div className="mt-4">
            <button 
              onClick={() => window.location.reload()}
              className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    )
  }

  if (!lastResult) {
    return (
      <div className="bg-muted/30 border-2 border-dashed border-muted rounded-lg p-8 text-center">
        <div className="space-y-2">
          <h3 className="font-medium text-lg">Ready to analyze</h3>
          <p className="text-muted-foreground">
            Configure your API keys and enter a query to get started.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="bg-card border rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium text-lg">Analysis Results</h3>
          <div className="flex items-center space-x-4 text-sm text-muted-foreground">
            <span>{lastResult.conversation_count} conversations</span>
            <span>{formatDuration(lastResult.response_time_ms)}</span>
            <span>{formatCurrency(lastResult.cost)}</span>
          </div>
        </div>
        
        <div className="space-y-3">
          {lastResult.insights.map((insight, index) => (
            <div key={index} className="flex items-start space-x-3">
              <div className="w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-xs font-medium mt-0.5">
                {index + 1}
              </div>
              <p className="text-sm leading-relaxed flex-1">{insight}</p>
            </div>
          ))}
        </div>
      </div>
      
      <div className="bg-muted/30 rounded-lg p-4">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-lg font-semibold">{lastResult.conversation_count}</div>
            <div className="text-xs text-muted-foreground">Conversations</div>
          </div>
          <div>
            <div className="text-lg font-semibold">{formatDuration(lastResult.response_time_ms)}</div>
            <div className="text-xs text-muted-foreground">Response Time</div>
          </div>
          <div>
            <div className="text-lg font-semibold">{formatCurrency(lastResult.cost)}</div>
            <div className="text-xs text-muted-foreground">AI Cost</div>
          </div>
        </div>
      </div>
    </div>
  )
}
