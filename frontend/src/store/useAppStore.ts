import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface StructuredInsight {
  id: string
  category: string
  title: string
  description: string
  impact: {
    customer_count: number
    percentage: number
    severity: string
  }
  customers: Array<{
    email: string
    conversation_id: string
    intercom_url: string
    issue_summary: string
  }>
  priority_score: number
  recommendation: string
}

export interface AnalysisResult {
  insights: StructuredInsight[]
  summary: {
    total_conversations: number
    total_messages: number
    analysis_timestamp: string
  }
  cost: number
  response_time_ms: number
  session_id: string
  request_id: string
  session_state?: any  // Session state for follow-up questions
  is_followup?: boolean  // Whether this was a follow-up question
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

export interface ProgressState {
  stage: string
  message: string
  percent: number
}

export interface SessionState {
  last_query?: string
  has_conversations?: boolean
  conversation_count?: number
  last_timeframe?: {
    description: string
    start_date: string
    end_date: string
  }
}

interface AppState {
  // API Configuration
  intercomToken: string
  openaiKey: string
  maxConversations: number | null  // null = no limit
  
  // Session Management
  sessionInfo: SessionInfo | null
  sessionState: SessionState | null  // For follow-up questions
  
  // Query State
  currentQuery: string
  isLoading: boolean
  error: ErrorResponse | null
  progress: ProgressState | null
  
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
  setMaxConversations: (max: number | null) => void
  setCurrentQuery: (query: string) => void
  setLoading: (loading: boolean) => void
  setError: (error: ErrorResponse | null) => void
  setResult: (result: AnalysisResult) => void
  setProgress: (progress: ProgressState | null) => void
  addToHistory: (query: string, result: AnalysisResult) => void
  clearHistory: () => void
  reset: () => void
  generateSessionId: () => string
  getSessionId: () => string
  setSessionState: (state: SessionState | null) => void
  isFollowupQuestion: (query: string) => boolean
  canFollowup: () => boolean
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial state
      intercomToken: '',
      openaiKey: '',
      maxConversations: null,  // No limit by default
      sessionInfo: null,
      sessionState: null,
      currentQuery: '',
      isLoading: false,
      error: null,
      progress: null,
      lastResult: null,
      queryHistory: [],
      
      // Actions
      setIntercomToken: (token) => set({ intercomToken: token }),
      setOpenaiKey: (key) => set({ openaiKey: key }),
      setMaxConversations: (max) => set({ 
        maxConversations: max === null ? null : Math.min(max, 1000) 
      }),
      setCurrentQuery: (query) => set({ currentQuery: query }),
      setLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error }),
      setResult: (result) => {
        // Update session state from result if available
        if (result.session_state) {
          set({ sessionState: result.session_state })
        }
        set({ lastResult: result, error: null })
      },
      setProgress: (progress) => set({ progress }),
      setSessionState: (state) => set({ sessionState: state }),
      
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
        progress: null,
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
      
      isFollowupQuestion: (query: string) => {
        const queryLower = query.toLowerCase()
        const followupPatterns = [
          'tell me more about',
          'more details on',
          'explain the',
          'what about',
          'drill into',
          'elaborate on',
          'expand on',
          'show me more',
          'details about',
          'specifics on',
          'verification',
          'access to funds',
          'business account',
          'onboarding',
        ]
        return followupPatterns.some(pattern => queryLower.includes(pattern))
      },
      
      canFollowup: () => {
        const state = get()
        return state.sessionState && state.sessionState.has_conversations
      },
    }),
    {
      name: 'ask-intercom-storage',
      partialize: (state) => ({
        intercomToken: state.intercomToken,
        openaiKey: state.openaiKey,
        maxConversations: state.maxConversations,
        queryHistory: state.queryHistory,
        sessionState: state.sessionState,
        sessionInfo: state.sessionInfo,
      }),
    }
  )
)
