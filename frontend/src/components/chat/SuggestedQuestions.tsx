/**
 * Suggested Questions Component
 * Displays clickable suggested questions in a compact pill format
 */
'use client'

import { Sparkles } from 'lucide-react'

interface SuggestedQuestionsProps {
  suggestions: string[]
  onSelect: (question: string) => void
}

export function SuggestedQuestions({ suggestions, onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="w-full">
      <div className="flex items-center gap-2 mb-3 justify-center">
        <Sparkles className="h-4 w-4 text-brand-blue" />
        <span className="text-sm font-bold text-muted-foreground uppercase tracking-wider">
          Mungkin Anda ingin bertanya:
        </span>
      </div>
      
      <div className="flex flex-wrap gap-2 justify-center">
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            onClick={() => onSelect(suggestion)}
            className="px-4 py-2 text-sm font-semibold bg-background border border-border rounded-full hover:border-brand-blue hover:bg-muted transition-all active:scale-95 shadow-sm text-foreground text-left"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )
}
