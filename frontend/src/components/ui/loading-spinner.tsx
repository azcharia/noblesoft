'use client'

/**
 * Loading Spinner Component
 * Reusable animated spinner with optional message text.
 */
export function LoadingSpinner({ message = 'Memuat data...' }: { message?: string }) {
  return (
    <div className="flex items-center gap-3 py-8 justify-center text-muted-foreground">
      <svg
        className="animate-spin h-5 w-5"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.37 0 0 5.37 0 12h4z"
        />
      </svg>
      <span className="text-sm">{message}</span>
    </div>
  )
}
