/**
 * Environment variable validation for frontend runtime.
 */

type FrontendEnvKey =
  | 'NEXT_PUBLIC_SUPABASE_URL'
  | 'NEXT_PUBLIC_SUPABASE_ANON_KEY'
  | 'NEXT_PUBLIC_API_URL'

const rawEnv: Record<FrontendEnvKey, string | undefined> = {
  NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
  NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
}

function getRequiredEnv(name: FrontendEnvKey): string {
  const value = rawEnv[name]

  if (!value || !value.trim()) {
    throw new Error(`Missing required environment variable: ${name}`)
  }

  const lowered = value.toLowerCase()
  const placeholderMarkers = ['your-', 'your_', 'example', 'changeme', 'replace', 'placeholder']
  if (placeholderMarkers.some((marker) => lowered.includes(marker))) {
    throw new Error(`Environment variable ${name} appears to be a placeholder value`)
  }

  return value
}

export const env = {
  NEXT_PUBLIC_SUPABASE_URL: getRequiredEnv('NEXT_PUBLIC_SUPABASE_URL'),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: getRequiredEnv('NEXT_PUBLIC_SUPABASE_ANON_KEY'),
  NEXT_PUBLIC_API_URL: getRequiredEnv('NEXT_PUBLIC_API_URL'),
}
