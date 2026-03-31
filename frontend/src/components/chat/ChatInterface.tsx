/**
 * Chat Interface Component
 * Beautiful, modern chat UI for AI Assistant
 */
'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { apiClient, APIError, type ChatResponse } from '@/lib/api/client'
import { getSessionToken } from '@/lib/supabase/client'
import { MessageBubble } from './MessageBubble'
import { SuggestedQuestions } from './SuggestedQuestions'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: ChatResponse['sources']
  retrievedCount?: number
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
  
  const loadSuggestions = useCallback(async (attempt: number = 0) => {
    try {
      const token = await getSessionToken({
        retries: 2,
        ensureHydrated: true,
        forceRefresh: attempt > 0,
      })

      if (!token) {
        throw new APIError('No authentication token available', 401)
      }

      const data = await apiClient.chat.getSuggestions()
      setSuggestionsError(null)
      setSuggestions(data.suggestions)
    } catch (error: any) {
      if (error instanceof APIError && error.status === 401 && attempt < 3) {
        await new Promise((resolve) => setTimeout(resolve, 700 * (attempt + 1)))
        return loadSuggestions(attempt + 1)
      }

      setSuggestions([])
      setSuggestionsError(
        error?.message || 'Gagal memuat pertanyaan yang disarankan. Silakan refresh halaman.'
      )
      console.error('Failed to load suggestions:', error)
    }
  }, [])

  // Load suggestions on mount
  useEffect(() => {
    loadSuggestions()
  }, [loadSuggestions])
  
  const sendMessage = async (messageText?: string) => {
    const text = messageText || input.trim()
    if (!text || isLoading) return
    
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    }
    
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    
    try {
      // Build conversation history
      const conversationHistory = messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }))
      
      // Send to API
      const response = await apiClient.chat.send(text, conversationHistory)
      
      // Add assistant message
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        sources: response.sources,
        retrievedCount: response.retrieved_count,
      }
      
      setMessages((prev) => [...prev, assistantMessage])
    } catch (error: any) {
      // Add error message
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: error.message || 'Maaf, terjadi kesalahan. Silakan coba lagi.',
        timestamp: new Date(),
      }
      
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      textareaRef.current?.focus()
    }
  }
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }
  
  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion)
  }
  
  return (
    <div className="flex-1 flex flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          // Empty state
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-accent shadow-accent">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <h3 className="mb-2 text-xl font-semibold text-foreground">
              NobleSoft AI Assistant
            </h3>
            <p className="mb-8 max-w-md text-muted-foreground">
              Tanyakan apa saja tentang inventory, invoice, dan data bisnis Anda.
              AI akan menjawab berdasarkan data aktual perusahaan Anda.
            </p>

            {suggestionsError && (
              <p className="mb-4 max-w-md rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                {suggestionsError}
              </p>
            )}
            
            {/* Suggested questions */}
            {suggestions.length > 0 && (
              <SuggestedQuestions
                suggestions={suggestions}
                onSelect={handleSuggestionClick}
              />
            )}
          </div>
        ) : (
          // Messages
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            
            {/* Loading indicator */}
            {isLoading && (
              <div className="flex items-center gap-3 text-muted-foreground">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span className="text-sm">AI sedang berpikir...</span>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
      
      {/* Input area */}
      <div className="border-t border-border bg-muted/40 p-4">
        <div className="flex gap-3">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ketik pertanyaan Anda... (Enter untuk kirim, Shift+Enter untuk baris baru)"
            className="flex-1 min-h-[60px] max-h-[200px] resize-none"
            disabled={isLoading}
          />
          <Button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isLoading}
            size="lg"
            className="px-6"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </Button>
        </div>
        
        <p className="mt-2 text-xs text-muted-foreground">
          AI hanya menjawab berdasarkan data perusahaan Anda. Tidak ada hallucination.
        </p>
      </div>
    </div>
  )
}
