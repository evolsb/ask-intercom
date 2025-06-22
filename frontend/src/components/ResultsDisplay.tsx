import { useState, useRef, useEffect } from 'react'
import { useAppStore, type StructuredInsight } from '../store/useAppStore'
import { formatCurrency, formatDuration } from '../lib/utils'
import { ChevronDown, ChevronUp, ExternalLink, MessageCircle, AlertTriangle, Lightbulb, Bug, Settings, Copy, Check, Star } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'

interface ProgressState {
  stage: string
  message: string
  percent: number
}

interface AnalysisCardProps {
  insight: StructuredInsight
  defaultExpanded?: boolean
}

export function ResultsDisplay() {
  const { lastResult, error, isLoading, currentQuery, progress } = useAppStore()
  
  // Default progress state if none provided
  const displayProgress = progress || {
    stage: 'starting',
    message: 'Initializing...',
    percent: 0
  }

  if (isLoading) {
    return (
      <div className="bg-card border rounded-lg p-6">
        <div className="flex items-center space-x-3">
          <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <div className="flex-1">
            <h3 className="font-medium">Analyzing conversations...</h3>
            <p className="text-sm text-muted-foreground mt-1">
              {displayProgress.message}
            </p>
          </div>
          <span className="text-sm font-medium text-primary">{displayProgress.percent}%</span>
        </div>
        
        <div className="mt-4">
          <div className="w-full bg-muted rounded-full h-2">
            <div 
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{ width: `${displayProgress.percent}%` }}
            />
          </div>
        </div>
        
        <div className="mt-4 space-y-2">
          <ProgressStep active={displayProgress.stage === 'initializing' || displayProgress.percent >= 5} 
                       complete={displayProgress.percent > 10}
                       label="Initializing Intercom connection" />
          <ProgressStep active={displayProgress.stage === 'timeframe' || displayProgress.percent >= 10} 
                       complete={displayProgress.percent > 20}
                       label="Interpreting query timeframe" />
          <ProgressStep active={displayProgress.stage === 'fetching' || displayProgress.percent >= 20} 
                       complete={displayProgress.percent > 70}
                       label="Fetching conversations" />
          <ProgressStep active={displayProgress.stage === 'analyzing' || displayProgress.percent >= 60} 
                       complete={displayProgress.percent > 90}
                       label="Analyzing with AI" />
          <ProgressStep active={displayProgress.stage === 'finalizing' || displayProgress.percent >= 90} 
                       complete={displayProgress.percent === 100}
                       label="Finalizing results" />
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

  // Don't show ResultsDisplay for follow-up responses - they go to chat interface
  if (lastResult.is_followup) {
    return null
  }

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Analysis Results
          </CardTitle>
          <CardDescription>
            {lastResult.insights.length} insights from {lastResult.summary?.total_conversations || 'unknown'} conversations • {formatDuration(lastResult.response_time_ms)} • {formatCurrency(lastResult.cost)}
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          {lastResult.insights.length > 0 ? (
            <div className="space-y-4">
              {lastResult.insights
                .sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0))
                .map((insight, index) => (
                <AnalysisCard 
                  key={insight.id || index} 
                  insight={insight}
                  defaultExpanded={index === 0}
                />
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground">No insights found in the analysis.</p>
          )}
        </CardContent>
      </Card>
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

function AnalysisCard({ insight, defaultExpanded = true }: AnalysisCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const [copiedUrls, setCopiedUrls] = useState<Set<number>>(new Set())
  const [contentHeight, setContentHeight] = useState<number>(0)
  const contentRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    if (contentRef.current) {
      setContentHeight(contentRef.current.scrollHeight)
    }
  }, [insight])
  
  const copyToClipboard = async (url: string, index: number) => {
    try {
      await navigator.clipboard.writeText(url)
      setCopiedUrls(prev => new Set(prev).add(index))
      setTimeout(() => {
        setCopiedUrls(prev => {
          const newSet = new Set(prev)
          newSet.delete(index)
          return newSet
        })
      }, 2000)
    } catch (err) {
      console.error('Failed to copy URL:', err)
    }
  }
  
  const getCategoryIcon = (category: string) => {
    switch (category.toUpperCase()) {
      case 'BUG': return <Bug className="h-4 w-4" />
      case 'FEATURE_REQUEST': return <Lightbulb className="h-4 w-4" />
      case 'CONFUSION': 
      case 'QUESTION': return <MessageCircle className="h-4 w-4" />
      case 'COMPLAINT': return <AlertTriangle className="h-4 w-4" />
      case 'PRAISE': return <Star className="h-4 w-4" />
      case 'PROCESS_ISSUE': return <Settings className="h-4 w-4" />
      default: return <MessageCircle className="h-4 w-4" />
    }
  }
  
  const getCategoryBadge = (category: string) => {
    switch (category.toUpperCase()) {
      case 'BUG': return <Badge variant="destructive">Bug Report</Badge>
      case 'FEATURE_REQUEST': return <Badge variant="secondary">Feature Request</Badge>
      case 'CONFUSION':
      case 'QUESTION': return <Badge variant="outline">Question</Badge>
      case 'COMPLAINT': return <Badge variant="destructive">Complaint</Badge>
      case 'PRAISE': return <Badge variant="default">Praise</Badge>
      case 'PROCESS_ISSUE': return <Badge variant="secondary">Process Issue</Badge>
      default: return <Badge variant="outline">Other</Badge>
    }
  }

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical': return <Badge variant="destructive" className="text-xs">Critical</Badge>
      case 'high': return <Badge variant="destructive" className="text-xs bg-orange-500">High</Badge>
      case 'medium': return <Badge variant="secondary" className="text-xs">Medium</Badge>
      case 'low': return <Badge variant="outline" className="text-xs">Low</Badge>
      default: return <Badge variant="outline" className="text-xs">{severity}</Badge>
    }
  }
  
  return (
    <Card className="border-border overflow-hidden">
      <CardHeader 
        className="pb-3 cursor-pointer hover:bg-muted/50 transition-colors border-b border-border/50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3">
            <div className="mt-0.5">
              {getCategoryIcon(insight.category)}
            </div>
            <div className="space-y-1">
              <CardTitle className="text-base font-medium leading-none">{insight.title}</CardTitle>
              <div className="flex items-center space-x-2 flex-wrap gap-1">
                {getCategoryBadge(insight.category)}
                {getSeverityBadge(insight.impact.severity)}
                <CardDescription className="text-xs">
                  {insight.impact.customer_count} customer{insight.impact.customer_count > 1 ? 's' : ''} • {insight.impact.percentage.toFixed(1)}%
                </CardDescription>
                <CardDescription className="text-xs font-medium">
                  Priority: {insight.priority_score}/100
                </CardDescription>
              </div>
            </div>
          </div>
          <div className="shrink-0 text-muted-foreground">
            {isExpanded ? 
              <ChevronUp className="h-4 w-4" /> : 
              <ChevronDown className="h-4 w-4" />
            }
          </div>
        </div>
      </CardHeader>
      
      <div 
        className="transition-all duration-300 ease-in-out overflow-hidden"
        style={{
          maxHeight: isExpanded ? `${contentHeight}px` : '0px',
          opacity: isExpanded ? 1 : 0
        }}
      >
        <CardContent ref={contentRef} className="pt-0 space-y-4 pb-6">
          <div>
            <p className="text-sm leading-relaxed text-muted-foreground mb-3">{insight.description}</p>
            {insight.recommendation && (
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <p className="text-sm text-blue-900 dark:text-blue-100">
                  <strong>Recommendation:</strong> {insight.recommendation}
                </p>
              </div>
            )}
          </div>
          
          {insight.customers.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2">Affected Customers:</h4>
              <div className="flex gap-2 flex-wrap">
                {insight.customers.map((customer, index) => (
                  <div key={index} className="inline-flex rounded-md border border-input bg-background overflow-hidden">
                    <a
                      href={customer.intercom_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center px-3 py-1.5 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
                      title={customer.issue_summary}
                    >
                      <ExternalLink className="h-3 w-3 mr-1.5" />
                      {customer.email}
                    </a>
                    <div className="w-px bg-border"></div>
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        copyToClipboard(customer.intercom_url, index)
                      }}
                      className="flex items-center justify-center px-2 py-1.5 hover:bg-accent hover:text-accent-foreground transition-colors"
                      title="Copy URL"
                    >
                      {copiedUrls.has(index) ? 
                        <Check className="h-3 w-3 text-green-600" /> :
                        <Copy className="h-3 w-3" />
                      }
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </div>
    </Card>
  )
}
