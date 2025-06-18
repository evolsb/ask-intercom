import { useAppStore } from './store/useAppStore'
import { ApiKeySetup } from './components/ApiKeySetup'
import { QueryInput } from './components/QueryInput'
import { ResultsDisplay } from './components/ResultsDisplay'

function App() {
  const { 
    intercomToken, 
    openaiKey, 
    setLoading, 
    setError, 
    setResult, 
    addToHistory,
    maxConversations 
  } = useAppStore()

  const handleQuery = async (query: string) => {
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
    
    // Get session ID for request tracking
    const sessionId = useAppStore.getState().getSessionId()

    try {
      const response = await fetch('/api/analyze', {
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
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        
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

      const result = await response.json()
      setResult(result)
      addToHistory(query, result)
      
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
      setError({
        error_category: 'connectivity_error',
        message: error instanceof Error ? error.message : 'An unexpected error occurred',
        user_action: 'Please check your internet connection and try again',
        retryable: true,
        session_id: sessionId,
        request_id: `req_${Date.now()}`,
        timestamp: new Date().toISOString()
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container max-w-4xl mx-auto px-4 py-8">
        <header className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">Ask Intercom</h1>
          <p className="text-muted-foreground">
            Transform your Intercom conversations into actionable insights
          </p>
        </header>

        <div className="space-y-6">
          <ApiKeySetup />
          
          <div className="bg-card border rounded-lg p-6">
            <QueryInput onSubmit={handleQuery} />
          </div>
          
          <ResultsDisplay />
        </div>

        <footer className="text-center mt-12 text-xs text-muted-foreground">
          <p>
            Built with privacy in mind • Data stored locally • 
            Automatically deleted after 30 days
          </p>
        </footer>
      </div>
    </div>
  )
}

export default App
