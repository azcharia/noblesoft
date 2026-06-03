/**
 * Chat Interface Component
 * Beautiful, modern chat UI for AI Assistant
 */
'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, Sparkles, Mic, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { apiClient, APIError, type ChatResponse } from '@/lib/api/client'
import { getSessionToken } from '@/lib/supabase/client'
import { cn } from '@/lib/utils'
import { MessageBubble } from './MessageBubble'
import { SuggestedQuestions } from './SuggestedQuestions'
import { ConfirmationModal, type ConfirmationData } from './ConfirmationModal'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: ChatResponse['sources']
  retrievedCount?: number
}

interface ChatInterfaceProps {
  noBorder?: boolean
}

export function ChatInterface({ noBorder = false }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
  // Voice Recording State
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  // Confirmation Modal State
  const [confirmationData, setConfirmationData] = useState<ConfirmationData | null>(null)
  const [pendingAction, setPendingAction] = useState<any>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      // Supported MIME types priority
      const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/wav']
        .find(type => MediaRecorder.isTypeSupported(type)) || ''
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType })
        await handleTranscription(audioBlob)
        
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
      
      // Haptic Feedback
      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        navigator.vibrate(50)
      }
    } catch (err) {
      console.error('Microphone access denied:', err)
      alert('Akses mikrofon ditolak. Silakan izinkan akses mikrofon di pengaturan browser Anda untuk menggunakan fitur ini.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      
      // Haptic Feedback
      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        navigator.vibrate(50)
      }
    }
  }

  const QUICK_ACTIONS = [
    {
      label: '💰 Jual Barang',
      template: 'Saya ingin menjual [nama_barang] sebanyak [jumlah] ke [nama_pelanggan]',
    },
    {
      label: '📦 Tambah Stok',
      template: 'Tambah stok [nama_barang] sebanyak [jumlah]',
    },
    {
      label: '🔍 Cek Stok / Harga',
      template: 'Berapa stok dan harga [nama_barang]?',
    },
    {
      label: '📝 Catat Utang',
      template: 'Catat utang [nama_barang] sebanyak [jumlah] ke [nama_pelanggan]',
    },
    {
      label: '📊 Laporan Hari Ini',
      template: 'Tampilkan laporan ringkas penjualan hari ini',
    },
  ]

  const handleQuickAction = (template: string) => {
    setInput(template)
    // Focus the textarea and set cursor inside the first bracket if possible
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus()
        const firstBracketStart = template.indexOf('[')
        const firstBracketEnd = template.indexOf(']')
        if (firstBracketStart !== -1 && firstBracketEnd !== -1) {
          textareaRef.current.setSelectionRange(firstBracketStart, firstBracketEnd + 1)
        }
      }
    }, 10)
  }

  const handleTranscription = async (audioBlob: Blob) => {
    setIsTranscribing(true)
    try {
      const result = await apiClient.chat.transcribe(audioBlob)
      if (result.text) {
        setInput(prev => (prev ? `${prev} ${result.text}` : result.text))
      }
    } catch (error: any) {
      console.error('Transcription failed:', error)
      alert('Gagal memproses suara. Silakan coba lagi atau ketik manual.')
    } finally {
      setIsTranscribing(false)
    }
  }
  
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
      
      // Check if response contains confirmation data (execution_result or parsed from action)
      // Note: In production, the backend should return this structured data.
      // We check if it's a function call that needs confirmation
      if (response.execution_result?.requires_confirmation) {
        setConfirmationData(response.execution_result.confirmation_data)
        setPendingAction(response.execution_result.pending_action)
        setIsModalOpen(true)
      }
      
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
  
  const handleConfirm = async () => {
    if (!pendingAction) return
    setIsModalOpen(false)
    setIsLoading(true)
    
    try {
      const response = await apiClient.chat.confirm(pendingAction)
      
      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        sources: response.sources || [],
        retrievedCount: response.retrieved_count || 0,
      }
      
      setMessages((prev) => [...prev, assistantMessage])
      setPendingAction(null)
      setConfirmationData(null)
    } catch (error: any) {
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: error.message || 'Gagal menyimpan transaksi ke database. Silakan coba lagi.',
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
    <div className={cn(
      "flex-1 flex flex-col overflow-hidden",
      !noBorder && "rounded-2xl border border-border bg-card shadow-sm"
    )}>
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          // Empty state
          <div className="flex flex-col items-center justify-center h-full text-center py-4">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-accent shadow-accent">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <h3 className="mb-2 text-xl font-bold text-foreground">
              Asisten AI Toko
            </h3>
            <p className="mb-6 max-w-md text-base font-medium text-slate-600">
              Tanyakan apa saja tentang stok barang, nota, dan data toko Anda.
              AI akan menjawab berdasarkan data aktual toko Anda.
            </p>

            {suggestionsError && (
              <p className="mb-6 max-w-md rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm font-medium text-destructive">
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
              <div className="flex items-center gap-3 text-slate-700 p-5 bg-muted rounded-2xl w-fit border border-border">
                <Loader2 className="w-6 h-6 animate-spin text-brand-blue" />
                <span className="text-base font-bold animate-pulse">Sebentar ya, Asisten sedang mengecek catatan toko...</span>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
      
      {/* Input area */}
      <div className="border-t border-border bg-muted/40 p-4">
        {/* Quick Action Buttons */}
        <div className="flex items-center gap-3 overflow-x-auto pb-3 mb-1 no-scrollbar scroll-smooth">
          {QUICK_ACTIONS.map((action, index) => (
            <button
              key={index}
              onClick={() => handleQuickAction(action.template)}
              className="flex-shrink-0 px-5 py-3 min-h-[48px] bg-background border border-slate-300 rounded-full text-base font-bold text-slate-900 shadow-sm hover:bg-slate-50 hover:border-brand-blue transition-all active:scale-95"
            >
              {action.label}
            </button>
          ))}
        </div>

        <div className="flex gap-3 items-end">
          <Button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isTranscribing || isLoading}
            size="icon"
            className={cn(
              "h-12 w-12 rounded-full flex-shrink-0 transition-all duration-200",
              isRecording 
                ? "bg-destructive hover:bg-destructive/90 animate-pulse ring-4 ring-destructive/30" 
                : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
            )}
            title={isRecording ? "Hentikan Rekaman" : "Mulai Rekam Suara"}
          >
            {isTranscribing ? (
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
            ) : isRecording ? (
              <Square className="w-5 h-5 fill-current" />
            ) : (
              <Mic className="w-6 h-6" />
            )}
          </Button>

          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isRecording 
                ? "Sedang merekam suara..." 
                : isTranscribing 
                  ? "Sedang memproses suara..." 
                  : "Ketik pertanyaan Anda... (Enter untuk kirim)"
            }
            className="flex-1 min-h-[48px] max-h-[200px] resize-none text-base"
            disabled={isLoading || isRecording || isTranscribing}
          />
          <Button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isLoading || isRecording || isTranscribing}
            size="icon"
            className="h-12 w-12 rounded-full flex-shrink-0"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </Button>
        </div>
        
        <p className="mt-3 text-sm text-center text-muted-foreground font-medium">
          AI hanya menjawab berdasarkan data perusahaan Anda.
        </p>
      </div>

      <ConfirmationModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setPendingAction(null)
          setConfirmationData(null)
        }}
        onConfirm={handleConfirm}
        data={confirmationData}
      />
    </div>
  )
}
