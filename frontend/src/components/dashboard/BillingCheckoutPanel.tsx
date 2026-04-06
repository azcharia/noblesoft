'use client'

import { useEffect, useMemo, useState } from 'react'

import { apiClient, type BillingAddOnCode, type BillingCatalogResponse, type BillingPeriod, type BillingTier } from '@/lib/api/client'
import { cn, formatCurrency } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageAlert } from '@/components/dashboard/PageAlert'

const TIER_ORDER: Record<BillingTier, number> = {
  basic: 1,
  pro: 2,
  enterprise: 3,
}

interface BillingCheckoutPanelProps {
  currentTier: string
  currentCompanyName: string
}

function toNumber(value: number | string): number {
  if (typeof value === 'number') return value
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function normalizeTier(tier: string): BillingTier {
  if (tier === 'basic' || tier === 'pro' || tier === 'enterprise') {
    return tier
  }
  return 'basic'
}

export function BillingCheckoutPanel({ currentTier, currentCompanyName }: BillingCheckoutPanelProps) {
  const normalizedCurrentTier = normalizeTier(currentTier)
  const [catalog, setCatalog] = useState<BillingCatalogResponse | null>(null)
  const [selectedTier, setSelectedTier] = useState<BillingTier>(normalizedCurrentTier)
  const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>('monthly')
  const [selectedAddOns, setSelectedAddOns] = useState<Record<BillingAddOnCode, boolean>>({
    ai_agent_pack: false,
    automation_pack: false,
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true

    apiClient.billing
      .getCatalog()
      .then((response) => {
        if (!mounted) return
        setCatalog(response)
      })
      .catch((err) => {
        if (!mounted) return
        const message = err instanceof Error ? err.message : 'Gagal memuat katalog billing.'
        setError(message)
      })

    return () => {
      mounted = false
    }
  }, [])

  const selectedPlan = useMemo(
    () => (catalog ? catalog.plans.find((plan) => plan.tier === selectedTier) : undefined),
    [catalog, selectedTier]
  )

  const selectedAddOnCodes = useMemo(
    () => Object.entries(selectedAddOns).filter(([, enabled]) => enabled).map(([code]) => code as BillingAddOnCode),
    [selectedAddOns]
  )

  const totalPrice = useMemo(() => {
    const planPrice = selectedPlan
      ? billingPeriod === 'annual'
        ? toNumber(selectedPlan.annual_price)
        : toNumber(selectedPlan.monthly_price)
      : 0

    const addOnPrice = (catalog?.add_ons || [])
      .filter((item) => selectedAddOnCodes.includes(item.code))
      .reduce((sum, item) => {
        const price = billingPeriod === 'annual' ? toNumber(item.annual_price) : toNumber(item.monthly_price)
        return sum + price
      }, 0)

    return planPrice + addOnPrice
  }, [billingPeriod, catalog, selectedAddOnCodes, selectedPlan])

  const checkoutLabel = billingPeriod === 'annual' ? 'Checkout Paket Tahunan' : 'Checkout Paket Bulanan'

  const handleCheckout = async () => {
    if (!catalog) return

    setError('')
    setSubmitting(true)

    try {
      const response = await apiClient.billing.createTransaction({
        target_tier: selectedTier,
        billing_period: billingPeriod,
        add_ons: selectedAddOnCodes.map((code) => ({ code, quantity: 1 })),
        customer_name: currentCompanyName,
      })

      window.location.href = response.redirect_url
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Gagal membuat transaksi Midtrans.'
      setError(message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-5">
      {!catalog ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Memuat katalog billing...</p>
            {error ? <PageAlert className="mt-4" variant="error" message={error} /> : null}
          </CardContent>
        </Card>
      ) : null}

      {catalog ? (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Plan Selection</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {catalog.plans.map((plan) => {
              const isCurrent = plan.tier === normalizedCurrentTier
              const canSelect = TIER_ORDER[plan.tier] >= TIER_ORDER[normalizedCurrentTier]
              const planPrice = billingPeriod === 'annual' ? toNumber(plan.annual_price) : toNumber(plan.monthly_price)

              return (
                <button
                  type="button"
                  key={plan.tier}
                  disabled={!canSelect}
                  onClick={() => setSelectedTier(plan.tier)}
                  className={cn(
                    'rounded-xl border p-4 text-left transition-all',
                    selectedTier === plan.tier
                      ? 'border-accent bg-accent/10 shadow-accent'
                      : 'border-border bg-muted/50 hover:border-accent/40',
                    !canSelect && 'cursor-not-allowed opacity-60'
                  )}
                >
                  <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">{plan.tier}</p>
                  <p className="mt-2 text-xl font-semibold text-foreground">{formatCurrency(planPrice)}</p>
                  <p className="mt-1 text-xs text-muted-foreground">maks {plan.max_users} user</p>
                  {isCurrent ? <p className="mt-2 text-xs font-medium text-accent">Paket aktif saat ini</p> : null}
                </button>
              )
            })}
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Button
              type="button"
              variant={billingPeriod === 'monthly' ? 'default' : 'outline'}
              onClick={() => setBillingPeriod('monthly')}
            >
              Bulanan
            </Button>
            <Button
              type="button"
              variant={billingPeriod === 'annual' ? 'default' : 'outline'}
              onClick={() => setBillingPeriod('annual')}
            >
              Tahunan ({catalog.annual_discount_percent}% lebih hemat)
            </Button>
          </div>
        </CardContent>
      </Card>
      ) : null}

      {catalog ? (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">AI Add-on</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {catalog.add_ons.map((addOn) => {
            const price = billingPeriod === 'annual' ? toNumber(addOn.annual_price) : toNumber(addOn.monthly_price)
            const checked = selectedAddOns[addOn.code]

            return (
              <label
                key={addOn.code}
                className="flex cursor-pointer items-start justify-between gap-3 rounded-xl border border-border bg-muted/40 p-3"
              >
                <div className="space-y-1">
                  <p className="font-medium text-foreground">{addOn.name}</p>
                  <p className="text-sm text-muted-foreground">{addOn.description}</p>
                  <p className="text-sm font-medium text-accent">{formatCurrency(price)}</p>
                </div>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(event) => {
                    setSelectedAddOns((prev) => ({ ...prev, [addOn.code]: event.target.checked }))
                  }}
                  className="mt-1 h-4 w-4 rounded border-border"
                />
              </label>
            )
          })}
        </CardContent>
      </Card>
      ) : null}

      {catalog ? (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Ringkasan Checkout</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-xl border border-border bg-muted/50 p-4">
            <p className="text-sm text-muted-foreground">Total tagihan</p>
            <p className="mt-1 text-2xl font-semibold text-foreground">{formatCurrency(totalPrice)}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Nominal dihitung dari katalog backend dan diverifikasi lagi sebelum transaksi dibuat.
            </p>
          </div>

          {error ? <PageAlert variant="error" message={error} /> : null}

          <Button type="button" onClick={handleCheckout} disabled={submitting} className="w-full">
            {submitting ? 'Membuat transaksi...' : checkoutLabel}
          </Button>
        </CardContent>
      </Card>
      ) : null}
    </div>
  )
}
