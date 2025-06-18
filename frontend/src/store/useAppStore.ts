import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface AnalysisResult {
  insights: string[]
  cost: number
  response_time_ms: number
  conversation_count: number
  session_id: string
  request_id: string
}

export interface ErrorResponse {
  error_category: string
  message: string
  user_action: string
  retryable: boolean
  session_id: string
  request_id: string
  timestamp: string
}

export interface SessionInfo {
  sessionId: string
  startTime: number
  queries: number
}

interface AppState {
  // API Configuration
  intercomToken: string
  openaiKey: string
  maxConversations: number
  
  // Session Management
  sessionInfo: SessionInfo | null
  
  // Query State
  currentQuery: string
  isLoading: boolean
  error: ErrorResponse | null
  
  // Results
  lastResult: AnalysisResult | null
  queryHistory: Array<{
    query: string
    result: AnalysisResult
    timestamp: number
  }>
  
  // Actions
  setIntercomToken: (token: string) => void
  setOpenaiKey: (key: string) => void
  setMaxConversations: (max: number) => void
  setCurrentQuery: (query: string) => void
  setLoading: (loading: boolean) => void
  setError: (error: ErrorResponse | null) => void
  setResult: (result: AnalysisResult) => void
  addToHistory: (query: string, result: AnalysisResult) => void
  clearHistory: () => void
  reset: () => void
  generateSessionId: () => string
  getSessionId: () => string
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial state
      intercomToken: '',
      openaiKey: '',
      maxConversations: 50,
      sessionInfo: null,
      currentQuery: '',
      isLoading: false,
      error: null,
      lastResult: null,
      queryHistory: [],
      
      // Actions
      setIntercomToken: (token) => set({ intercomToken: token }),
      setOpenaiKey: (key) => set({ openaiKey: key }),
      setMaxConversations: (max) => set({ maxConversations: Math.min(max, 200) }),
      setCurrentQuery: (query) => set({ currentQuery: query }),
      setLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error }),
      setResult: (result) => set({ lastResult: result, error: null }),
      
      addToHistory: (query, result) => {
        const history = get().queryHistory
        const newEntry = { query, result, timestamp: Date.now() }
        // Keep only last 20 queries
        const newHistory = [newEntry, ...history].slice(0, 20)
        set({ queryHistory: newHistory })
      },
      
      clearHistory: () => set({ queryHistory: [] }),
      
      reset: () => set({
        currentQuery: '',
        isLoading: false,
        error: null,
        lastResult: null,
      }),
      
      generateSessionId: () => {
        const sessionId = `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        const sessionInfo: SessionInfo = {
          sessionId,
          startTime: Date.now(),
          queries: 0
        }
        set({ sessionInfo })
        return sessionId
      },
      
      getSessionId: () => {
        const current = get().sessionInfo
        if (!current) {
          return get().generateSessionId()
        }
        return current.sessionId
      },
    }),
    {
      name: 'ask-intercom-storage',
      partialize: (state) => ({
        intercomToken: state.intercomToken,
        openaiKey: state.openaiKey,
        maxConversations: state.maxConversations,
        queryHistory: state.queryHistory,
      }),
    }
  )
)
