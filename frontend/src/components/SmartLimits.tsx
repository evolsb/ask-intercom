import { useState, useEffect } from 'react'
import { Brain, Settings } from 'lucide-react'
import { cn } from '../lib/utils'

interface SmartLimitsProps {
  query: string
  maxConversations: number | null
  onMaxConversationsChange: (value: number | null) => void
  disabled?: boolean
}

interface SmartLimitInfo {
  limit: number
  description: string
  timeframe: string
}

export function SmartLimits({ 
  query, 
  maxConversations, 
  onMaxConversationsChange, 
  disabled = false 
}: SmartLimitsProps) {
  const [smartLimit, setSmartLimit] = useState<SmartLimitInfo | null>(null)
  const [showOverride, setShowOverride] = useState(false)
  const [overrideValue, setOverrideValue] = useState('')

  // Calculate smart limit based on query
  useEffect(() => {
    if (!query.trim()) {
      setSmartLimit(null)
      return
    }

    const result = calculateSmartLimit(query)
    setSmartLimit(result)
    
    // If not in override mode, use smart limit
    if (maxConversations === null) {
      // Smart limit is active
    } else if (maxConversations <= 100) {
      // Small hardcoded value - convert to smart limit
      onMaxConversationsChange(null)
    }
  }, [query])

  // Update override value when maxConversations changes
  useEffect(() => {
    if (maxConversations !== null && maxConversations > 100) {
      setOverrideValue(maxConversations.toString())
      setShowOverride(true)
    } else {
      setOverrideValue('')
      setShowOverride(false)
    }
  }, [maxConversations])

  const handleOverrideToggle = () => {
    if (showOverride) {
      // Disable override - use smart limits
      setShowOverride(false)
      setOverrideValue('')
      onMaxConversationsChange(null)
    } else {
      // Enable override
      setShowOverride(true)
      setOverrideValue('')
    }
  }

  const handleOverrideChange = (value: string) => {
    setOverrideValue(value)
    
    if (value === '') {
      onMaxConversationsChange(null) // Use smart limit
    } else {
      const num = parseInt(value)
      if (!isNaN(num) && num > 0) {
        onMaxConversationsChange(Math.min(num, 1000)) // Cap at 1000
      }
    }
  }

  if (!smartLimit) {
    return null
  }

  const isUsingSmartLimit = maxConversations === null || maxConversations <= 100

  return (
    <div className="space-y-3">
      {/* Smart Limit Display */}
      <div className={cn(
        "flex items-start space-x-3 p-3 rounded-lg border transition-all",
        isUsingSmartLimit 
          ? "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800" 
          : "bg-gray-50 dark:bg-gray-900/30 border-gray-200 dark:border-gray-700"
      )}>
        <Brain className={cn(
          "w-5 h-5 mt-0.5 flex-shrink-0",
          isUsingSmartLimit 
            ? "text-blue-600 dark:text-blue-400" 
            : "text-gray-500 dark:text-gray-400"
        )} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <h4 className={cn(
              "text-sm font-medium",
              isUsingSmartLimit 
                ? "text-blue-900 dark:text-blue-100" 
                : "text-gray-700 dark:text-gray-300"
            )}>
              Smart Limit
            </h4>
            {isUsingSmartLimit && (
              <span className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full">
                Active
              </span>
            )}
          </div>
          <p className={cn(
            "text-sm mt-1",
            isUsingSmartLimit 
              ? "text-blue-700 dark:text-blue-300" 
              : "text-gray-600 dark:text-gray-400"
          )}>
            <span className="font-medium">{smartLimit.limit} conversations</span>
            <span className="mx-1">•</span>
            <span>{smartLimit.description}</span>
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {smartLimit.timeframe}
          </p>
        </div>
        <button
          type="button"
          onClick={handleOverrideToggle}
          disabled={disabled}
          className={cn(
            "flex items-center space-x-1 px-2 py-1 text-xs rounded transition-all",
            "hover:bg-white dark:hover:bg-gray-800",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            showOverride 
              ? "text-gray-600 dark:text-gray-400" 
              : "text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
          )}
          title={showOverride ? "Use smart limit" : "Set custom limit"}
        >
          <Settings className="w-3 h-3" />
          <span>{showOverride ? "Auto" : "Custom"}</span>
        </button>
      </div>

      {/* Override Input */}
      {showOverride && (
        <div className="ml-8 space-y-2">
          <label htmlFor="override-limit" className="block text-sm text-gray-600 dark:text-gray-400">
            Custom limit (leave blank to use smart limit):
          </label>
          <input
            id="override-limit"
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            value={overrideValue}
            onChange={(e) => {
              const value = e.target.value.replace(/[^0-9]/g, '')
              handleOverrideChange(value)
            }}
            placeholder="e.g., 150"
            className="w-32 px-3 py-1.5 border border-input rounded text-sm bg-background"
            disabled={disabled}
          />
          {overrideValue && parseInt(overrideValue) > 500 && (
            <p className="text-xs text-amber-600 dark:text-amber-400">
              Large limits may take longer to process and cost more
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// Smart limit calculation logic (mirrors backend)
function calculateSmartLimit(query: string): SmartLimitInfo {
  const queryLower = query.toLowerCase()
  
  // Simple timeframe detection (simplified version of backend logic)
  if (/\b(today|yesterday)\b/.test(queryLower)) {
    return {
      limit: 100,
      description: "Short timeframe",
      timeframe: queryLower.includes('today') ? 'Today' : 'Yesterday'
    }
  }
  
  if (/\b(this\s+week|last\s+week|7\s+days?)\b/.test(queryLower)) {
    return {
      limit: 300,
      description: "Weekly timeframe", 
      timeframe: "This/last week"
    }
  }
  
  if (/\b(this\s+month|last\s+month|30\s+days?)\b/.test(queryLower)) {
    return {
      limit: 500,
      description: "Monthly timeframe",
      timeframe: "This/last month"
    }
  }
  
  if (/\b(last|past)\s+\d+\s+(hours?|days?|weeks?|months?)\b/.test(queryLower)) {
    const match = queryLower.match(/\b(last|past)\s+(\d+)\s+(hours?|days?|weeks?|months?)\b/)
    if (match) {
      const quantity = parseInt(match[2])
      const unit = match[3]
      
      if (unit.includes('hour')) {
        return {
          limit: 100,
          description: "Short timeframe",
          timeframe: `Last ${quantity} ${unit}`
        }
      } else if (unit.includes('day')) {
        if (quantity <= 7) {
          return {
            limit: 300,
            description: "Weekly timeframe",
            timeframe: `Last ${quantity} ${unit}`
          }
        } else {
          return {
            limit: 500,
            description: "Extended timeframe",
            timeframe: `Last ${quantity} ${unit}`
          }
        }
      } else if (unit.includes('week')) {
        return {
          limit: 500,
          description: "Extended timeframe", 
          timeframe: `Last ${quantity} ${unit}`
        }
      } else if (unit.includes('month')) {
        return {
          limit: 500,
          description: "Extended timeframe",
          timeframe: `Last ${quantity} ${unit}`
        }
      }
    }
  }
  
  // Default case
  return {
    limit: 500,
    description: "General timeframe",
    timeframe: "Last 30 days (default)"
  }
}