import { useState } from 'react'
import { Settings as SettingsIcon, X } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { cn } from '../lib/utils'

export function Settings() {
  const { maxConversations, setMaxConversations } = useAppStore()
  const [isOpen, setIsOpen] = useState(false)
  const [localMaxConversations, setLocalMaxConversations] = useState(
    maxConversations?.toString() || ''
  )

  const handleSave = () => {
    const value = localMaxConversations.trim()
    if (value === '') {
      setMaxConversations(null) // No limit
    } else {
      const num = parseInt(value, 10)
      if (!isNaN(num) && num > 0) {
        setMaxConversations(Math.min(num, 1000)) // Cap at 1000
      }
    }
    setIsOpen(false)
  }

  const handleCancel = () => {
    setLocalMaxConversations(maxConversations?.toString() || '')
    setIsOpen(false)
  }

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

        <div className="space-y-4">
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

        <div className="flex justify-end space-x-2 mt-6">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 rounded-md transition-colors"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  )
}
