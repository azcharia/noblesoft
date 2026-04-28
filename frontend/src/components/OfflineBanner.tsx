'use client'

/**
 * Offline Banner Component
 * Fixed banner displayed when the browser loses network connectivity.
 */
import { useOnlineStatus } from '@/hooks/useOnlineStatus'

export function OfflineBanner() {
  const isOnline = useOnlineStatus()

  if (isOnline) return null

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-destructive text-destructive-foreground py-2 px-4 text-center text-sm font-medium shadow-md">
      ⚠️ Anda sedang offline. Beberapa fitur mungkin tidak tersedia.
    </div>
  )
}
