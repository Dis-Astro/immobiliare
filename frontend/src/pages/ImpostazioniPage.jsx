import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import api from '../stores';
import { useAuthStore } from '../stores';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import {
  Tabs, TabsContent, TabsList, TabsTrigger
} from '../components/ui/tabs';
import {
  Sparkles, Server, CheckCircle2, XCircle, Loader2, Cpu, Cloud
} from 'lucide-react';

const OLLAMA_MODELS = [
  'llama3.2:3b', 'llama3.2:1b', 'llama3.1:8b', 'mistral:7b',
  'qwen2.5:3b', 'qwen2.5:7b', 'gemma2:2b', 'phi3.5:3.8b'
];

export default function ImpostazioniPage() {
  const { user } = useAuthStore();
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [externalModels, setExternalModels] = useState([]);

  const isSupervisore = user?.ruolo === 'supervisore';

  const fetchConfig = async () => {
    try {
      const res = await api.get('/ai/config');
      setConfig(res.data);
      setExternalModels(res.data.available_external_models || []);
    } catch (err) {
      toast.error('Errore caricamento config');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchConfig(); }, []);

  const handleSave = async () => {
    if (!isSupervisore) {
      toast.error('Solo supervisori possono modificare');
      return;
    }
    setSaving(true);
    try {
      const res = await api.put('/ai/config', {
        provider: config.provider,
        ollama_url: config.ollama_url,
        ollama_model: config.ollama_model,
        external_model: config.external_model,
        max_context_messages: config.max_context_messages,
        temperature: config.temperature,
        enabled: config.enabled
      });
      setConfig({ ...res.data, available_external_models: externalModels });
      toast.success('Configurazione salvata');
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.post('/ai/test-connection');
      setTestResult(res.data);
      if (res.data.success) {
        toast.success(`Connessione OK (${res.data.latency_ms}ms)`);
      } else {
        toast.error('Test fallito: ' + res.data.error);
      }
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
      setTestResult({ success: false, error: err.message });
    } finally {
      setTesting(false);
    }
  };

  if (loading) return <div className="p-8 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>;
  if (!config) return <div className="p-8 text-center text-red-500">Errore caricamento configurazione</div>;

  return (
    <div className="space-y-6 max-w-4xl" data-testid="impostazioni-page">
      <div>
        <h1 className="text-3xl font-bold font-heading">Impostazioni</h1>
        <p className="text-slate-500">Configurazione AI e parametri di sistema</p>
      </div>

      <Tabs defaultValue="ai">
        <TabsList>
          <TabsTrigger value="ai" data-testid="tab-ai"><Sparkles className="w-4 h-4 mr-2" /> AI</TabsTrigger>
          <TabsTrigger value="general" data-testid="tab-general">Generale</TabsTrigger>
        </TabsList>

        <TabsContent value="ai" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-purple-500" />
                Configurazione AI
              </CardTitle>
              <CardDescription>
                Scegli il provider AI tra Ollama (locale) o servizi esterni (OpenAI, Anthropic, Google).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <Label htmlFor="enabled" className="text-base">AI abilitata</Label>
                <input
                  id="enabled"
                  type="checkbox"
                  checked={config.enabled}
                  onChange={e => setConfig({...config, enabled: e.target.checked})}
                  disabled={!isSupervisore}
                  className="w-5 h-5"
                  data-testid="toggle-enabled"
                />
                <Badge variant={config.enabled ? 'default' : 'destructive'}>
                  {config.enabled ? 'Attiva' : 'Disattivata'}
                </Badge>
              </div>

              <div>
                <Label>Provider</Label>
                <Select value={config.provider} onValueChange={v => setConfig({...config, provider: v})} disabled={!isSupervisore}>
                  <SelectTrigger data-testid="select-provider"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ollama">
                      <div className="flex items-center gap-2"><Cpu className="w-4 h-4" /> Ollama (locale)</div>
                    </SelectItem>
                    <SelectItem value="openai">
                      <div className="flex items-center gap-2"><Cloud className="w-4 h-4" /> OpenAI (Emergent LLM)</div>
                    </SelectItem>
                    <SelectItem value="anthropic">
                      <div className="flex items-center gap-2"><Cloud className="w-4 h-4" /> Anthropic Claude (Emergent LLM)</div>
                    </SelectItem>
                    <SelectItem value="gemini">
                      <div className="flex items-center gap-2"><Cloud className="w-4 h-4" /> Google Gemini (Emergent LLM)</div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {config.provider === 'ollama' ? (
                <Card className="bg-slate-50 dark:bg-slate-900">
                  <CardContent className="pt-4 space-y-3">
                    <div>
                      <Label>URL Ollama</Label>
                      <Input
                        value={config.ollama_url}
                        onChange={e => setConfig({...config, ollama_url: e.target.value})}
                        placeholder="http://ollama:11434"
                        disabled={!isSupervisore}
                        data-testid="input-ollama-url"
                      />
                      <p className="text-xs text-slate-500 mt-1">In produzione, Ollama gira nel container Proxmox come servizio Docker.</p>
                    </div>
                    <div>
                      <Label>Modello Ollama</Label>
                      <Select value={config.ollama_model} onValueChange={v => setConfig({...config, ollama_model: v})} disabled={!isSupervisore}>
                        <SelectTrigger data-testid="select-ollama-model"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {OLLAMA_MODELS.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-slate-500 mt-1">Il modello deve essere già scaricato sul server Ollama (<code>ollama pull {config.ollama_model}</code>).</p>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card className="bg-slate-50 dark:bg-slate-900">
                  <CardContent className="pt-4 space-y-3">
                    <div>
                      <Label>Modello {config.provider}</Label>
                      <Select value={config.external_model} onValueChange={v => setConfig({...config, external_model: v})} disabled={!isSupervisore}>
                        <SelectTrigger data-testid="select-external-model"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {externalModels
                            .filter(m => {
                              if (config.provider === 'openai') return m.startsWith('gpt');
                              if (config.provider === 'anthropic') return m.startsWith('claude');
                              if (config.provider === 'gemini') return m.startsWith('gemini');
                              return true;
                            })
                            .map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-slate-500 mt-1">Utilizza la chiave universale Emergent LLM. Verifica il credito disponibile nel pannello Emergent.</p>
                    </div>
                  </CardContent>
                </Card>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Temperature ({config.temperature})</Label>
                  <Input
                    type="range" min="0" max="2" step="0.1"
                    value={config.temperature}
                    onChange={e => setConfig({...config, temperature: parseFloat(e.target.value)})}
                    disabled={!isSupervisore}
                    data-testid="input-temperature"
                  />
                  <p className="text-xs text-slate-500">0 = deterministico, 2 = creativo</p>
                </div>
                <div>
                  <Label>Max messaggi cronologia</Label>
                  <Input
                    type="number" min="1" max="100"
                    value={config.max_context_messages}
                    onChange={e => setConfig({...config, max_context_messages: parseInt(e.target.value)})}
                    disabled={!isSupervisore}
                    data-testid="input-max-context"
                  />
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <Button onClick={handleSave} disabled={saving || !isSupervisore} data-testid="btn-save-ai-config">
                  {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Salva
                </Button>
                <Button variant="outline" onClick={handleTest} disabled={testing || !config.enabled} data-testid="btn-test-ai">
                  {testing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Server className="w-4 h-4 mr-2" />}
                  Testa connessione
                </Button>
              </div>

              {testResult && (
                <div className={`p-3 rounded-lg ${testResult.success ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800' : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'}`} data-testid="test-result">
                  <div className="flex items-center gap-2">
                    {testResult.success ? <CheckCircle2 className="w-5 h-5 text-emerald-600" /> : <XCircle className="w-5 h-5 text-red-600" />}
                    <span className="font-medium">{testResult.success ? 'Connessione riuscita' : 'Connessione fallita'}</span>
                  </div>
                  {testResult.success ? (
                    <div className="mt-2 text-sm space-y-1">
                      <div>Provider: <code>{testResult.provider}</code></div>
                      <div>Modello: <code>{testResult.model}</code></div>
                      <div>Latenza: {testResult.latency_ms}ms</div>
                      <div>Risposta: <em>"{testResult.response_preview}"</em></div>
                    </div>
                  ) : (
                    <div className="mt-2 text-sm text-red-700 dark:text-red-300">{testResult.error}</div>
                  )}
                </div>
              )}

              {!isSupervisore && (
                <p className="text-sm text-amber-600 italic">Solo i supervisori possono modificare la configurazione AI.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="general">
          <Card>
            <CardHeader>
              <CardTitle>Impostazioni generali</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-slate-500">Altre impostazioni saranno disponibili a breve.</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
