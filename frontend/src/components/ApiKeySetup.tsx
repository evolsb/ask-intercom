import { useState } from 'react'
import { useAppStore } from '../store/useAppStore'
import { cn } from '../lib/utils'

export function ApiKeySetup() {
  const { intercomToken, openaiKey, setIntercomToken, setOpenaiKey } = useAppStore()
  const [showTokens, setShowTokens] = useState(false)
  
  const isConfigured = intercomToken && openaiKey

  return (
    <div className="bg-card border rounded-lg p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">API Configuration</h2>
        <div className={cn(
          "w-2 h-2 rounded-full",
          isConfigured ? "bg-green-500" : "bg-red-500"
        )} />
      </div>
      
      <div className="space-y-4">
        <div>
          <label htmlFor="intercom-token" className="block text-sm font-medium mb-2">
            Intercom Access Token
          </label>
          <input
            id="intercom-token"
            type={showTokens ? "text" : "password"}
            value={intercomToken}
            onChange={(e) => setIntercomToken(e.target.value)}
            placeholder="Enter your Intercom access token"
            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:ring-2 focus:ring-ring focus:border-transparent"
          />
        </div>
        
        <div>
          <label htmlFor="openai-key" className="block text-sm font-medium mb-2">
            OpenAI API Key
          </label>
          <input
            id="openai-key"
            type={showTokens ? "text" : "password"}
            value={openaiKey}
            onChange={(e) => setOpenaiKey(e.target.value)}
            placeholder="Enter your OpenAI API key"
            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:ring-2 focus:ring-ring focus:border-transparent"
          />
        </div>
        
        <div className="flex items-center space-x-2">
          <input
            id="show-tokens"
            type="checkbox"
            checked={showTokens}
            onChange={(e) => setShowTokens(e.target.checked)}
            className="rounded border-input"
          />
          <label htmlFor="show-tokens" className="text-sm text-muted-foreground">
            Show API keys
          </label>
        </div>
      </div>
      
      <div className="text-xs text-muted-foreground space-y-1">
        <p>• Keys are stored locally in your browser</p>
        <p>• Data is automatically deleted after 30 days</p>
        <p>• Never share your API keys with others</p>
      </div>
    </div>
  )
}
