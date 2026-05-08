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
  Dialog, DialogContent, DialogHeader, DialogTitle
} from '../components/ui/dialog';
import {
  Sparkles, Server, CheckCircle2, XCircle, Loader2, Cpu, Cloud, Mail,
  Plus, Trash2, Send, Eye, AlertCircle
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
          <TabsTrigger value="brief" data-testid="tab-brief"><Mail className="w-4 h-4 mr-2" /> Brief AI</TabsTrigger>
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

        <TabsContent value="brief" className="space-y-4">
          <BriefSettings isSupervisore={isSupervisore} />
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


function BriefSettings({ isSupervisore }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [previewHtml, setPreviewHtml] = useState(null);
  const [previewStats, setPreviewStats] = useState(null);
  const [newRecipient, setNewRecipient] = useState('');

  const fetchConfig = async () => {
    try {
      const res = await api.get('/brief/config');
      setConfig(res.data);
    } catch (err) {
      toast.error('Errore caricamento config brief');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchConfig(); }, []);

  const handleSave = async () => {
    if (!isSupervisore) return;
    setSaving(true);
    try {
      const res = await api.put('/brief/config', {
        enabled: config.enabled,
        cron_hour: config.cron_hour,
        cron_minute: config.cron_minute,
        recipients: config.recipients,
        include_rate: config.include_rate,
        include_ape: config.include_ape,
        include_contratti: config.include_contratti,
        include_interventi: config.include_interventi,
      });
      setConfig(res.data);
      toast.success('Configurazione brief salvata');
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const addRecipient = () => {
    const email = newRecipient.trim();
    if (!email) return;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast.error('Email non valida');
      return;
    }
    if (config.recipients.includes(email)) {
      toast.error('Email già presente');
      return;
    }
    setConfig({ ...config, recipients: [...config.recipients, email] });
    setNewRecipient('');
  };

  const removeRecipient = (email) => {
    setConfig({ ...config, recipients: config.recipients.filter(r => r !== email) });
  };

  const handlePreview = async () => {
    setPreviewing(true);
    try {
      const res = await api.post('/brief/preview');
      setPreviewHtml(res.data.summary_html);
      setPreviewStats(res.data.stats);
    } catch (err) {
      toast.error('Errore anteprima: ' + (err.response?.data?.detail || err.message));
    } finally {
      setPreviewing(false);
    }
  };

  const handleSendNow = async () => {
    if (!isSupervisore) return;
    setSending(true);
    try {
      const res = await api.post('/brief/send-now');
      if (res.data.status === 'success') {
        toast.success(`Brief inviato a ${res.data.sent_count}/${res.data.total_recipients} destinatari`);
      } else if (res.data.status === 'partial') {
        toast.warning(`Inviato parzialmente: ${res.data.sent_count}/${res.data.total_recipients}`);
      } else {
        toast.error('Invio fallito: ' + (res.data.errors?.[0] || 'errore sconosciuto'));
      }
      fetchConfig();
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSending(false);
    }
  };

  if (loading) return <div className="p-8 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>;
  if (!config) return <p className="text-red-500">Errore caricamento</p>;

  return (
    <Card data-testid="brief-settings">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="w-5 h-5 text-blue-500" />
          Brief mattutino AI via email
        </CardTitle>
        <CardDescription>
          Sintesi quotidiana automatica via email con sintesi AI di rate, APE, contratti e interventi.
          Richiede SMTP configurato (variabili <code>SMTP_*</code> nel <code>.env</code> backend).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <Label htmlFor="brief-enabled" className="text-base">Brief abilitato</Label>
          <input
            id="brief-enabled"
            type="checkbox"
            checked={config.enabled}
            onChange={e => setConfig({ ...config, enabled: e.target.checked })}
            disabled={!isSupervisore}
            className="w-5 h-5"
            data-testid="toggle-brief-enabled"
          />
          <Badge variant={config.enabled ? 'default' : 'secondary'}>
            {config.enabled ? 'Attivo' : 'Disattivato'}
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Ora invio</Label>
            <Input
              type="number" min="0" max="23"
              value={config.cron_hour}
              onChange={e => setConfig({ ...config, cron_hour: parseInt(e.target.value) || 0 })}
              disabled={!isSupervisore}
              data-testid="input-cron-hour"
            />
          </div>
          <div>
            <Label>Minuti</Label>
            <Input
              type="number" min="0" max="59"
              value={config.cron_minute}
              onChange={e => setConfig({ ...config, cron_minute: parseInt(e.target.value) || 0 })}
              disabled={!isSupervisore}
              data-testid="input-cron-minute"
            />
          </div>
        </div>
        <p className="text-xs text-slate-500 -mt-2">
          Fuso orario: Europe/Rome. Es. 8:00 = 08:00 italiana.
        </p>

        <div>
          <Label>Destinatari email</Label>
          <div className="flex gap-2 mt-1">
            <Input
              type="email"
              placeholder="nome@azienda.it"
              value={newRecipient}
              onChange={e => setNewRecipient(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addRecipient())}
              disabled={!isSupervisore}
              data-testid="input-new-recipient"
            />
            <Button onClick={addRecipient} disabled={!isSupervisore || !newRecipient.trim()} variant="outline" data-testid="btn-add-recipient">
              <Plus className="w-4 h-4" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            {config.recipients.length === 0 && (
              <p className="text-sm text-slate-400">Nessun destinatario configurato</p>
            )}
            {config.recipients.map(email => (
              <Badge key={email} variant="secondary" className="pl-2 pr-1 py-1 gap-1">
                {email}
                {isSupervisore && (
                  <button
                    onClick={() => removeRecipient(email)}
                    className="hover:text-red-500 ml-1"
                    data-testid={`btn-remove-${email}`}
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </Badge>
            ))}
          </div>
        </div>

        <div>
          <Label>Sezioni da includere</Label>
          <div className="grid grid-cols-2 gap-2 mt-2">
            {[
              { key: 'include_rate', label: 'Rate in ritardo' },
              { key: 'include_ape', label: 'APE in scadenza (90gg)' },
              { key: 'include_contratti', label: 'Contratti in scadenza (30gg)' },
              { key: 'include_interventi', label: 'Interventi aperti' },
            ].map(s => (
              <label key={s.key} className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={config[s.key]}
                  onChange={e => setConfig({ ...config, [s.key]: e.target.checked })}
                  disabled={!isSupervisore}
                  data-testid={`toggle-${s.key}`}
                />
                {s.label}
              </label>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 pt-2 border-t">
          <Button onClick={handleSave} disabled={saving || !isSupervisore} data-testid="btn-save-brief">
            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
            Salva
          </Button>
          <Button variant="outline" onClick={handlePreview} disabled={previewing} data-testid="btn-preview-brief">
            {previewing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Eye className="w-4 h-4 mr-2" />}
            Anteprima
          </Button>
          <Button
            variant="outline"
            onClick={handleSendNow}
            disabled={sending || !isSupervisore || config.recipients.length === 0}
            data-testid="btn-send-now"
          >
            {sending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
            Invia ora
          </Button>
        </div>

        {config.last_sent_at && (
          <div className="text-xs text-slate-500 pt-2 border-t flex items-start gap-2" data-testid="brief-last-status">
            {config.last_status === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5" />
            ) : config.last_status === 'error' ? (
              <XCircle className="w-4 h-4 text-red-600 mt-0.5" />
            ) : (
              <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5" />
            )}
            <div>
              Ultimo invio: {new Date(config.last_sent_at).toLocaleString('it-IT')} — <strong className="capitalize">{config.last_status}</strong>
              {config.last_error && <div className="text-red-500 mt-1">{config.last_error}</div>}
            </div>
          </div>
        )}

        {!isSupervisore && (
          <p className="text-sm text-amber-600 italic">Solo i supervisori possono modificare la configurazione del brief.</p>
        )}
      </CardContent>

      <Dialog open={!!previewHtml} onOpenChange={(o) => !o && setPreviewHtml(null)}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Anteprima Brief Mattutino</DialogTitle>
          </DialogHeader>
          {previewStats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
              <Badge variant="secondary" className="justify-center">Rate: {previewStats.rate_in_ritardo}</Badge>
              <Badge variant="secondary" className="justify-center">APE: {previewStats.ape_in_scadenza}</Badge>
              <Badge variant="secondary" className="justify-center">Contratti: {previewStats.contratti_in_scadenza}</Badge>
              <Badge variant="secondary" className="justify-center">Interventi: {previewStats.interventi_aperti}</Badge>
            </div>
          )}
          <div
            className="border rounded p-3 bg-white"
            data-testid="brief-preview-content"
            dangerouslySetInnerHTML={{ __html: previewHtml || '' }}
          />
        </DialogContent>
      </Dialog>
    </Card>
  );
}
