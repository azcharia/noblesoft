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
      <div className="flex items-center gap-2 mb-4 justify-center">
        <Sparkles className="h-5 w-5 text-accent" />
        <span className="text-base font-bold text-slate-700">
          Pertanyaan yang disarankan:
        </span>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {suggestions.map((suggestion, index) => (
          <Button
            key={index}
            variant="outline"
            onClick={() => onSelect(suggestion)}
            className="h-auto min-h-[56px] justify-start border-slate-300 px-4 py-3 text-left hover:border-brand-blue hover:bg-slate-50 shadow-sm"
          >
            <span className="text-base font-semibold text-slate-900">{suggestion}</span>
          </Button>
        ))}
      </div>
    </div>
  )
}
