/**
 * Suggested Questions Component
 * Displays clickable suggested questions
 */
'use client'

import { Button } from '@/components/ui/button'
import { Sparkles } from 'lucide-react'

interface SuggestedQuestionsProps {
  suggestions: string[]
  onSelect: (question: string) => void
}

export function SuggestedQuestions({ suggestions, onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="w-full max-w-2xl">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="h-4 w-4 text-accent" />
        <span className="text-sm font-medium text-muted-foreground">
          Pertanyaan yang disarankan:
        </span>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {suggestions.map((suggestion, index) => (
          <Button
            key={index}
            variant="outline"
            onClick={() => onSelect(suggestion)}
            className="h-auto justify-start border-border/80 px-3.5 py-2 text-left hover:border-accent/30 hover:bg-accent/5"
          >
            <span className="text-xs md:text-sm text-foreground">{suggestion}</span>
          </Button>
        ))}
      </div>
    </div>
  )
}
