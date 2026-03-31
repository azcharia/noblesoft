/**
 * Supabase Database Types
 * Generated from Supabase schema
 */

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      tenants: {
        Row: {
          id: string
          company_name: string
          subscription_tier: 'trial' | 'basic' | 'pro' | 'enterprise'
          trial_start_date: string | null
          trial_end_date: string | null
          is_active: boolean
          max_users: number
          payment_gateway_customer_id: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          company_name: string
          subscription_tier?: 'trial' | 'basic' | 'pro' | 'enterprise'
          trial_start_date?: string | null
          trial_end_date?: string | null
          is_active?: boolean
          max_users?: number
          payment_gateway_customer_id?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          company_name?: string
          subscription_tier?: 'trial' | 'basic' | 'pro' | 'enterprise'
          trial_start_date?: string | null
          trial_end_date?: string | null
          is_active?: boolean
          max_users?: number
          payment_gateway_customer_id?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      users: {
        Row: {
          id: string
          tenant_id: string
          email: string
          full_name: string | null
          role: 'owner' | 'admin' | 'member'
          is_active: boolean
          created_at: string
          updated_at: string
        }
        Insert: {
          id: string
          tenant_id: string
          email: string
          full_name?: string | null
          role?: 'owner' | 'admin' | 'member'
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          tenant_id?: string
          email?: string
          full_name?: string | null
          role?: 'owner' | 'admin' | 'member'
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
  }
}
