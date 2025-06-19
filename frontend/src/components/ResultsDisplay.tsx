import { useState, useEffect } from 'react'
import { useAppStore } from '../store/useAppStore'
import { formatCurrency, formatDuration } from '../lib/utils'
import { ChevronDown, ChevronUp, ExternalLink, MessageCircle, AlertTriangle, Lightbulb, Bug, Settings, Copy, Check } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'

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
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
      <Card>
        <CardHeader>
          <CardTitle>Analysis Results</CardTitle>
          <CardDescription>
            {lastResult.conversation_count} conversations • {formatDuration(lastResult.response_time_ms)} • {formatCurrency(lastResult.cost)}
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          {lastResult.summary && (
            <div className="space-y-4">
              {parseAnalysisIntoCards(lastResult.summary).map((card, index) => (
                <AnalysisCard key={index} {...card} />
              ))}
            </div>
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

function AnalysisCard({ title, category, content, urls, defaultExpanded = true }: AnalysisCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const [copiedUrls, setCopiedUrls] = useState<Set<number>>(new Set())
  
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
      case 'CONFUSION': return <MessageCircle className="h-4 w-4" />
      case 'COMPLAINT': return <AlertTriangle className="h-4 w-4" />
      case 'PROCESS_ISSUE': return <Settings className="h-4 w-4" />
      default: return <MessageCircle className="h-4 w-4" />
    }
  }
  
  const getCategoryBadge = (category: string) => {
    switch (category.toUpperCase()) {
      case 'BUG': return <Badge variant="destructive">Bug Report</Badge>
      case 'FEATURE_REQUEST': return <Badge variant="secondary">Feature Request</Badge>
      case 'CONFUSION': return <Badge variant="outline">Confusion</Badge>
      case 'COMPLAINT': return <Badge variant="destructive">Complaint</Badge>
      case 'PROCESS_ISSUE': return <Badge variant="secondary">Process Issue</Badge>
      default: return <Badge variant="outline">Other</Badge>
    }
  }
  
  return (
    <Card className="border-border">
      <CardHeader 
        className="pb-3 cursor-pointer hover:bg-muted/50 transition-colors border-b border-border/50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3">
            <div className="mt-0.5">
              {getCategoryIcon(category)}
            </div>
            <div className="space-y-1">
              <CardTitle className="text-base font-medium leading-none">{title}</CardTitle>
              <div className="flex items-center space-x-2">
                {getCategoryBadge(category)}
                {urls.length > 0 && (
                  <CardDescription className="text-xs">
                    {urls.length} conversation{urls.length > 1 ? 's' : ''}
                  </CardDescription>
                )}
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
      
      {isExpanded && (
        <CardContent className="pt-0">
          <p className="text-sm leading-relaxed text-muted-foreground mb-4">{content}</p>
          
          {urls.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {urls.map((link, index) => (
                <div key={index} className="inline-flex rounded-md border border-input bg-background overflow-hidden">
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center px-3 py-1.5 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
                  >
                    <ExternalLink className="h-3 w-3 mr-1.5" />
                    {link.text}
                  </a>
                  <div className="w-px bg-border"></div>
                  <button
                    onClick={(e) => {
                      e.preventDefault()
                      copyToClipboard(link.url, index)
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
          )}
        </CardContent>
      )}
    </Card>
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
      
      // Extract URLs from the section and extract customer names from URLs
      const urlMatches = Array.from(section.matchAll(/\[View\]\((https?:\/\/[^\)]+)\)/g))
      const urls = urlMatches.map((match, index) => {
        const url = match[1]
        
        // Try to extract email from the URL query parameter
        const emailMatch = url.match(/query=([^&]+)/)
        let customerName = `Customer ${index + 1}`
        
        if (emailMatch) {
          const email = decodeURIComponent(emailMatch[1].replace(/%.+/g, ''))
          if (email.includes('@')) {
            customerName = email
          }
        }
        
        // If no email in URL, try to extract from the section text around the URL
        if (customerName.startsWith('Customer')) {
          const beforeUrl = section.substring(0, section.indexOf(match[0]))
          const emailInText = beforeUrl.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g)
          if (emailInText && emailInText.length > 0) {
            customerName = emailInText[emailInText.length - 1] // Use the last email found before this URL
          }
        }
        
        return {
          text: customerName,
          url: url
        }
      })
      
      
      // Clean content by removing category markers and URLs
      let content = section
        .replace(/\[(BUG|FEATURE_REQUEST|CONFUSION|COMPLAINT|PROCESS_ISSUE|OTHER)\]/g, '')
        .replace(/\[View\]\(https?:\/\/[^\)]+\)/g, '')
        .trim()
      
      // Generate a title from the first sentence or first meaningful part
      let title = content.split('.')[0].trim()
      
      // Clean up title - remove leading dashes, bullets, etc.
      title = title.replace(/^[-•*\s]+/, '').trim()
      
      // If title is too short or empty, create a category-based title
      if (!title || title.length < 10) {
        const categoryTitles = {
          'BUG': 'Bug Report',
          'FEATURE_REQUEST': 'Feature Request', 
          'CONFUSION': 'User Confusion',
          'COMPLAINT': 'Customer Complaint',
          'PROCESS_ISSUE': 'Process Issue',
          'OTHER': 'Customer Feedback'
        }
        title = categoryTitles[category.toUpperCase() as keyof typeof categoryTitles] || 'Analysis Item'
      }
      
      // Only truncate if really necessary (keep more characters for better context)
      if (title.length > 120) {
        title = title.substring(0, 117) + '...'
      }
      
      // Remove title from content to avoid duplication (only if content actually starts with it)
      const originalTitle = content.split('.')[0].trim().replace(/^[-•*\s]+/, '').trim()
      if (content.toLowerCase().startsWith(originalTitle.toLowerCase()) && originalTitle.length > 5) {
        content = content.substring(content.indexOf('.') + 1).replace(/^[.\s]+/, '').trim()
      }
      
      // Clean up content - remove leading dashes, bullets, etc. from the remaining content
      content = content.replace(/^[-•*\s]+/, '').trim()
      
      // Remove any additional leading dashes that might appear at line breaks
      content = content.replace(/\n\s*[-•*]\s*/g, '\n').trim()
      
      if (title && content) {
        cards.push({
          title,
          category,
          content,
          urls
        })
      }
    }
  }
  
  // If no categorized content found, create a single general card
  if (cards.length === 0 && summary.trim()) {
    const urlMatches = Array.from(summary.matchAll(/\[View\]\((https?:\/\/[^\)]+)\)/g))
    const urls = urlMatches.map((match, index) => {
      const url = match[1]
      
      // Try to extract email from the URL query parameter
      const emailMatch = url.match(/query=([^&]+)/)
      let customerName = `Customer ${index + 1}`
      
      if (emailMatch) {
        const email = decodeURIComponent(emailMatch[1].replace(/%.+/g, ''))
        if (email.includes('@')) {
          customerName = email
        }
      }
      
      // If no email in URL, try to extract from the summary text around the URL
      if (customerName.startsWith('Customer')) {
        const beforeUrl = summary.substring(0, summary.indexOf(match[0]))
        const emailInText = beforeUrl.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g)
        if (emailInText && emailInText.length > 0) {
          customerName = emailInText[emailInText.length - 1] // Use the last email found before this URL
        }
      }
      
      return {
        text: customerName,
        url: url
      }
    })
    
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
