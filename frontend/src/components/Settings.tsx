import { useState } from 'react'
import { Settings as SettingsIcon, X, Eye, EyeOff, Check, AlertTriangle } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { cn } from '../lib/utils'

interface ValidationResult {
  valid: boolean
  message: string
}

interface ApiKeyValidation {
  intercom: ValidationResult | null
  openai: ValidationResult | null
  loading: boolean
}

export function Settings() {
  const { 
    maxConversations, 
    setMaxConversations,
    intercomToken,
    openaiKey,
    setIntercomToken,
    setOpenaiKey,
    getSessionId
  } = useAppStore()
  const [isOpen, setIsOpen] = useState(false)
  const [localMaxConversations, setLocalMaxConversations] = useState(
    maxConversations?.toString() || ''
  )
  const [showIntercomToken, setShowIntercomToken] = useState(false)
  const [showOpenAIKey, setShowOpenAIKey] = useState(false)
  const [localIntercomToken, setLocalIntercomToken] = useState(intercomToken)
  const [localOpenAIKey, setLocalOpenAIKey] = useState(openaiKey)
  const [validation, setValidation] = useState<ApiKeyValidation>({
    intercom: null,
    openai: null,
    loading: false
  })

  const validateAndSaveApiKeys = async () => {
    if (!localIntercomToken || !localOpenAIKey) {
      // Just save without validation if either is empty
      setIntercomToken(localIntercomToken)
      setOpenaiKey(localOpenAIKey)
      return true
    }
    
    setValidation(prev => ({ ...prev, loading: true }))
    
    try {
      const response = await fetch('/api/validate', {
        headers: {
          'X-Session-ID': getSessionId(),
          'Content-Type': 'application/json'
        },
        method: 'POST',
        body: JSON.stringify({
          intercom_token: localIntercomToken,
          openai_key: localOpenAIKey
        })
      })
      
      const data = await response.json()
      
      const intercomValid = data.connectivity?.intercom_api === 'reachable'
      const openaiValid = data.connectivity?.openai_api === 'reachable'
      
      setValidation({
        intercom: {
          valid: intercomValid,
          message: intercomValid
            ? 'Connected successfully'
            : data.connectivity?.intercom_api === 'unauthorized'
            ? 'Invalid token or permissions'
            : 'Connection failed'
        },
        openai: {
          valid: openaiValid,
          message: openaiValid
            ? 'Connected successfully'
            : data.connectivity?.openai_api === 'unauthorized'
            ? 'Invalid API key'
            : 'Connection failed'
        },
        loading: false
      })
      
      // Save the keys regardless of validation result
      setIntercomToken(localIntercomToken)
      setOpenaiKey(localOpenAIKey)
      
      return intercomValid && openaiValid
    } catch (error) {
      setValidation({
        intercom: { valid: false, message: 'Validation failed' },
        openai: { valid: false, message: 'Validation failed' },
        loading: false
      })
      return false
    }
  }

  const handleSave = async () => {
    // Save conversation limit
    const value = localMaxConversations.trim()
    if (value === '') {
      setMaxConversations(null) // No limit
    } else {
      const num = parseInt(value, 10)
      if (!isNaN(num) && num > 0) {
        setMaxConversations(Math.min(num, 1000)) // Cap at 1000
      }
    }
    
    // Validate and save API keys
    await validateAndSaveApiKeys()
    
    setIsOpen(false)
  }

  const handleCancel = () => {
    setLocalMaxConversations(maxConversations?.toString() || '')
    setLocalIntercomToken(intercomToken)
    setLocalOpenAIKey(openaiKey)
    setValidation({ intercom: null, openai: null, loading: false })
    setIsOpen(false)
  }
  
  const getInputBorderColor = (value: string, validationResult: ValidationResult | null) => {
    if (!value) return 'border-input'
    if (!validationResult) return 'border-input'
    return validationResult.valid ? 'border-green-500' : 'border-red-500'
  }
  
  const hasKeysConfigured = intercomToken && openaiKey
  const keysChanged = localIntercomToken !== intercomToken || localOpenAIKey !== openaiKey

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center space-x-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors border border-transparent hover:border-border rounded-md"
        title="Settings"
      >
        <SettingsIcon className="w-4 h-4" />
        <span>Settings</span>
      </button>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-card border rounded-lg max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Settings</h2>
          <button
            onClick={handleCancel}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-6">
          {/* API Keys Section */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              API Keys
              {hasKeysConfigured && !keysChanged && (
                <span className="text-green-600 dark:text-green-400">
                  <Check className="w-4 h-4" />
                </span>
              )}
              {keysChanged && (
                <span className="text-yellow-600 dark:text-yellow-400">
                  <AlertTriangle className="w-3 h-3" />
                </span>
              )}
            </h3>
            
            <div>
              <label htmlFor="settings-intercom-token" className="block text-sm font-medium mb-2">
                Intercom Access Token
              </label>
              <div className="relative">
                <input
                  id="settings-intercom-token"
                  type={showIntercomToken ? 'text' : 'password'}
                  value={localIntercomToken}
                  onChange={(e) => {
                    setLocalIntercomToken(e.target.value)
                    setValidation(prev => ({ ...prev, intercom: null }))
                  }}
                  placeholder="dG9rOmU5YzBlZmJiX2FiY2RlZjEyMzQ1Njc4OTA..."
                  className={cn(
                    "w-full px-3 py-2 pr-10 border rounded-md bg-background font-mono text-sm transition-colors",
                    "focus:ring-2 focus:ring-ring focus:border-transparent",
                    getInputBorderColor(localIntercomToken, validation.intercom)
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowIntercomToken(!showIntercomToken)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showIntercomToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {validation.intercom && (
                <p className={cn(
                  "text-xs mt-1",
                  validation.intercom.valid ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                )}>
                  {validation.intercom.message}
                </p>
              )}
            </div>
            
            <div>
              <label htmlFor="settings-openai-key" className="block text-sm font-medium mb-2">
                OpenAI API Key
              </label>
              <div className="relative">
                <input
                  id="settings-openai-key"
                  type={showOpenAIKey ? 'text' : 'password'}
                  value={localOpenAIKey}
                  onChange={(e) => {
                    setLocalOpenAIKey(e.target.value)
                    setValidation(prev => ({ ...prev, openai: null }))
                  }}
                  placeholder="sk-proj-abcdefghijklmnopqrstuvwxyz123456..."
                  className={cn(
                    "w-full px-3 py-2 pr-10 border rounded-md bg-background font-mono text-sm transition-colors",
                    "focus:ring-2 focus:ring-ring focus:border-transparent",
                    getInputBorderColor(localOpenAIKey, validation.openai)
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowOpenAIKey(!showOpenAIKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showOpenAIKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {validation.openai && (
                <p className={cn(
                  "text-xs mt-1",
                  validation.openai.valid ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                )}>
                  {validation.openai.message}
                </p>
              )}
            </div>
            
            {keysChanged && (
              <button
                onClick={validateAndSaveApiKeys}
                disabled={validation.loading || (!localIntercomToken || !localOpenAIKey)}
                className={cn(
                  "w-full py-2 px-4 rounded-md font-medium text-sm transition-colors",
                  (!localIntercomToken || !localOpenAIKey)
                    ? "bg-muted text-muted-foreground cursor-not-allowed"
                    : "bg-yellow-600 dark:bg-yellow-700 text-white hover:bg-yellow-700 dark:hover:bg-yellow-800"
                )}
              >
                {validation.loading ? (
                  <>
                    <span className="animate-spin mr-2">⚪</span>
                    Validating...
                  </>
                ) : (
                  'Validate API Keys'
                )}
              </button>
            )}
          </div>
          
          {/* Divider */}
          <div className="border-t" />
          
          {/* Conversation Limit Section */}
          <div>
            <h3 className="text-sm font-semibold mb-4">Query Settings</h3>
            <div>
              <label htmlFor="max-conversations" className="block text-sm font-medium mb-2">
                Conversation Limit
              </label>
              <input
                id="max-conversations"
                type="number"
                min="1"
                max="1000"
                value={localMaxConversations}
                onChange={(e) => setLocalMaxConversations(e.target.value)}
                placeholder="No limit (leave empty)"
                className={cn(
                  "w-full px-3 py-2 border rounded-md bg-background text-sm transition-colors",
                  "focus:ring-2 focus:ring-ring focus:border-transparent border-input"
                )}
              />
              <p className="text-xs text-muted-foreground mt-1">
                Leave empty for no limit. Maximum: 1000 conversations.
              </p>
            </div>
          </div>
          
          {/* Privacy Notice */}
          <div className="bg-muted/30 rounded-md p-3 text-xs text-muted-foreground">
            <p className="mb-1">🔒 Your API keys are stored locally in your browser.</p>
            <p>🗑️ Keys are automatically deleted after 30 days for security.</p>
          </div>
        </div>

        <div className="flex justify-end space-x-2 mt-6">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={validation.loading}
            className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  )
}
