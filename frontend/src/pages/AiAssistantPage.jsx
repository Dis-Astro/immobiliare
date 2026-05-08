import React, { useState, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import api from '../stores';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Send, Plus, Trash2, MessageSquare, Sparkles, FileText, Mail, ScrollText, X,
  Bot, User as UserIcon, Loader2, Wand2
} from 'lucide-react';

function MessageBubble({ message, isUser }) {
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`} data-testid={`msg-${message.role}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isUser ? 'bg-blue-600 text-white' : 'bg-purple-600 text-white'}`}>
        {isUser ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      <div className={`flex-1 max-w-[80%] ${isUser ? 'items-end' : ''}`}>
        <div className={`rounded-2xl px-4 py-2 ${isUser ? 'bg-blue-600 text-white ml-auto' : 'bg-slate-100 dark:bg-slate-800'}`}>
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        </div>
        {message.metadata?.model && (
          <div className="text-xs text-slate-400 mt-1 px-2">
            {message.metadata.model} · {message.metadata.latency_ms}ms
          </div>
        )}
      </div>
    </div>
  );
}

export default function AiAssistantPage() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [includeContext, setIncludeContext] = useState(true);
  const [aiConfig, setAiConfig] = useState(null);

  const [generateOpen, setGenerateOpen] = useState(false);
  const [genForm, setGenForm] = useState({ tipo: 'email_sollecito', istruzioni: '' });
  const [genLoading, setGenLoading] = useState(false);
  const [genResult, setGenResult] = useState('');

  const messagesEndRef = useRef(null);

  const fetchSessions = async () => {
    try {
      const res = await api.get('/ai/sessions');
      setSessions(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchConfig = async () => {
    try {
      const res = await api.get('/ai/config');
      setAiConfig(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const loadSession = async (sid) => {
    setCurrentSessionId(sid);
    try {
      const res = await api.get(`/ai/sessions/${sid}/messages`);
      setMessages(res.data.messages || []);
    } catch (err) {
      toast.error('Errore caricamento sessione');
    }
  };

  const newSession = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setInput('');
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMessage = input.trim();
    setInput('');

    const tempUser = { role: 'user', content: userMessage, created_at: new Date().toISOString(), metadata: {} };
    setMessages(prev => [...prev, tempUser]);
    setLoading(true);

    try {
      const res = await api.post('/ai/chat', {
        session_id: currentSessionId,
        message: userMessage,
        include_context: includeContext
      });
      if (!currentSessionId) {
        setCurrentSessionId(res.data.session_id);
        fetchSessions();
      }
      setMessages(prev => [...prev.slice(0, -1), res.data.user_message, res.data.assistant_message]);
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const deleteSession = async (sid, e) => {
    e.stopPropagation();
    if (!confirm('Eliminare questa conversazione?')) return;
    try {
      await api.delete(`/ai/sessions/${sid}`);
      if (sid === currentSessionId) {
        newSession();
      }
      fetchSessions();
    } catch (err) {
      toast.error('Errore eliminazione');
    }
  };

  const handleGenerate = async () => {
    setGenLoading(true);
    setGenResult('');
    try {
      const res = await api.post('/ai/generate', {
        tipo: genForm.tipo,
        contesto: {},
        istruzioni: genForm.istruzioni || null
      });
      setGenResult(res.data.content);
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setGenLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
    fetchConfig();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="h-[calc(100vh-8rem)] flex gap-4" data-testid="ai-page">
      {/* Sidebar sessioni */}
      <div className="w-64 flex flex-col gap-3">
        <Button onClick={newSession} className="w-full" data-testid="btn-new-chat">
          <Plus className="w-4 h-4 mr-2" /> Nuova chat
        </Button>
        <Button variant="outline" onClick={() => setGenerateOpen(true)} className="w-full" data-testid="btn-generate">
          <Wand2 className="w-4 h-4 mr-2" /> Genera testo
        </Button>
        <Card className="flex-1 overflow-hidden">
          <CardContent className="p-2 h-full">
            <ScrollArea className="h-full">
              <div className="space-y-1 p-1">
                {sessions.length === 0 ? (
                  <p className="text-xs text-slate-500 p-3">Nessuna conversazione</p>
                ) : sessions.map(s => (
                  <div
                    key={s.id}
                    onClick={() => loadSession(s.id)}
                    className={`p-2 rounded cursor-pointer flex items-start justify-between group ${currentSessionId === s.id ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-slate-100 dark:hover:bg-slate-800'}`}
                    data-testid={`session-${s.id}`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{s.titolo}</div>
                      <div className="text-xs text-slate-500">{s.message_count} msg · {new Date(s.updated_at).toLocaleDateString('it-IT')}</div>
                    </div>
                    <button onClick={(e) => deleteSession(s.id, e)} className="opacity-0 group-hover:opacity-100 p-1">
                      <Trash2 className="w-3 h-3 text-red-500" />
                    </button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Chat principale */}
      <Card className="flex-1 flex flex-col">
        <div className="border-b p-4 flex items-center justify-between">
          <div>
            <h1 className="font-bold flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-500" />
              Assistente AI
            </h1>
            {aiConfig && (
              <p className="text-xs text-slate-500">
                Provider: <Badge variant="outline" className="ml-1">{aiConfig.provider}</Badge>
                {' '}Model: <code className="text-xs">{aiConfig.provider === 'ollama' ? aiConfig.ollama_model : aiConfig.external_model}</code>
                {!aiConfig.enabled && <Badge variant="destructive" className="ml-2">Disabilitato</Badge>}
              </p>
            )}
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={includeContext} onChange={e => setIncludeContext(e.target.checked)} data-testid="toggle-context" />
            <span>Contesto app</span>
          </label>
        </div>

        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4 max-w-3xl mx-auto">
            {messages.length === 0 ? (
              <div className="text-center py-16">
                <Bot className="w-12 h-12 mx-auto text-slate-300 mb-3" />
                <p className="text-slate-500">Inizia una conversazione con l'assistente AI</p>
                <p className="text-sm text-slate-400 mt-2">Esempi: "Quali contratti scadono nei prossimi 30 giorni?", "Genera email sollecito per la rata di Marco Rossi"</p>
              </div>
            ) : (
              messages.map((m, i) => (
                <MessageBubble key={i} message={m} isUser={m.role === 'user'} />
              ))
            )}
            {loading && (
              <div className="flex gap-3" data-testid="loading">
                <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="rounded-2xl px-4 py-2 bg-slate-100 dark:bg-slate-800">
                  <Loader2 className="w-4 h-4 animate-spin" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        <div className="border-t p-4">
          <div className="max-w-3xl mx-auto flex gap-2">
            <Textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              placeholder="Scrivi un messaggio... (Shift+Invio per nuova riga)"
              rows={2}
              className="resize-none"
              disabled={loading}
              data-testid="input-message"
            />
            <Button onClick={sendMessage} disabled={loading || !input.trim()} data-testid="btn-send">
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </Card>

      {/* Dialog Genera */}
      <Dialog open={generateOpen} onOpenChange={(o) => { setGenerateOpen(o); if (!o) setGenResult(''); }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Genera testo con AI</DialogTitle>
            <DialogDescription>Crea email, clausole, report, disdette o testi liberi.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Tipo</Label>
              <Select value={genForm.tipo} onValueChange={v => setGenForm({...genForm, tipo: v})}>
                <SelectTrigger data-testid="select-gen-tipo"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="email_sollecito">Email sollecito pagamento</SelectItem>
                  <SelectItem value="clausola_contratto">Clausola contrattuale</SelectItem>
                  <SelectItem value="disdetta">Lettera di disdetta</SelectItem>
                  <SelectItem value="report_executive">Report executive</SelectItem>
                  <SelectItem value="free">Testo libero</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Istruzioni aggiuntive</Label>
              <Textarea value={genForm.istruzioni} onChange={e => setGenForm({...genForm, istruzioni: e.target.value})} rows={3} placeholder="Es. Per il contratto di Marco Rossi, importo €850 scaduto da 7 giorni" />
            </div>
            {genResult && (
              <div>
                <Label>Risultato</Label>
                <Textarea value={genResult} readOnly rows={10} className="font-mono text-sm" data-testid="gen-result" />
                <Button size="sm" variant="outline" className="mt-2" onClick={() => { navigator.clipboard.writeText(genResult); toast.success('Copiato'); }}>
                  Copia
                </Button>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setGenerateOpen(false)}>Chiudi</Button>
            <Button onClick={handleGenerate} disabled={genLoading} data-testid="btn-gen-confirm">
              {genLoading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generazione...</> : <><Wand2 className="w-4 h-4 mr-2" /> Genera</>}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
