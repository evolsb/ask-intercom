import { useState, useEffect } from 'react'
import { ChevronRight, Eye, EyeOff, Check, X } from 'lucide-react'
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

export function FirstTimeSetup() {
  const { 
    intercomToken, 
    openaiKey, 
    setIntercomToken, 
    setOpenaiKey,
    getSessionId
  } = useAppStore()
  
  const [showIntercomToken, setShowIntercomToken] = useState(false)
  const [showOpenAIKey, setShowOpenAIKey] = useState(false)
  const [localIntercomToken, setLocalIntercomToken] = useState(intercomToken)
  const [localOpenAIKey, setLocalOpenAIKey] = useState(openaiKey)
  const [validation, setValidation] = useState<ApiKeyValidation>({
    intercom: null,
    openai: null,
    loading: false
  })
  
  const isConfigured = intercomToken && openaiKey
  const hasLocalKeys = localIntercomToken && localOpenAIKey
  
  // Don't show if keys are already configured
  if (isConfigured) {
    return null
  }
  
  const validateApiKeys = async () => {
    if (!localIntercomToken || !localOpenAIKey) return
    
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
      
      // If both are valid, save the keys
      if (data.connectivity?.intercom_api === 'reachable' && 
          data.connectivity?.openai_api === 'reachable') {
        setIntercomToken(localIntercomToken)
        setOpenaiKey(localOpenAIKey)
      }
    } catch (error) {
      setValidation({
        intercom: { valid: false, message: 'Validation failed' },
        openai: { valid: false, message: 'Validation failed' },
        loading: false
      })
    }
  }
  
  const getInputBorderColor = (value: string, validationResult: ValidationResult | null) => {
    if (!value) return 'border-input'
    if (!validationResult) return 'border-input'
    return validationResult.valid ? 'border-green-500' : 'border-red-500'
  }
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-card border rounded-lg max-w-2xl w-full p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent dark:from-blue-400 dark:to-purple-400">
            Welcome to Ask Intercom
          </h1>
          <p className="text-muted-foreground">
            Let's get you set up with your API keys to start analyzing conversations
          </p>
        </div>
        
        <div className="space-y-6">
          <div>
            <label htmlFor="intercom-token" className="block text-sm font-medium mb-2">
              Intercom Access Token
            </label>
            <div className="relative">
              <input
                id="intercom-token"
                type={showIntercomToken ? 'text' : 'password'}
                value={localIntercomToken}
                onChange={(e) => setLocalIntercomToken(e.target.value)}
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
            <label htmlFor="openai-key" className="block text-sm font-medium mb-2">
              OpenAI API Key
            </label>
            <div className="relative">
              <input
                id="openai-key"
                type={showOpenAIKey ? 'text' : 'password'}
                value={localOpenAIKey}
                onChange={(e) => setLocalOpenAIKey(e.target.value)}
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
          
          <div className="bg-muted/30 rounded-md p-4 text-xs text-muted-foreground">
            <p className="mb-1">🔒 Your API keys are stored locally in your browser and never sent to our servers.</p>
            <p>🗑️ Keys are automatically deleted after 30 days for security.</p>
          </div>
          
          <button
            onClick={validateApiKeys}
            disabled={!hasLocalKeys || validation.loading}
            className={cn(
              "w-full py-2 px-4 rounded-md font-medium text-sm transition-colors flex items-center justify-center",
              hasLocalKeys
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            )}
          >
            {validation.loading ? (
              <>
                <span className="animate-spin mr-2">⚪</span>
                Validating...
              </>
            ) : (
              <>
                Continue
                <ChevronRight className="w-4 h-4 ml-1" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
