'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { PageAlert } from '@/components/dashboard/PageAlert';
import { ArrowLeft, Save, Sparkles, Sliders, Key, Globe, Cpu } from 'lucide-react';

interface AISettings {
  tenant_id: string;
  api_key: string | null;
  base_url: string | null;
  model_name: string;
  temperature: number;
}

export default function AISettingsPage() {
  const [settings, setSettings] = useState<AISettings | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [modelName, setModelName] = useState('llama-3.1-8b-instant');
  const [temperature, setTemperature] = useState(0.2);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const router = useRouter();

  // Load current settings
  useEffect(() => {
    async function loadSettings() {
      try {
        const data = await apiClient.get<AISettings>('/tenants/current/ai-settings');
        setSettings(data);
        setApiKey(data.api_key || '');
        setBaseUrl(data.base_url || '');
        setModelName(data.model_name || 'llama-3.1-8b-instant');
        setTemperature(data.temperature ?? 0.2);
      } catch (err: any) {
        setError(err.message || 'Gagal memuat pengaturan AI.');
      } finally {
        setLoading(false);
      }
    }
    loadSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const payload = {
        api_key: apiKey.trim() || null,
        base_url: baseUrl.trim() || null,
        model_name: modelName.trim(),
        temperature: parseFloat(temperature.toFixed(2)),
      };

      const updated = await apiClient.patch<AISettings>('/tenants/current/ai-settings', payload);
      setSettings(updated);
      setSuccess('Pengaturan AI berhasil diperbarui!');
      
      // Mask key again after visual update
      setApiKey(updated.api_key || '');
    } catch (err: any) {
      setError(err.message || 'Gagal menyimpan pengaturan AI.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="text-center space-y-2">
          <div className="w-10 h-10 border-4 border-brand-blue border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-muted-foreground">Memuat Pengaturan AI...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/settings">
          <Button variant="ghost" size="icon" className="rounded-lg">
            <ArrowLeft className="w-5 h-5 text-brand-teal" />
          </Button>
        </Link>
        <PageHeader
          label="Workspace"
          title="AI & API Settings"
          description="Konfigurasi integrasi AI mandiri (BYOK) untuk asisten pintar kasir Anda."
        />
      </div>

      <div className="max-w-2xl">
        <Card className="glass-card border-none shadow-md">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2 text-brand-teal">
              <Sparkles className="w-5 h-5 text-brand-blue" />
              Kustomisasi LLM / BYOK (Bring Your Own Key)
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Gunakan kunci API Anda sendiri untuk akses penuh tanpa batas. Data transaksi Anda diproses langsung ke API endpoint yang dikonfigurasi.
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSave} className="space-y-5">
              {/* API Key */}
              <div className="space-y-2">
                <label htmlFor="apiKey" className="text-sm font-medium flex items-center gap-2 text-brand-teal">
                  <Key className="w-4 h-4 text-accent" />
                  Groq API Key (atau Provider kustom)
                </label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder={settings?.api_key ? '••••••••••••••••••••••••' : 'gsk_...'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  disabled={saving}
                  className="h-10 glass-input text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  Masukkan kunci API Groq Anda. Kunci ini disimpan secara aman dan terenkripsi di database Anda sendiri.
                </p>
              </div>

              {/* Custom Endpoint */}
              <div className="space-y-2">
                <label htmlFor="baseUrl" className="text-sm font-medium flex items-center gap-2 text-brand-teal">
                  <Globe className="w-4 h-4 text-accent" />
                  Custom Base URL (Opsional)
                </label>
                <Input
                  id="baseUrl"
                  type="url"
                  placeholder="https://api.groq.com/openai/v1"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  disabled={saving}
                  className="h-10 glass-input text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  Kosongkan untuk menggunakan default Groq API. Anda dapat menggantinya ke provider yang kompatibel dengan OpenAI API.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Model Name */}
                <div className="space-y-2">
                  <label htmlFor="modelName" className="text-sm font-medium flex items-center gap-2 text-brand-teal">
                    <Cpu className="w-4 h-4 text-accent" />
                    Model Name
                  </label>
                  <Input
                    id="modelName"
                    type="text"
                    placeholder="llama-3.1-8b-instant"
                    value={modelName}
                    onChange={(e) => setModelName(e.target.value)}
                    required
                    disabled={saving}
                    className="h-10 glass-input text-sm"
                  />
                  <p className="text-xs text-muted-foreground">
                    Contoh: llama-3.1-8b-instant, mixtral-8x7b-32768, dll.
                  </p>
                </div>

                {/* Temperature */}
                <div className="space-y-2">
                  <label htmlFor="temperature" className="text-sm font-medium flex items-center gap-2 text-brand-teal">
                    <Sliders className="w-4 h-4 text-accent" />
                    Temperature: {temperature}
                  </label>
                  <div className="flex items-center gap-4 py-2">
                    <input
                      id="temperature"
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={temperature}
                      onChange={(e) => setTemperature(parseFloat(e.target.value))}
                      disabled={saving}
                      className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-blue"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Nilai lebih rendah membuat respons lebih fokus dan akurat.
                  </p>
                </div>
              </div>

              {/* Alert Notifications */}
              {error && <PageAlert message={error} variant="error" />}
              {success && <PageAlert message={success} variant="success" />}

              {/* Submit / Action buttons */}
              <div className="flex justify-end gap-3 pt-3 border-t border-border/50">
                <Link href="/settings">
                  <Button type="button" variant="ghost" disabled={saving}>
                    Batal
                  </Button>
                </Link>
                <Button
                  type="submit"
                  disabled={saving}
                  className="bg-brand-orange text-white hover:bg-brand-orange/90 flex items-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  {saving ? 'Menyimpan...' : 'Simpan Perubahan'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
