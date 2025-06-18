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
      setError('Please configure your API keys first')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
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
        throw new Error(errorData.detail || 'Analysis failed')
      }

      const result = await response.json()
      setResult(result)
      addToHistory(query, result)
    } catch (error) {
      setError(error instanceof Error ? error.message : 'An unexpected error occurred')
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
