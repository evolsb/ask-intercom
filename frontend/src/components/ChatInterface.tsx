import { useState, useRef, useEffect } from 'react'
import { Send, RotateCcw } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { cn } from '../lib/utils'
import { CustomerLink } from './CustomerLink'

interface ChatMessage {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: number
}

interface ChatInterfaceProps {
  onSubmit: (query: string) => void
  onReset: () => void
}

export function ChatInterface({ onSubmit, onReset }: ChatInterfaceProps) {
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [currentMessage, setCurrentMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { isLoading, lastResult, error } = useAppStore()

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, isTyping])

  // Add AI response when lastResult changes
  useEffect(() => {
    if (lastResult && lastResult.is_followup) {
      // For follow-ups, add the conversational response to chat
      const aiMessage: ChatMessage = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: lastResult.summary || lastResult.insights?.[0]?.description || 'No response available',
        timestamp: Date.now()
      }
      setChatMessages(prev => [...prev, aiMessage])
    }
  }, [lastResult])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentMessage.trim() || isLoading) return

    // Add user message to chat
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      type: 'user', 
      content: currentMessage.trim(),
      timestamp: Date.now()
    }
    setChatMessages(prev => [...prev, userMessage])

    // Submit the query
    onSubmit(currentMessage.trim())
    setCurrentMessage('')
    setIsTyping(true)
  }

  const handleReset = () => {
    setChatMessages([])
    setCurrentMessage('')
    setIsTyping(false)
    onReset()
  }

  // Stop typing indicator when loading stops
  useEffect(() => {
    if (!isLoading) {
      setIsTyping(false)
    }
  }, [isLoading])

  if (chatMessages.length === 0) {
    return null // Don't show chat interface until first follow-up
  }

  return (
    <div className="bg-card border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium flex items-center gap-2">
          ✨ AI Chat
        </h3>
        <button
          onClick={handleReset}
          className="flex items-center gap-2 px-3 py-1 text-sm text-muted-foreground hover:text-foreground border border-transparent hover:border-border rounded-md transition-colors"
          title="Start a new conversation"
        >
          <RotateCcw className="w-4 h-4" />
          Reset
        </button>
      </div>

      {/* Chat Messages */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {chatMessages.map((message) => (
          <div
            key={message.id}
            className={cn(
              "flex",
              message.type === 'user' ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={cn(
                "max-w-[80%] rounded-lg px-3 py-2",
                message.type === 'user'
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              )}
            >
              {message.type === 'ai' ? (
                <RichTextContent content={message.content} />
              ) : (
                <p className="text-sm">{message.content}</p>
              )}
            </div>
          </div>
        ))}
        
        {/* Typing indicator */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-lg px-3 py-2">
              <div className="flex items-center gap-1">
                <span className="text-sm text-muted-foreground">✨ AI is thinking</span>
                <div className="flex gap-1">
                  <div className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3">
          <p className="text-sm text-red-600 dark:text-red-400">{error.message}</p>
        </div>
      )}

      {/* Chat Input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={currentMessage}
          onChange={(e) => setCurrentMessage(e.target.value)}
          placeholder="Ask a follow-up question..."
          disabled={isLoading}
          className={cn(
            "flex-1 px-3 py-2 border rounded-md bg-background text-sm transition-colors",
            "focus:ring-2 focus:ring-ring focus:border-transparent",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        />
        <button
          type="submit"
          disabled={!currentMessage.trim() || isLoading}
          className={cn(
            "px-3 py-2 bg-primary text-primary-foreground rounded-md transition-colors",
            "hover:bg-primary/90 focus:ring-2 focus:ring-ring focus:ring-offset-2",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  )
}

interface RichTextContentProps {
  content: string
}

function RichTextContent({ content }: RichTextContentProps) {
  // Parse the content for customer email patterns with conversation IDs
  const parseContent = (text: string) => {
    // Pattern to match: customer@email.com (conversation: conv_abc123)
    const customerPattern = /([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s*\(conversation:\s*([^)]+)\)/g
    
    const parts = []
    let lastIndex = 0
    let match

    while ((match = customerPattern.exec(text)) !== null) {
      // Add text before the match
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: text.slice(lastIndex, match.index)
        })
      }

      // Add the customer link
      parts.push({
        type: 'customer',
        email: match[1],
        conversationId: match[2].trim(),
        content: match[0]
      })

      lastIndex = match.index + match[0].length
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push({
        type: 'text',
        content: text.slice(lastIndex)
      })
    }

    return parts
  }

  const parts = parseContent(content)

  return (
    <div className="text-sm space-y-1">
      {parts.map((part, index) => {
        if (part.type === 'customer') {
          return (
            <CustomerLink
              key={index}
              email={part.email}
              conversationId={part.conversationId}
            />
          )
        } else {
          // Split text by newlines and render paragraphs
          const lines = part.content.split('\n').filter(line => line.trim())
          return lines.map((line, lineIndex) => (
            <p key={`${index}-${lineIndex}`} className="leading-relaxed">
              {line}
            </p>
          ))
        }
      })}
    </div>
  )
}
