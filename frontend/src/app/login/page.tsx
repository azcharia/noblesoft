'use client';

import { useState } from 'react';
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
  const showTestCredentials = process.env.NODE_ENV !== 'production';

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
        router.push('/chat');
        router.refresh();
      }
    } catch (err: any) {
      setError(err.message || 'Login failed');
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
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-accent to-accent-secondary rounded-2xl shadow-accent mb-4">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-display mb-2">
            Noble<span className="gradient-text">Soft</span>
          </h1>
          <p className="text-muted-foreground">
            AI-Powered Business Management
          </p>
        </div>

        {/* Login card */}
        <Card className="overflow-hidden">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-2xl font-display text-center">
              Welcome Back
            </CardTitle>
            <p className="text-center text-sm text-muted-foreground">
              Sign in to access your dashboard
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              {/* Email input */}
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium flex items-center gap-2">
                  <Mail className="w-4 h-4 text-accent" />
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={loading}
                  className="h-12"
                />
              </div>

              {/* Password input */}
              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium flex items-center gap-2">
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
                  className="h-12"
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
                  'Signing in...'
                ) : (
                  <>
                    Sign In
                    <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
                  </>
                )}
              </Button>

              {/* Test credentials info */}
              {showTestCredentials && (
                <div className="mt-6 p-4 bg-accent/5 border border-accent/20 rounded-lg">
                  <div className="flex items-start gap-3">
                    <div className="w-2 h-2 rounded-full bg-accent mt-1.5 animate-pulse-slow" />
                    <div>
                      <p className="text-sm font-medium text-foreground mb-1">
                        Test Credentials
                      </p>
                      <p className="text-xs text-muted-foreground font-mono">
                        admin@noblesoft.com<br />
                        admin123
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </form>
          </CardContent>
        </Card>

        {/* Footer text */}
        <p className="text-center text-xs text-muted-foreground mt-6">
          100% FREE • Powered by Groq AI • Local Embeddings
        </p>
      </div>
    </div>
  );
}
