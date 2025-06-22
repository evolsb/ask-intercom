import { useState } from 'react'
import { Copy, ExternalLink, Check } from 'lucide-react'
import { cn } from '../lib/utils'

interface CustomerLinkProps {
  email: string
  conversationId: string
}

export function CustomerLink({ email, conversationId }: CustomerLinkProps) {
  const [copied, setCopied] = useState<'email' | 'conversation' | null>(null)
  const [showActions, setShowActions] = useState(false)

  const copyToClipboard = async (text: string, type: 'email' | 'conversation') => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(type)
      setTimeout(() => setCopied(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const openIntercomConversation = () => {
    // Generate Intercom URL (we might need the app_id from backend later)
    const intercomUrl = `https://app.intercom.com/conversation/${conversationId}`
    window.open(intercomUrl, '_blank', 'noopener,noreferrer')
  }

  return (
    <span 
      className="inline-block relative"
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-md text-sm font-medium border border-blue-200 dark:border-blue-700">
        {email}
      </span>
      
      {/* Hover Actions Popup */}
      {showActions && (
        <div className="absolute bottom-full left-0 mb-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50 p-2 min-w-max">
          <div className="flex flex-col gap-1">
            <button
              onClick={() => copyToClipboard(email, 'email')}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
            >
              {copied === 'email' ? (
                <Check className="w-4 h-4 text-green-500" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
              Copy email
            </button>
            
            <button
              onClick={() => copyToClipboard(conversationId, 'conversation')}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
            >
              {copied === 'conversation' ? (
                <Check className="w-4 h-4 text-green-500" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
              Copy conversation ID
            </button>
            
            <button
              onClick={openIntercomConversation}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              Open in Intercom
            </button>
          </div>
          
          {/* Arrow pointing down */}
          <div className="absolute top-full left-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-200 dark:border-t-gray-700"></div>
        </div>
      )}
    </span>
  )
}
