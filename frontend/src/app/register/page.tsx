'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { createClient, getSessionToken, primeSessionToken } from '@/lib/supabase/client';
import { env } from '@/lib/env';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { PageAlert } from '@/components/dashboard/PageAlert';
import { Sparkles, ArrowRight, Lock, Mail, Store, User } from 'lucide-react';

export default function RegisterPage() {
  const [companyName, setCompanyName] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();
  const supabase = createClient();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // 1. Hit registration endpoint at backend
      const response = await fetch(`${env.NEXT_PUBLIC_API_URL}/api/v1/tenants/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          company_name: companyName,
          email: email,
          password: password,
          full_name: fullName,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Registrasi gagal. Silakan coba lagi.');
      }

      // 2. Automate login on success
      const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (authError) throw authError;

      if (authData.user) {
        primeSessionToken(authData.session?.access_token ?? null);
        await getSessionToken({ retries: 3, ensureHydrated: true });
        await new Promise((resolve) => setTimeout(resolve, 800));
        router.push('/dashboard');
        router.refresh();
      }
    } catch (err: any) {
      setError(err.message || 'Gagal mendaftarkan toko baru.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4 relative overflow-hidden">
      {/* Decorative background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Radial glow top-right */}
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-accent/5 rounded-full blur-[150px]" />
        {/* Radial glow bottom-left */}
        <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-accent-secondary/5 rounded-full blur-[150px]" />
        
        {/* Floating decorative elements */}
        <div className="absolute top-20 left-20 w-32 h-32 border-2 border-accent/10 rounded-full animate-float" />
        <div className="absolute bottom-32 right-32 w-24 h-24 bg-gradient-to-br from-accent/10 to-accent-secondary/10 rounded-2xl animate-float-delayed" />
      </div>

      {/* Main content */}
      <div className="relative z-10 w-full max-w-md">
        {/* Logo/Brand section */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br from-accent to-accent-secondary rounded-2xl shadow-accent mb-3">
            <Sparkles className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-3xl font-display mb-1 text-brand-teal">
            Noble<span className="text-brand-orange">Soft</span>
          </h1>
          <p className="text-sm text-muted-foreground">
            Daftarkan toko Anda untuk mulai mengelola stok & kasir berbasis AI
          </p>
        </div>

        {/* Register card */}
        <Card className="overflow-hidden glass-card border-none shadow-lg">
          <CardHeader className="space-y-1 pb-3">
            <CardTitle className="text-xl font-display text-center text-brand-teal">
              Registrasi Toko Baru
            </CardTitle>
            <p className="text-center text-xs text-muted-foreground">
              Lengkapi formulir di bawah ini untuk memulai
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleRegister} className="space-y-4">
              {/* Company/Store Name input */}
              <div className="space-y-1.5">
                <label htmlFor="companyName" className="text-xs font-medium flex items-center gap-2 text-brand-teal">
                  <Store className="w-3.5 h-3.5 text-accent" />
                  Nama Toko / UMKM
                </label>
                <Input
                  id="companyName"
                  type="text"
                  placeholder="Contoh: Toko Kopi Sejahtera"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  required
                  disabled={loading}
                  className="h-10 glass-input text-sm"
                />
              </div>

              {/* Owner Name input */}
              <div className="space-y-1.5">
                <label htmlFor="fullName" className="text-xs font-medium flex items-center gap-2 text-brand-teal">
                  <User className="w-3.5 h-3.5 text-accent" />
                  Nama Pemilik
                </label>
                <Input
                  id="fullName"
                  type="text"
                  placeholder="Contoh: Ahmad Subardjo"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  disabled={loading}
                  className="h-10 glass-input text-sm"
                />
              </div>

              {/* Email input */}
              <div className="space-y-1.5">
                <label htmlFor="email" className="text-xs font-medium flex items-center gap-2 text-brand-teal">
                  <Mail className="w-3.5 h-3.5 text-accent" />
                  Email Toko
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="anda@toko.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={loading}
                  className="h-10 glass-input text-sm"
                />
              </div>

              {/* Password input */}
              <div className="space-y-1.5">
                <label htmlFor="password" className="text-xs font-medium flex items-center gap-2 text-brand-teal">
                  <Lock className="w-3.5 h-3.5 text-accent" />
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Minimal 6 karakter"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  disabled={loading}
                  className="h-10 glass-input text-sm"
                />
              </div>

              {/* Error message */}
              {error && (
                <PageAlert message={error} variant="error" />
              )}

              {/* Submit button */}
              <Button
                type="submit"
                className="w-full group mt-2"
                size="default"
                disabled={loading}
              >
                {loading ? (
                  'Mendaftarkan Toko...'
                ) : (
                  <>
                    Daftar Sekarang
                    <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
                  </>
                )}
              </Button>

              <div className="mt-4 text-center">
                <p className="text-xs text-muted-foreground">
                  Sudah memiliki akun toko?{' '}
                  <Link href="/login" className="text-brand-blue font-medium hover:underline">
                    Masuk di sini
                  </Link>
                </p>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Footer text */}
        <p className="text-center text-xs text-muted-foreground mt-4">
          100% GRATIS • Didukung Groq AI & Supabase
        </p>
      </div>
    </div>
  );
}
