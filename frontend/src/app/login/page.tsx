'use client';

import { useState } from 'react';
import Link from 'next/link';
import { createClient, getSessionToken, primeSessionToken } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { PageAlert } from '@/components/dashboard/PageAlert';
import { Sparkles, ArrowRight, Lock, Mail } from 'lucide-react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();
  const supabase = createClient();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) throw error;

      if (data.user) {
        primeSessionToken(data.session?.access_token ?? null);
        await getSessionToken({ retries: 3, ensureHydrated: true });
        await new Promise((resolve) => setTimeout(resolve, 800));
        router.push('/dashboard');
        router.refresh();
      }
    } catch (err: any) {
      let errorMessage = 'Aduh, sistem sedang sibuk. Boleh coba sebentar lagi?';
      if (err.message?.toLowerCase().includes('invalid') || err.message?.toLowerCase().includes('credentials')) {
        errorMessage = 'Hmm, sepertinya Email atau Password-nya keliru. Coba dicek lagi ya!';
      }
      setError(errorMessage);
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
        <div className="text-center mb-8 flex flex-col items-center">
          <img src="/logo.jpg" alt="NobleSoft Logo" className="w-16 h-16 rounded-2xl shadow-md object-cover mb-4" />
          <h1 className="text-4xl font-display mb-2 text-brand-teal">
            Noble<span className="text-brand-orange">Soft</span>
          </h1>
          <p className="text-muted-foreground">
            Aplikasi Kasir Digital & Manajemen Stok Berbasis AI
          </p>
        </div>

        {/* Login card */}
        <Card className="overflow-hidden glass-card border-none shadow-lg">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-2xl font-display text-center text-brand-teal">
              Selamat Datang
            </CardTitle>
            <p className="text-center text-sm text-muted-foreground">
              Masuk untuk mengakses kasir digital Anda
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              {/* Email input */}
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium flex items-center gap-2 text-brand-teal">
                  <Mail className="w-4 h-4 text-accent" />
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
                  className="h-12 glass-input"
                />
              </div>

              {/* Password input */}
              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium flex items-center gap-2 text-brand-teal">
                  <Lock className="w-4 h-4 text-accent" />
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                  className="h-12 glass-input"
                />
              </div>

              {/* Error message */}
              {error && (
                <PageAlert message={error} variant="error" />
              )}

              {/* Submit button */}
              <Button
                type="submit"
                className="w-full group"
                size="lg"
                disabled={loading}
              >
                {loading ? (
                  'Masuk...'
                ) : (
                  <>
                    Masuk ke Kasir
                    <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
                  </>
                )}
              </Button>

              <div className="mt-6 text-center">
                <p className="text-sm text-muted-foreground">
                  Belum punya akun toko?{' '}
                  <Link href="/register" className="text-brand-blue font-medium hover:underline">
                    Daftar Toko Baru
                  </Link>
                </p>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Footer text */}
        <p className="text-center text-xs text-muted-foreground mt-6">
          100% GRATIS • Didukung Groq AI & Supabase
        </p>
      </div>
    </div>
  );
}
