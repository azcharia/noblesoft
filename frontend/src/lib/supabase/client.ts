/**
 * Supabase Browser Client
 * Handles authentication and session management
 */
import { createBrowserClient } from '@supabase/ssr'
import { env } from '@/lib/env'
import type { Database } from '@/types/database'

let browserClient: ReturnType<typeof createBrowserClient<Database>> | null = null
let sessionHydrated = false
let hydrationInFlight: Promise<void> | null = null
let primedAccessToken: string | null = null

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// Create singleton Supabase client
export const createClient = () => {
  if (!browserClient) {
    browserClient = createBrowserClient<Database>(
      env.NEXT_PUBLIC_SUPABASE_URL,
      env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    )
  }
  return browserClient
}

// Export default client instance
export const supabase = createClient()

supabase.auth.onAuthStateChange((event) => {
  if (event === 'SIGNED_OUT') {
    sessionHydrated = false
    primedAccessToken = null
    return
  }

  if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED' || event === 'INITIAL_SESSION') {
    sessionHydrated = true
  }
})

/**
 * Prime token immediately after login to avoid stale-session races before hydration settles.
 */
export function primeSessionToken(token: string | null) {
  primedAccessToken = token
  if (token) {
    sessionHydrated = true
  }
}

async function ensureSessionHydrated(maxWaitMs: number = 2000): Promise<void> {
  if (sessionHydrated) return

  if (hydrationInFlight) {
    await hydrationInFlight
    return
  }

  hydrationInFlight = (async () => {
    const started = Date.now()
    while (Date.now() - started < maxWaitMs) {
      const {
        data: { session },
        error,
      } = await supabase.auth.getSession()

      if (!error && session?.access_token) {
        sessionHydrated = true
        return
      }

      await sleep(120)
    }
  })()

  try {
    await hydrationInFlight
  } finally {
    hydrationInFlight = null
  }
}

export interface SessionTokenOptions {
  retries?: number
  forceRefresh?: boolean
  ensureHydrated?: boolean
}

/**
 * Get current session token
 * Used by API client to attach to requests
 */
export async function getSessionToken(options: SessionTokenOptions = {}): Promise<string | null> {
  const retries = Math.max(0, options.retries ?? 2)
  const forceRefresh = Boolean(options.forceRefresh)
  const shouldHydrate = options.ensureHydrated !== false

  if (primedAccessToken && !forceRefresh) {
    return primedAccessToken
  }

  if (shouldHydrate) {
    await ensureSessionHydrated()
  }

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    // When forced, refresh first so we do not keep returning a stale cached token.
    if (forceRefresh) {
      const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession()
      if (!refreshError && refreshData.session?.access_token) {
        sessionHydrated = true
        primedAccessToken = refreshData.session.access_token
        return refreshData.session.access_token
      }
    }

    const {
      data: { session },
      error,
    } = await supabase.auth.getSession()

    const accessToken = session?.access_token
    if (!error && accessToken) {
      const expiresAt = typeof session.expires_at === 'number' ? session.expires_at : null
      const expiresSoon = Boolean(expiresAt && (expiresAt - Math.floor(Date.now() / 1000)) <= 30)

      // If a forced refresh was requested, only reuse cached token after at least one retry.
      if (!forceRefresh || attempt > 0) {
        if (!expiresSoon) {
          primedAccessToken = accessToken
          return accessToken
        }
      }
    }

    const shouldTryRefresh = forceRefresh || attempt < retries
    if (shouldTryRefresh) {
      const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession()
      if (!refreshError && refreshData.session?.access_token) {
        sessionHydrated = true
        primedAccessToken = refreshData.session.access_token
        return refreshData.session.access_token
      }
    }

    if (attempt < retries) {
      await sleep(150 * (attempt + 1))
    }
  }

  return null
}

/**
 * Get current user with tenant information
 */
export async function getCurrentUser() {
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) return null
  
  // Fetch user details with tenant info
  const { data: userData } = await supabase
    .from('users')
    .select(`
      *,
      tenants (
        id,
        company_name,
        subscription_tier,
        is_active,
        trial_end_date,
        max_users
      )
    `)
    .eq('id', user.id)
    .single()
  
  return userData
}

/**
 * Sign out user
 */
export async function signOut() {
  try {
    await supabase.auth.signOut({ scope: 'local' })
  } finally {
    sessionHydrated = false
    primedAccessToken = null
    window.location.href = '/login'
  }
}
