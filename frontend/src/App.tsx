import { useRef, useState } from 'react'
import { useAppStore } from './store/useAppStore'
import { QueryInput } from './components/QueryInput'
import { ResultsDisplay } from './components/ResultsDisplay'
import { ThemeToggle } from './components/ThemeToggle'
import { Settings } from './components/Settings'
import { ChatInterface } from './components/ChatInterface'
import { CLIInterface } from './components/CLIInterface'

function App() {
  const { 
    intercomToken, 
    openaiKey, 
    setLoading, 
    setError, 
    setResult, 
    addToHistory,
    maxConversations,
    setProgress,
    sessionState,
    isFollowupQuestion,
    canFollowup,
    lastResult,
    reset
  } = useAppStore()
  
  const [activeTab, setActiveTab] = useState<'main' | 'cli'>('main')
  const abortControllerRef = useRef<AbortController | null>(null)

  const handleQuery = async (query: string) => {
    // Cancel any previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    if (!intercomToken || !openaiKey) {
      setError({
        error_category: 'environment_error',
        message: 'Please configure your API keys first',
        user_action: 'Enter your Intercom and OpenAI API keys in the configuration section above',
        retryable: true,
        session_id: useAppStore.getState().getSessionId(),
        request_id: `req_${Date.now()}`,
        timestamp: new Date().toISOString()
      })
      return
    }

    setLoading(true)
    setError(null)
    setProgress(null)
    
    // Get session ID for request tracking
    const sessionId = useAppStore.getState().getSessionId()
    
    // Create new AbortController for this request
    abortControllerRef.current = new AbortController()

    try {
      // Use Server-Sent Events for real-time progress with structured results
      const response = await fetch('/api/analyze/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId,
        },
        body: JSON.stringify({
          query,
          intercom_token: intercomToken,
          openai_key: openaiKey,
          max_conversations: maxConversations,
          session_state: sessionState,
        }),
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) {
        let errorData: any
        try {
          // Try to get the response text first (since we can only read it once)
          const responseText = await response.text()
          try {
            // Try to parse as JSON
            errorData = JSON.parse(responseText)
          } catch (jsonParseError) {
            // If JSON parsing fails, use the raw text
            setError({
              error_category: 'server_error',
              message: `Server error (${response.status}): ${response.statusText}`,
              user_action: response.status === 500 
                ? 'The server encountered an internal error. Please try again in a few moments or contact support.'
                : 'Please try again or contact support if the problem persists',
              retryable: true,
              session_id: sessionId,
            request_id: response.headers.get('X-Request-ID') || `req_${Date.now()}`,
            timestamp: new Date().toISOString()
          })
          console.error('Server error response:', responseText.substring(0, 200))
          return
          }
        } catch (parseError) {
          // If we can't read the response at all
          setError({
            error_category: 'connectivity_error',
            message: `Server error (${response.status}): Unable to read response`,
            user_action: 'Please check your internet connection and try again',
            retryable: true,
            session_id: sessionId,
            request_id: `req_${Date.now()}`,
            timestamp: new Date().toISOString()
          })
          return
        }
        
        // Check if it's a structured error response
        if (errorData.detail && typeof errorData.detail === 'object') {
          setError(errorData.detail)
        } else {
          // Fallback for non-structured errors
          setError({
            error_category: 'processing_error',
            message: errorData.detail || 'Analysis failed',
            user_action: 'Please try again or contact support if the problem persists',
            retryable: true,
            session_id: sessionId,
            request_id: response.headers.get('X-Request-ID') || `req_${Date.now()}`,
            timestamp: new Date().toISOString()
          })
        }
        return
      }

      // Handle Server-Sent Events
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('Failed to get response reader')
      }

      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        
        // Process complete SSE events (ended by double newline)
        const events = buffer.split('\n\n')
        buffer = events.pop() || '' // Keep incomplete event in buffer

        for (const event of events) {
          if (!event.trim()) continue

          const lines = event.split('\n')
          let eventType = ''
          let eventData = ''

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.substring(7).trim()
            } else if (line.startsWith('data: ')) {
              eventData = line.substring(6).trim()
            }
          }

          if (eventData) {
            try {
              const data = JSON.parse(eventData)
              
              if (eventType === 'progress' && data.stage && data.message && typeof data.percent === 'number') {
                // Update progress in store
                setProgress({
                  stage: data.stage,
                  message: data.message,
                  percent: data.percent
                })
              } else if (eventType === 'complete' && data.insights && data.summary) {
                // Final result - check if it's structured or legacy format
                if (Array.isArray(data.insights) && data.insights.length > 0 && data.insights[0].id) {
                  // Structured format - use directly
                  const structuredResult = {
                    insights: data.insights,
                    summary: data.summary,
                    cost: data.cost,
                    response_time_ms: data.response_time_ms,
                    session_id: data.session_id,
                    request_id: data.request_id,
                    session_state: data.session_state,
                    is_followup: data.is_followup
                  }
                  setResult(structuredResult)
                  addToHistory(query, structuredResult)
                } else {
                  // Legacy format - convert to structured (fallback)
                  const structuredResult = {
                    insights: data.insights.map((insight: string, index: number) => ({
                      id: `insight_${index}`,
                      category: 'GENERAL',
                      title: insight,
                      description: insight,
                      impact: {
                        customer_count: 1,
                        percentage: 0,
                        severity: 'medium'
                      },
                      customers: [],
                      priority_score: 50,
                      recommendation: ''
                    })),
                    summary: {
                      total_conversations: data.conversation_count || 0,
                      total_messages: (data.conversation_count || 0) * 5,
                      analysis_timestamp: new Date().toISOString()
                    },
                    cost: data.cost,
                    response_time_ms: data.response_time_ms,
                    session_id: data.session_id,
                    request_id: data.request_id,
                    session_state: data.session_state,
                    is_followup: data.is_followup
                  }
                  setResult(structuredResult)
                  addToHistory(query, structuredResult)
                }
              } else if (eventType === 'error' && data.error_category) {
                // Error event
                setError(data)
                return
              }
            } catch (parseError) {
              console.error('Failed to parse SSE data:', {
                error: parseError,
                eventType,
                eventData,
                rawEvent: event
              })
              // Show user-friendly error for parsing issues
              setError({
                error_category: 'processing_error',
                message: 'Failed to process server response',
                user_action: 'Please refresh the page and try again',
                retryable: true,
                session_id: sessionId,
                request_id: `req_${Date.now()}`,
                timestamp: new Date().toISOString()
              })
            }
          }
        }
      }
      
      // Update session query count
      const currentSession = useAppStore.getState().sessionInfo
      if (currentSession) {
        useAppStore.setState({
          sessionInfo: {
            ...currentSession,
            queries: currentSession.queries + 1
          }
        })
      }
      
    } catch (error) {
      // Don't show error for aborted requests
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Request was aborted')
      } else {
        setError({
          error_category: 'connectivity_error',
          message: error instanceof Error ? error.message : 'An unexpected error occurred',
          user_action: 'Please check your internet connection and try again',
          retryable: true,
          session_id: sessionId,
          request_id: `req_${Date.now()}`,
          timestamp: new Date().toISOString()
        })
      }
    } finally {
      setLoading(false)
      abortControllerRef.current = null
    }
  }

  return (
    <div className="min-h-screen bg-background transition-colors">
      <div className="container max-w-4xl mx-auto px-4 py-8">
        <header className="mb-8">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent dark:from-blue-400 dark:to-purple-400 flex items-center gap-2">
                ✨ Ask Intercom
              </h1>
              <p className="text-muted-foreground">
                Transform your Intercom conversations into actionable insights
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <Settings />
              <ThemeToggle />
            </div>
          </div>
        </header>

        {/* Tab Navigation */}
        <div className="mb-6">
          <div className="border-b border-border">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('main')}
                className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'main'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:border-gray-300'
                }`}
              >
                ✨ Main Interface
              </button>
              <button
                onClick={() => setActiveTab('cli')}
                className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'cli'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:border-gray-300'
                }`}
              >
                🚀 CLI Testing
              </button>
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'main' && (
          <div className="space-y-6">
            <div className="bg-card border rounded-lg p-6 hover:shadow-lg transition-shadow duration-300">
              <QueryInput onSubmit={handleQuery} />
            </div>
            
            <ResultsDisplay />
            
            {/* Chat interface appears after first result */}
            {lastResult && (
              <ChatInterface 
                onSubmit={handleQuery} 
                onReset={() => {
                  reset()
                  // Cancel any ongoing request
                  if (abortControllerRef.current) {
                    abortControllerRef.current.abort()
                    abortControllerRef.current = null
                  }
                }} 
              />
            )}
          </div>
        )}

        {activeTab === 'cli' && (
          <div className="space-y-6">
            <CLIInterface onSubmit={handleQuery} />
            
            {/* Performance Summary for CLI */}
            {lastResult && (
              <div className="bg-card border rounded-lg p-4">
                <h3 className="font-medium mb-3">⚡ Performance Summary</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-muted-foreground">Total Time</div>
                    <div className="font-mono">{((lastResult.processing_time_ms || 0)/1000).toFixed(1)}s</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Data Fetch</div>
                    <div className="font-mono">{((lastResult.fetch_time_ms || 0)/1000).toFixed(1)}s</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">AI Analysis</div>
                    <div className="font-mono">{((lastResult.analysis_time_ms || 0)/1000).toFixed(1)}s</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Cost</div>
                    <div className="font-mono">${(lastResult.cost_info?.estimated_cost_usd || 0).toFixed(3)}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        <footer className="text-center mt-12 text-xs text-muted-foreground">
          <p>
            Built with privacy in mind • Data stored locally • 
            Automatically deleted after 30 days
          </p>
          <p className="mt-1 font-mono opacity-50">
            Session: {useAppStore.getState().getSessionId()}
          </p>
        </footer>
      </div>
    </div>
  )
}

export default App
