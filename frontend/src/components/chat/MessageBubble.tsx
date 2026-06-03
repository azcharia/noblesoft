/**
 * Message Bubble Component
 * Displays individual chat messages
 */
'use client'

import { User, Bot } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { SourcesPanel } from './SourcesPanel'
import ReactMarkdown from 'react-markdown'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: Array<{
    type: string
    content: string
    metadata: Record<string, any>
  }>
  retrievedCount?: number
}

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  
  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-accent shadow-accent">
          <Bot className="w-5 h-5 text-white" />
        </div>
      )}
      
      <div className={`flex flex-col gap-2 max-w-[70%] ${isUser ? 'items-end' : 'items-start'}`}>
        <Card
          className={`p-4 shadow-md ${
            isUser
              ? 'border-transparent bg-blue-700 text-white'
              : 'border-slate-300 bg-white text-slate-900'
          }`}
        >
          <div className={`prose md:prose-lg max-w-none break-words ${isUser ? 'text-white' : 'text-slate-900 font-medium'}`}>
            <ReactMarkdown>
              {message.content}
            </ReactMarkdown>
          </div>
        </Card>
        
        {/* Sources panel for assistant messages */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourcesPanel
            sources={message.sources}
            retrievedCount={message.retrievedCount || 0}
          />
        )}
        
        <span className="text-sm font-bold text-slate-600">
          {message.timestamp.toLocaleTimeString('id-ID', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
      
      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
          <User className="w-5 h-5 text-muted-foreground" />
        </div>
      )}
    </div>
  )
}
