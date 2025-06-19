import { useState, useEffect } from 'react'
import { Brain, Settings } from 'lucide-react'
import { cn } from '../lib/utils'

interface SmartLimitsProps {
  maxConversations: number | null
  onMaxConversationsChange: (value: number | null) => void
  disabled?: boolean
}

export function SmartLimits({ 
  maxConversations, 
  onMaxConversationsChange, 
  disabled = false 
}: SmartLimitsProps) {
  const [showManual, setShowManual] = useState(false)
  const [manualValue, setManualValue] = useState('')

  // Update manual value when maxConversations changes
  useEffect(() => {
    if (maxConversations !== null && maxConversations > 100) {
      setManualValue(maxConversations.toString())
      setShowManual(true)
    } else {
      setManualValue('')
      setShowManual(false)
    }
  }, [maxConversations])

  const handleToggle = () => {
    if (showManual) {
      // Switch to smart limits
      setShowManual(false)
      setManualValue('')
      onMaxConversationsChange(null)
    } else {
      // Switch to manual
      setShowManual(true)
      setManualValue('')
    }
  }

  const handleManualChange = (value: string) => {
    setManualValue(value)
    
    if (value === '') {
      onMaxConversationsChange(null) // Use smart limit
    } else {
      const num = parseInt(value)
      if (!isNaN(num) && num > 0) {
        onMaxConversationsChange(Math.min(num, 1000)) // Cap at 1000
      }
    }
  }

  const isUsingSmartLimit = maxConversations === null || maxConversations <= 100

  return (
    <div className="space-y-3">
      {/* Smart/Manual Toggle */}
      <div className={cn(
        "flex items-center justify-between p-3 rounded-lg border transition-all",
        isUsingSmartLimit 
          ? "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800" 
          : "bg-gray-50 dark:bg-gray-900/30 border-gray-200 dark:border-gray-700"
      )}>
        <div className="flex items-center space-x-3">
          <Brain className={cn(
            "w-5 h-5",
            isUsingSmartLimit 
              ? "text-blue-600 dark:text-blue-400" 
              : "text-gray-500 dark:text-gray-400"
          )} />
          <div>
            <div className="flex items-center space-x-2">
              <span className={cn(
                "text-sm font-medium",
                isUsingSmartLimit 
                  ? "text-blue-900 dark:text-blue-100" 
                  : "text-gray-700 dark:text-gray-300"
              )}>
                {isUsingSmartLimit ? 'Smart Limits' : 'Manual Limit'}
              </span>
              {isUsingSmartLimit && (
                <span className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full">
                  Active
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {isUsingSmartLimit 
                ? 'Automatically adjusts based on your query' 
                : 'Use a fixed number of conversations'
              }
            </p>
          </div>
        </div>
        
        <button
          type="button"
          onClick={handleToggle}
          disabled={disabled}
          className={cn(
            "flex items-center space-x-1 px-3 py-1.5 text-xs rounded transition-all",
            "hover:bg-white dark:hover:bg-gray-800 border",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            showManual 
              ? "text-gray-600 dark:text-gray-400 border-gray-300 dark:border-gray-600" 
              : "text-blue-600 dark:text-blue-400 border-blue-300 dark:border-blue-600"
          )}
        >
          <Settings className="w-3 h-3" />
          <span>{showManual ? "Use Smart Limits" : "Set Manual Limit"}</span>
        </button>
      </div>

      {/* Manual Input */}
      {showManual && (
        <div className="pl-8 space-y-2">
          <label htmlFor="manual-limit" className="block text-sm text-gray-600 dark:text-gray-400">
            Number of conversations:
          </label>
          <input
            id="manual-limit"
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            value={manualValue}
            onChange={(e) => {
              const value = e.target.value.replace(/[^0-9]/g, '')
              handleManualChange(value)
            }}
            placeholder="e.g., 100"
            className="w-32 px-3 py-1.5 border border-input rounded text-sm bg-background"
            disabled={disabled}
            required
          />
          {manualValue && parseInt(manualValue) > 500 && (
            <p className="text-xs text-amber-600 dark:text-amber-400">
              Large limits may take longer to process and cost more
            </p>
          )}
          {!manualValue && (
            <p className="text-xs text-red-600 dark:text-red-400">
              Please enter a number to use manual limits
            </p>
          )}
        </div>
      )}
    </div>
  )
}