import { useState, useEffect } from 'react'
import { ChevronDown, ChevronUp, Check, X, Eye, EyeOff, AlertTriangle } from 'lucide-react'
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

export function ApiKeySetup() {
  const { 
    intercomToken, 
    openaiKey, 
    setIntercomToken, 
    setOpenaiKey,
    getSessionId
  } = useAppStore()
  
  const [showTokens, setShowTokens] = useState(false)
  const [isExpanded, setIsExpanded] = useState(true)
  const [validation, setValidation] = useState<ApiKeyValidation>({
    intercom: null,
    openai: null,
    loading: false
  })
  
  const isConfigured = intercomToken && openaiKey
  const isValidated = validation.intercom?.valid && validation.openai?.valid
  
  // Auto-collapse after successful validation
  useEffect(() => {
    if (isValidated && isConfigured) {
      const timer = setTimeout(() => setIsExpanded(false), 2000)
      return () => clearTimeout(timer)
    }
  }, [isValidated, isConfigured])
  
  // Auto-expand if keys are cleared
  useEffect(() => {
    if (!isConfigured) {
      setIsExpanded(true)
      setValidation({ intercom: null, openai: null, loading: false })
    }
  }, [isConfigured])
  
  const validateApiKeys = async () => {
    if (!intercomToken || !openaiKey) return
    
    setValidation(prev => ({ ...prev, loading: true }))
    
    try {
      const response = await fetch('/api/validate', {
        headers: {
          'X-Session-ID': getSessionId(),
          'Content-Type': 'application/json'
        },
        method: 'POST',
        body: JSON.stringify({
          intercom_token: intercomToken,
          openai_key: openaiKey
        })
      })
      
      const data = await response.json()
      
      setValidation({
        intercom: {
          valid: data.connectivity?.intercom_api === 'reachable',
          message: data.connectivity?.intercom_api === 'reachable' 
            ? 'Connected successfully'
            : data.connectivity?.intercom_api === 'unauthorized'
            ? 'Invalid token or permissions'
            : 'Connection failed'
        },
        openai: {
          valid: data.connectivity?.openai_api === 'reachable',
          message: data.connectivity?.openai_api === 'reachable'
            ? 'Connected successfully'
            : data.connectivity?.openai_api === 'unauthorized'
            ? 'Invalid API key'
            : 'Connection failed'
        },
        loading: false
      })
    } catch (error) {
      setValidation({
        intercom: { valid: false, message: 'Validation failed' },
        openai: { valid: false, message: 'Validation failed' },
        loading: false
      })
    }
  }
  
  const getStatusIcon = () => {
    if (validation.loading) {
      return <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
    }
    if (isValidated) {
      return <Check className="w-4 h-4 text-green-500" />
    }
    if (isConfigured && !isValidated && validation.intercom && validation.openai) {
      return <X className="w-4 h-4 text-red-500" />
    }
    if (isConfigured) {
      return <AlertTriangle className="w-4 h-4 text-yellow-500" />
    }
    return <div className="w-2 h-2 bg-red-500 rounded-full" />
  }
  
  const getStatusText = () => {
    if (validation.loading) return 'Validating...'
    if (isValidated) return 'API keys validated'
    if (isConfigured && validation.intercom && validation.openai) return 'Validation failed'
    if (isConfigured) return 'Ready to validate'
    return 'API keys required'
  }

  return (
    <div className="bg-card border rounded-lg overflow-hidden">
      {/* Header - Always visible */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-3">
          <h2 className="text-lg font-semibold">API Configuration</h2>
          {getStatusIcon()}
          <span className="text-sm text-gray-600 dark:text-gray-400">{getStatusText()}</span>
        </div>
        
        <div className="flex items-center space-x-2">
          {isConfigured && !isExpanded && (
            <div className="flex items-center space-x-1 text-xs text-gray-600 dark:text-gray-400">
              <span>{intercomToken.slice(0, 8)}...</span>
              <span>•</span>
              <span>{openaiKey.slice(0, 8)}...</span>
            </div>
          )}
          {isExpanded ? 
            <ChevronUp className="w-4 h-4 text-muted-foreground" /> : 
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          }
        </div>
      </div>
      
      {/* Collapsible content */}
      {isExpanded && (
        <div className="border-t p-4 space-y-4">
          <div className="space-y-4">
            <div>
              <label htmlFor="intercom-token" className="block text-sm font-medium mb-2">
                Intercom Access Token
              </label>
              <div className="relative">
                <input
                  id="intercom-token"
                  type={showTokens ? "text" : "password"}
                  value={intercomToken}
                  onChange={(e) => {
                    setIntercomToken(e.target.value)
                    setValidation(prev => ({ ...prev, intercom: null }))
                  }}
                  placeholder="Enter your Intercom access token"
                  className={cn(
                    "w-full px-3 py-2 pr-10 border rounded-md bg-background text-sm transition-colors",
                    "focus:ring-2 focus:ring-ring focus:border-transparent",
                    validation.intercom?.valid === false 
                      ? "border-red-500 focus:ring-red-500/20" 
                      : validation.intercom?.valid === true
                      ? "border-green-500 focus:ring-green-500/20"
                      : "border-input"
                  )}
                />
                {validation.intercom && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    {validation.intercom.valid ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <X className="w-4 h-4 text-red-500" />
                    )}
                  </div>
                )}
              </div>
              {validation.intercom && (
                <p className={cn(
                  "text-xs mt-1",
                  validation.intercom.valid ? "text-green-600" : "text-red-600"
                )}>
                  {validation.intercom.message}
                </p>
              )}
            </div>
            
            <div>
              <label htmlFor="openai-key" className="block text-sm font-medium mb-2">
                OpenAI API Key
              </label>
              <div className="relative">
                <input
                  id="openai-key"
                  type={showTokens ? "text" : "password"}
                  value={openaiKey}
                  onChange={(e) => {
                    setOpenaiKey(e.target.value)
                    setValidation(prev => ({ ...prev, openai: null }))
                  }}
                  placeholder="Enter your OpenAI API key (sk-...)"
                  className={cn(
                    "w-full px-3 py-2 pr-10 border rounded-md bg-background text-sm transition-colors",
                    "focus:ring-2 focus:ring-ring focus:border-transparent",
                    validation.openai?.valid === false 
                      ? "border-red-500 focus:ring-red-500/20" 
                      : validation.openai?.valid === true
                      ? "border-green-500 focus:ring-green-500/20"
                      : "border-input"
                  )}
                />
                {validation.openai && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    {validation.openai.valid ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <X className="w-4 h-4 text-red-500" />
                    )}
                  </div>
                )}
              </div>
              {validation.openai && (
                <p className={cn(
                  "text-xs mt-1",
                  validation.openai.valid ? "text-green-600" : "text-red-600"
                )}>
                  {validation.openai.message}
                </p>
              )}
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => setShowTokens(!showTokens)}
                  className="flex items-center space-x-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
                >
                  {showTokens ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                  <span>{showTokens ? 'Hide' : 'Show'} keys</span>
                </button>
              </div>
              
              <button
                onClick={validateApiKeys}
                disabled={!isConfigured || validation.loading}
                className={cn(
                  "px-4 py-2 text-sm font-medium rounded-md transition-all",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  isValidated
                    ? "bg-green-100 text-green-700 border border-green-200 hover:bg-green-200"
                    : "bg-primary text-primary-foreground hover:bg-primary/90"
                )}
              >
                {validation.loading ? (
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    <span>Validating...</span>
                  </div>
                ) : isValidated ? (
                  <div className="flex items-center space-x-2">
                    <Check className="w-3 h-3" />
                    <span>Validated</span>
                  </div>
                ) : (
                  'Validate API Keys'
                )}
              </button>
            </div>
          </div>
          
          <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1 pt-2 border-t">
            <p>• Keys are stored locally in your browser</p>
            <p>• Data is automatically deleted after 30 days</p>
            <p>• Never share your API keys with others</p>
          </div>
        </div>
      )}
    </div>
  )
}
