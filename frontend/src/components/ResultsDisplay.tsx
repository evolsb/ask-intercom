import { useState, useEffect } from 'react'
import { useAppStore } from '../store/useAppStore'
import { formatCurrency, formatDuration } from '../lib/utils'
import { ChevronDown, ChevronUp, ExternalLink, MessageCircle, AlertTriangle, Lightbulb, Bug, Settings } from 'lucide-react'

interface ProgressState {
  stage: string
  message: string
  percent: number
}

interface AnalysisCardData {
  title: string
  category: string
  content: string
  urls: Array<{ text: string; url: string }>
  customerEmail?: string
}

interface AnalysisCardProps extends AnalysisCardData {
  defaultExpanded?: boolean
}

export function ResultsDisplay() {
  const { lastResult, error, isLoading, currentQuery } = useAppStore()
  const [progress, setProgress] = useState<ProgressState>({
    stage: 'starting',
    message: 'Initializing...',
    percent: 0
  })
  const [showFullSummary, setShowFullSummary] = useState(false)

  if (isLoading) {
    return (
      <div className="bg-card border rounded-lg p-6">
        <div className="flex items-center space-x-3">
          <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <div className="flex-1">
            <h3 className="font-medium">Analyzing conversations...</h3>
            <p className="text-sm text-muted-foreground mt-1">
              {progress.message}
            </p>
          </div>
          <span className="text-sm font-medium text-primary">{progress.percent}%</span>
        </div>
        
        <div className="mt-4">
          <div className="w-full bg-muted rounded-full h-2">
            <div 
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress.percent}%` }}
            />
          </div>
        </div>
        
        <div className="mt-4 space-y-2">
          <ProgressStep active={progress.stage === 'initializing' || progress.percent >= 5} 
                       complete={progress.percent > 10}
                       label="Initializing Intercom connection" />
          <ProgressStep active={progress.stage === 'timeframe' || progress.percent >= 10} 
                       complete={progress.percent > 50}
                       label="Interpreting query timeframe" />
          <ProgressStep active={progress.stage === 'fetching' || progress.percent >= 50} 
                       complete={progress.percent > 75}
                       label="Fetching conversations" />
          <ProgressStep active={progress.stage === 'analyzing' || progress.percent >= 75} 
                       complete={progress.percent === 100}
                       label="Analyzing with AI" />
        </div>
        
        <div className="mt-4 text-xs text-muted-foreground">
          Processing: "{currentQuery}"
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
            <span className="text-xs text-gray-600 dark:text-gray-400">Session: {error.session_id}</span>
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
          <summary className="cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100">
            Support Information
          </summary>
          <div className="mt-2 space-y-1 text-gray-600 dark:text-gray-400">
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
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      {/* Header with Metrics */}
      <div className="bg-card border rounded-xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Analysis Results</h3>
          <div className="flex items-center space-x-6 text-sm">
            <div className="text-center">
              <div className="text-lg font-bold text-gray-900 dark:text-gray-100">{lastResult.conversation_count}</div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Conversations</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-gray-900 dark:text-gray-100">{formatDuration(lastResult.response_time_ms)}</div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Response Time</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-gray-900 dark:text-gray-100">{formatCurrency(lastResult.cost)}</div>
              <div className="text-xs text-gray-600 dark:text-gray-400">AI Cost</div>
            </div>
          </div>
        </div>
        
        {/* Key Insights Grid */}
        <div className="grid gap-4">
          {lastResult.insights.map((insight, index) => (
            <div key={index} className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-semibold mt-0.5 shadow-sm">
                  {index + 1}
                </div>
                <p className="text-gray-800 dark:text-gray-200 leading-relaxed font-medium">{insight}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detailed Analysis Cards */}
      {lastResult.summary && (
        <div className="space-y-4">
          <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Detailed Analysis with Conversation Links</h4>
          {parseAnalysisIntoCards(lastResult.summary).map((card, index) => (
            <AnalysisCard key={index} {...card} />
          ))}
        </div>
      )}
    </div>
  )
}

function ProgressStep({ active, complete, label }: { active: boolean; complete: boolean; label: string }) {
  return (
    <div className="flex items-center space-x-2">
      <div className={`w-2 h-2 rounded-full transition-all ${
        complete ? 'bg-green-500' : 
        active ? 'bg-blue-500 animate-pulse' : 
        'bg-gray-300'
      }`} />
      <span className={`text-sm transition-colors ${
        active || complete ? 'text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-500'
      }`}>
        {label}
      </span>
    </div>
  )
}

function AnalysisCard({ title, category, content, urls, customerEmail, defaultExpanded = true }: AnalysisCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  
  const getCategoryIcon = (category: string) => {
    switch (category.toUpperCase()) {
      case 'BUG': return <Bug className="w-4 h-4" />
      case 'FEATURE_REQUEST': return <Lightbulb className="w-4 h-4" />
      case 'CONFUSION': return <MessageCircle className="w-4 h-4" />
      case 'COMPLAINT': return <AlertTriangle className="w-4 h-4" />
      case 'PROCESS_ISSUE': return <Settings className="w-4 h-4" />
      default: return <MessageCircle className="w-4 h-4" />
    }
  }
  
  const getCategoryColor = (category: string) => {
    switch (category.toUpperCase()) {
      case 'BUG': return 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20'
      case 'FEATURE_REQUEST': return 'border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/20'
      case 'CONFUSION': return 'border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/20'
      case 'COMPLAINT': return 'border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-900/20'
      case 'PROCESS_ISSUE': return 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20'
      default: return 'border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/20'
    }
  }

  const getCategoryTextColor = (category: string) => {
    switch (category.toUpperCase()) {
      case 'BUG': return 'text-red-700 dark:text-red-300'
      case 'FEATURE_REQUEST': return 'text-purple-700 dark:text-purple-300'
      case 'CONFUSION': return 'text-yellow-700 dark:text-yellow-300'
      case 'COMPLAINT': return 'text-orange-700 dark:text-orange-300'
      case 'PROCESS_ISSUE': return 'text-blue-700 dark:text-blue-300'
      default: return 'text-gray-700 dark:text-gray-300'
    }
  }
  
  return (
    <div className={`border rounded-xl overflow-hidden transition-all duration-200 hover:shadow-md ${getCategoryColor(category)}`}>
      <div 
        className="p-4 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${getCategoryTextColor(category)}`}>
              {getCategoryIcon(category)}
            </div>
            <div>
              <h5 className="font-semibold text-gray-900 dark:text-gray-100">{title}</h5>
              <span className={`text-xs font-medium uppercase tracking-wide ${getCategoryTextColor(category)}`}>
                {category.replace('_', ' ')}
              </span>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {urls.length > 0 && (
              <span className="text-xs text-gray-600 dark:text-gray-400 font-medium">
                {urls.length} conversation{urls.length > 1 ? 's' : ''}
              </span>
            )}
            {isExpanded ? 
              <ChevronUp className="w-5 h-5 text-gray-600 dark:text-gray-400" /> : 
              <ChevronDown className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            }
          </div>
        </div>
      </div>
      
      {isExpanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-white dark:bg-gray-950">
          <div className="space-y-4">
            <p className="text-gray-700 dark:text-gray-200 leading-relaxed">{content}</p>
            
            {customerEmail && (
              <div className="flex items-center space-x-2 text-sm">
                <span className="text-gray-600 dark:text-gray-400">Customer:</span>
                <span className="font-medium text-blue-600 dark:text-blue-400">{customerEmail}</span>
              </div>
            )}
            
            {urls.length > 0 && (
              <div className="space-y-2">
                <h6 className="text-sm font-medium text-gray-900 dark:text-gray-100">Related Conversations:</h6>
                <div className="flex flex-wrap gap-2">
                  {urls.map((link, index) => (
                    <a
                      key={index}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center space-x-1 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-xs font-medium hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                    >
                      <span>{link.text}</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function parseAnalysisIntoCards(summary: string): AnalysisCardData[] {
  const cards: AnalysisCardData[] = []
  
  // Split by double newlines to get potential sections
  const sections = summary.split('\n\n').filter(s => s.trim())
  
  for (const section of sections) {
    // Look for category markers like [BUG], [FEATURE_REQUEST], etc.
    const categoryMatch = section.match(/\[(BUG|FEATURE_REQUEST|CONFUSION|COMPLAINT|PROCESS_ISSUE|OTHER)\]/)
    
    if (categoryMatch) {
      const category = categoryMatch[1]
      
      // Extract URLs from the section
      const urlMatches = Array.from(section.matchAll(/\[View\]\((https?:\/\/[^\)]+)\)/g))
      const urls = urlMatches.map((match, index) => ({
        text: `View Conversation ${index + 1}`,
        url: match[1]
      }))
      
      // Extract customer email if present
      const emailMatch = section.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/)
      const customerEmail = emailMatch ? emailMatch[1] : undefined
      
      // Clean content by removing category markers and URLs
      let content = section
        .replace(/\[(BUG|FEATURE_REQUEST|CONFUSION|COMPLAINT|PROCESS_ISSUE|OTHER)\]/g, '')
        .replace(/\[View\]\(https?:\/\/[^\)]+\)/g, '')
        .trim()
      
      // Generate a title from the first sentence or first meaningful part
      let title = content.split('.')[0].trim()
      if (title.length > 80) {
        title = title.substring(0, 80) + '...'
      }
      
      // Remove title from content to avoid duplication
      if (content.startsWith(title)) {
        content = content.substring(title.length).replace(/^[.\s]+/, '').trim()
      }
      
      if (title && content) {
        cards.push({
          title,
          category,
          content,
          urls,
          customerEmail
        })
      }
    }
  }
  
  // If no categorized content found, create a single general card
  if (cards.length === 0 && summary.trim()) {
    const urlMatches = Array.from(summary.matchAll(/\[View\]\((https?:\/\/[^\)]+)\)/g))
    const urls = urlMatches.map((match, index) => ({
      text: `View Conversation ${index + 1}`,
      url: match[1]
    }))
    
    const cleanContent = summary.replace(/\[View\]\(https?:\/\/[^\)]+\)/g, '').trim()
    const title = cleanContent.split('.')[0].trim()
    const content = cleanContent.substring(title.length).replace(/^[.\s]+/, '').trim()
    
    cards.push({
      title: title || 'Analysis Summary',
      category: 'OTHER',
      content: content || cleanContent,
      urls
    })
  }
  
  return cards
}

function formatSummaryWithLinks(summary: string): string {
  // Convert markdown links to HTML links with styling
  let formatted = summary
    .replace(/\[View\]\((https?:\/\/[^\)]+)\)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 underline ml-1">[View]</a>')
    .replace(/\n/g, '<br />')
  
  // Format categories with colors
  formatted = formatted.replace(/\[(BUG|FEATURE_REQUEST|CONFUSION|COMPLAINT|PROCESS_ISSUE|OTHER)\]/g, (match, category) => {
    const colors: Record<string, string> = {
      BUG: 'text-red-600 font-semibold',
      FEATURE_REQUEST: 'text-purple-600 font-semibold',
      CONFUSION: 'text-yellow-600 font-semibold',
      COMPLAINT: 'text-orange-600 font-semibold',
      PROCESS_ISSUE: 'text-blue-600 font-semibold',
      OTHER: 'text-gray-600 font-semibold'
    }
    return `<span class="${colors[category] || 'font-semibold'}">[${category}]</span>`
  })
  
  // Format email addresses
  formatted = formatted.replace(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g, '<span class="text-blue-600">$1</span>')
  
  return formatted
}
