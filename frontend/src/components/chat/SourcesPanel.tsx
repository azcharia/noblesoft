/**
 * Sources Panel Component
 * Displays retrieved source documents used by AI
 */
'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, FileText, Package, Database } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface Source {
  type: string
  content: string
  metadata: Record<string, any>
}

interface SourcesPanelProps {
  sources: Source[]
  retrievedCount: number
}

export function SourcesPanel({ sources, retrievedCount }: SourcesPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'product':
        return <Package className="w-4 h-4" />
      case 'invoice':
        return <FileText className="w-4 h-4" />
      default:
        return <Database className="w-4 h-4" />
    }
  }
  
  const getSourceColor = (type: string) => {
    switch (type) {
      case 'product':
        return 'border-emerald-200 bg-emerald-50 text-emerald-700'
      case 'invoice':
        return 'border-accent/20 bg-accent/10 text-accent'
      default:
        return 'border-border bg-muted text-muted-foreground'
    }
  }
  
  return (
    <Card className="w-full border-border bg-muted/50 p-3">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full justify-between p-0 h-auto hover:bg-transparent"
      >
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-muted-foreground" />
          <span className="text-xs font-medium text-muted-foreground">
            {retrievedCount} sumber data digunakan
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </Button>
      
      {isExpanded && (
        <div className="mt-3 space-y-2">
          {sources.map((source, index) => (
            <div
              key={index}
              className={`p-2 rounded-lg border ${getSourceColor(source.type)}`}
            >
              <div className="flex items-center gap-2 mb-1">
                {getSourceIcon(source.type)}
                <Badge variant="outline" className="text-xs">
                  {source.type.toUpperCase()}
                </Badge>
              </div>
              <p className="line-clamp-2 text-xs leading-relaxed">
                {source.content}
              </p>
              {source.metadata && Object.keys(source.metadata).length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {Object.entries(source.metadata).slice(0, 3).map(([key, value]) => (
                    <span key={key} className="text-[11px] opacity-80">
                      {key}: {String(value)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
