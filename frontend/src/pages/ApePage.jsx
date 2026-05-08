import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import api from '../stores';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
  Plus, Upload, RefreshCw, FileText, Calendar, AlertTriangle,
  CheckCircle2, XCircle, History, Sparkles, Trash2, Pencil
} from 'lucide-react';

const CLASSI = ['A4','A3','A2','A1','B','C','D','E','F','G'];
const ZONE = ['A','B','C','D','E','F'];

const STATO_BADGE = {
  valido: { color: 'bg-emerald-500', icon: CheckCircle2, label: 'Valido' },
  in_scadenza: { color: 'bg-amber-500', icon: AlertTriangle, label: 'In scadenza' },
  scaduto: { color: 'bg-red-500', icon: XCircle, label: 'Scaduto' },
  sostituito: { color: 'bg-slate-400', icon: History, label: 'Sostituito' },
};

const CLASSE_COLOR = {
  A4: 'bg-emerald-700', A3: 'bg-emerald-600', A2: 'bg-emerald-500', A1: 'bg-green-500',
  B: 'bg-lime-500', C: 'bg-yellow-500', D: 'bg-amber-500',
  E: 'bg-orange-500', F: 'bg-red-500', G: 'bg-red-700'
};

function StatoBadge({ stato }) {
  const cfg = STATO_BADGE[stato] || STATO_BADGE.valido;
  const Icon = cfg.icon;
  return (
    <Badge className={`${cfg.color} text-white border-0 gap-1`} data-testid={`ape-stato-${stato}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </Badge>
  );
}

function ClasseBadge({ classe }) {
  return (
    <Badge className={`${CLASSE_COLOR[classe] || 'bg-slate-500'} text-white border-0 font-bold`}>
      {classe}
    </Badge>
  );
}

export default function ApePage() {
  const navigate = useNavigate();
  const [apeList, setApeList] = useState([]);
  const [unitaList, setUnitaList] = useState([]);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState('all'); // all | in_scadenza | scaduti
  const [loading, setLoading] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [editingApe, setEditingApe] = useState(null);
  const [rimandoOpen, setRimandoOpen] = useState(false);
  const [replaceOpen, setReplaceOpen] = useState(false);
  const [storicoOpen, setStoricoOpen] = useState(false);
  const [analyzeLoading, setAnalyzeLoading] = useState(null);
  const [aiResultOpen, setAiResultOpen] = useState(false);
  const [aiResult, setAiResult] = useState({ title: '', content: '' });

  const [form, setForm] = useState({
    unita_id: '',
    classe_energetica: 'D',
    data_emissione: new Date().toISOString().split('T')[0],
    data_scadenza: new Date(new Date().setFullYear(new Date().getFullYear() + 10)).toISOString().split('T')[0],
    certificatore_nome: '',
    certificatore_albo: '',
    zona_climatica: '',
    epgl_nren: '',
    superficie_utile_mq: '',
    note: '',
    file: null
  });

  const [rimandoForm, setRimandoForm] = useState({ nuova_scadenza: '', motivazione: '' });
  const [replaceForm, setReplaceForm] = useState({ file: null, motivazione: '' });

  const fetchData = async () => {
    setLoading(true);
    try {
      let url = '/ape';
      if (filter === 'in_scadenza') url = '/ape/in-scadenza?giorni=90';
      if (filter === 'scaduti') url = '/ape/scaduti';
      const [apeRes, unitaRes, statsRes] = await Promise.all([
        api.get(url),
        api.get('/unita'),
        api.get('/ape/stats/dashboard')
      ]);
      setApeList(apeRes.data);
      setUnitaList(unitaRes.data);
      setStats(statsRes.data);
    } catch (err) {
      toast.error('Errore caricamento APE: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [filter]);

  const resetForm = () => {
    setForm({
      unita_id: '', classe_energetica: 'D',
      data_emissione: new Date().toISOString().split('T')[0],
      data_scadenza: new Date(new Date().setFullYear(new Date().getFullYear() + 10)).toISOString().split('T')[0],
      certificatore_nome: '', certificatore_albo: '', zona_climatica: '',
      epgl_nren: '', superficie_utile_mq: '', note: '', file: null
    });
  };

  const handleCreate = async () => {
    if (!form.unita_id || !form.certificatore_nome) {
      toast.error('Compila unità e certificatore');
      return;
    }
    try {
      if (form.file) {
        const fd = new FormData();
        fd.append('file', form.file);
        fd.append('unita_id', form.unita_id);
        fd.append('classe_energetica', form.classe_energetica);
        fd.append('data_emissione', form.data_emissione);
        fd.append('data_scadenza', form.data_scadenza);
        fd.append('certificatore_nome', form.certificatore_nome);
        if (form.certificatore_albo) fd.append('certificatore_albo', form.certificatore_albo);
        if (form.zona_climatica) fd.append('zona_climatica', form.zona_climatica);
        if (form.epgl_nren) fd.append('epgl_nren', form.epgl_nren);
        if (form.superficie_utile_mq) fd.append('superficie_utile_mq', form.superficie_utile_mq);
        if (form.note) fd.append('note', form.note);
        await api.post('/ape/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      } else {
        await api.post('/ape', {
          unita_id: form.unita_id,
          classe_energetica: form.classe_energetica,
          data_emissione: form.data_emissione,
          data_scadenza: form.data_scadenza,
          certificatore_nome: form.certificatore_nome,
          certificatore_albo: form.certificatore_albo || null,
          zona_climatica: form.zona_climatica || null,
          epgl_nren: form.epgl_nren ? parseFloat(form.epgl_nren) : null,
          superficie_utile_mq: form.superficie_utile_mq ? parseFloat(form.superficie_utile_mq) : null,
          note: form.note || null
        });
      }
      toast.success('APE creato');
      setCreateOpen(false);
      resetForm();
      fetchData();
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleRimando = async () => {
    if (!rimandoForm.nuova_scadenza || !rimandoForm.motivazione) {
      toast.error('Compila tutti i campi');
      return;
    }
    try {
      await api.put(`/ape/${editingApe.id}/scadenza`, {
        nuova_scadenza: rimandoForm.nuova_scadenza,
        motivazione: rimandoForm.motivazione
      });
      toast.success('Scadenza aggiornata');
      setRimandoOpen(false);
      setRimandoForm({ nuova_scadenza: '', motivazione: '' });
      fetchData();
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleReplace = async () => {
    if (!replaceForm.file || !replaceForm.motivazione) {
      toast.error('Seleziona file e motivazione');
      return;
    }
    try {
      const fd = new FormData();
      fd.append('file', replaceForm.file);
      fd.append('motivazione', replaceForm.motivazione);
      await api.put(`/ape/${editingApe.id}/file`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success('File sostituito');
      setReplaceOpen(false);
      setReplaceForm({ file: null, motivazione: '' });
      fetchData();
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Eliminare definitivamente questo APE?')) return;
    try {
      await api.delete(`/ape/${id}`);
      toast.success('APE eliminato');
      fetchData();
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleAnalyzeAi = async (ape) => {
    if (!ape.file_path) {
      toast.error('Nessun file caricato per questo APE');
      return;
    }
    setAnalyzeLoading(ape.id);
    try {
      const res = await api.post('/ai/analyze-document', {
        ape_id: ape.id,
        prompt: 'Analizza questo APE ed estrai: classe energetica dichiarata, EPgl,nren, certificatore, validità. Rileva eventuali incongruenze con i dati registrati: classe=' + ape.classe_energetica + ', scadenza=' + ape.data_scadenza
      });
      toast.success('Analisi completata', { duration: 4000 });
      setAiResult({ title: `Analisi APE classe ${ape.classe_energetica}`, content: res.data.content });
      setAiResultOpen(true);
    } catch (err) {
      toast.error('Errore AI: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAnalyzeLoading(null);
    }
  };

  return (
    <div className="space-y-6" data-testid="ape-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-heading">Gestione APE</h1>
          <p className="text-slate-500">Attestati Prestazione Energetica per unità immobiliari</p>
        </div>
        <Button onClick={() => { resetForm(); setCreateOpen(true); }} data-testid="btn-new-ape">
          <Plus className="w-4 h-4 mr-2" /> Nuovo APE
        </Button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card><CardContent className="pt-6">
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-sm text-slate-500">APE attivi</p>
          </CardContent></Card>
          <Card><CardContent className="pt-6">
            <div className="text-2xl font-bold text-emerald-600">{stats.validi}</div>
            <p className="text-sm text-slate-500">Validi</p>
          </CardContent></Card>
          <Card><CardContent className="pt-6">
            <div className="text-2xl font-bold text-amber-600">{stats.in_scadenza}</div>
            <p className="text-sm text-slate-500">In scadenza (90gg)</p>
          </CardContent></Card>
          <Card><CardContent className="pt-6">
            <div className="text-2xl font-bold text-red-600">{stats.scaduti}</div>
            <p className="text-sm text-slate-500">Scaduti</p>
          </CardContent></Card>
        </div>
      )}

      {/* Filtri */}
      <div className="flex gap-2">
        <Button variant={filter==='all'?'default':'outline'} size="sm" onClick={() => setFilter('all')} data-testid="filter-all">Tutti</Button>
        <Button variant={filter==='in_scadenza'?'default':'outline'} size="sm" onClick={() => setFilter('in_scadenza')} data-testid="filter-in-scadenza">In scadenza</Button>
        <Button variant={filter==='scaduti'?'default':'outline'} size="sm" onClick={() => setFilter('scaduti')} data-testid="filter-scaduti">Scaduti</Button>
      </div>

      {/* Tabella */}
      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-center text-slate-500 py-8">Caricamento...</p>
          ) : apeList.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500">Nessun APE trovato</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Unità</TableHead>
                  <TableHead>Classe</TableHead>
                  <TableHead>Emissione</TableHead>
                  <TableHead>Scadenza</TableHead>
                  <TableHead>Certificatore</TableHead>
                  <TableHead>Stato</TableHead>
                  <TableHead className="text-right">Azioni</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {apeList.map(ape => (
                  <TableRow key={ape.id} data-testid={`ape-row-${ape.id}`}>
                    <TableCell className="font-mono text-sm">
                      {ape.unita_codice || ape.unita_id?.substring(0, 8)}
                      {ape.immobile_titolo && (
                        <div className="text-xs text-slate-500">{ape.immobile_titolo}</div>
                      )}
                    </TableCell>
                    <TableCell><ClasseBadge classe={ape.classe_energetica} /></TableCell>
                    <TableCell className="text-sm">{ape.data_emissione}</TableCell>
                    <TableCell>
                      <div className="text-sm">{ape.data_scadenza}</div>
                      {ape.giorni_alla_scadenza !== null && (
                        <div className={`text-xs ${ape.giorni_alla_scadenza < 0 ? 'text-red-600' : ape.giorni_alla_scadenza < 90 ? 'text-amber-600' : 'text-slate-500'}`}>
                          {ape.giorni_alla_scadenza < 0 ? `${Math.abs(ape.giorni_alla_scadenza)}gg fa` : `tra ${ape.giorni_alla_scadenza}gg`}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-sm">{ape.certificatore_nome}</TableCell>
                    <TableCell><StatoBadge stato={ape.stato} /></TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        {ape.file_path && (
                          <Button variant="ghost" size="icon" onClick={() => handleAnalyzeAi(ape)} disabled={analyzeLoading===ape.id} data-testid={`btn-ai-${ape.id}`} title="Analizza con AI">
                            <Sparkles className={`w-4 h-4 ${analyzeLoading===ape.id?'animate-pulse text-purple-500':''}`} />
                          </Button>
                        )}
                        <Button variant="ghost" size="icon" onClick={() => { setEditingApe(ape); setRimandoForm({ nuova_scadenza: ape.data_scadenza, motivazione: '' }); setRimandoOpen(true); }} data-testid={`btn-rimando-${ape.id}`} title="Rimanda scadenza">
                          <Calendar className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => { setEditingApe(ape); setReplaceForm({ file: null, motivazione: '' }); setReplaceOpen(true); }} data-testid={`btn-replace-${ape.id}`} title="Sostituisci file">
                          <Upload className="w-4 h-4" />
                        </Button>
                        {ape.storico_modifiche?.length > 0 && (
                          <Button variant="ghost" size="icon" onClick={() => { setEditingApe(ape); setStoricoOpen(true); }} data-testid={`btn-storico-${ape.id}`} title="Storico">
                            <History className="w-4 h-4" />
                          </Button>
                        )}
                        <Button variant="ghost" size="icon" onClick={() => handleDelete(ape.id)} data-testid={`btn-delete-${ape.id}`} title="Elimina">
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Dialog crea APE */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="dialog-new-ape">
          <DialogHeader>
            <DialogTitle>Nuovo APE</DialogTitle>
            <DialogDescription>
              Crea un nuovo Attestato di Prestazione Energetica. Il file PDF è opzionale ma consigliato.
            </DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Label>Unità *</Label>
              <Select value={form.unita_id} onValueChange={v => setForm({...form, unita_id: v})}>
                <SelectTrigger data-testid="select-unita"><SelectValue placeholder="Seleziona unità" /></SelectTrigger>
                <SelectContent>
                  {unitaList.map(u => (
                    <SelectItem key={u.id} value={u.id}>{u.codice_unita} - {u.tipo_immobile} ({u.mq||'?'}mq)</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Classe energetica *</Label>
              <Select value={form.classe_energetica} onValueChange={v => setForm({...form, classe_energetica: v})}>
                <SelectTrigger data-testid="select-classe"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CLASSI.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Zona climatica</Label>
              <Select value={form.zona_climatica} onValueChange={v => setForm({...form, zona_climatica: v})}>
                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                <SelectContent>
                  {ZONE.map(z => <SelectItem key={z} value={z}>{z}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Data emissione *</Label>
              <Input type="date" value={form.data_emissione} onChange={e => setForm({...form, data_emissione: e.target.value})} data-testid="input-emissione" />
            </div>
            <div>
              <Label>Data scadenza *</Label>
              <Input type="date" value={form.data_scadenza} onChange={e => setForm({...form, data_scadenza: e.target.value})} data-testid="input-scadenza" />
            </div>
            <div>
              <Label>Certificatore *</Label>
              <Input value={form.certificatore_nome} onChange={e => setForm({...form, certificatore_nome: e.target.value})} data-testid="input-cert-nome" />
            </div>
            <div>
              <Label>N. iscrizione albo</Label>
              <Input value={form.certificatore_albo} onChange={e => setForm({...form, certificatore_albo: e.target.value})} />
            </div>
            <div>
              <Label>EPgl,nren (kWh/m²/anno)</Label>
              <Input type="number" step="0.01" value={form.epgl_nren} onChange={e => setForm({...form, epgl_nren: e.target.value})} />
            </div>
            <div>
              <Label>Superficie utile (m²)</Label>
              <Input type="number" step="0.01" value={form.superficie_utile_mq} onChange={e => setForm({...form, superficie_utile_mq: e.target.value})} />
            </div>
            <div className="col-span-2">
              <Label>Note</Label>
              <Textarea value={form.note} onChange={e => setForm({...form, note: e.target.value})} rows={2} />
            </div>
            <div className="col-span-2">
              <Label>File PDF/immagine (opzionale, max 50MB)</Label>
              <Input type="file" accept=".pdf,image/*" onChange={e => setForm({...form, file: e.target.files[0]})} data-testid="input-file" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Annulla</Button>
            <Button onClick={handleCreate} data-testid="btn-save-ape">Crea APE</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog rimando scadenza */}
      <Dialog open={rimandoOpen} onOpenChange={setRimandoOpen}>
        <DialogContent data-testid="dialog-rimando">
          <DialogHeader>
            <DialogTitle>Rimanda/Modifica scadenza APE</DialogTitle>
            <DialogDescription>
              Scadenza attuale: <strong>{editingApe?.data_scadenza}</strong>. La modifica viene tracciata nello storico.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Nuova scadenza *</Label>
              <Input type="date" value={rimandoForm.nuova_scadenza} onChange={e => setRimandoForm({...rimandoForm, nuova_scadenza: e.target.value})} data-testid="input-nuova-scadenza" />
            </div>
            <div>
              <Label>Motivazione *</Label>
              <Textarea value={rimandoForm.motivazione} onChange={e => setRimandoForm({...rimandoForm, motivazione: e.target.value})} rows={3} placeholder="Es. Ristrutturazione completata, validità prorogata in attesa nuova certificazione" data-testid="input-motivazione" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRimandoOpen(false)}>Annulla</Button>
            <Button onClick={handleRimando} data-testid="btn-confirm-rimando">Conferma</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog sostituzione file */}
      <Dialog open={replaceOpen} onOpenChange={setReplaceOpen}>
        <DialogContent data-testid="dialog-replace">
          <DialogHeader>
            <DialogTitle>Sostituisci file APE</DialogTitle>
            <DialogDescription>
              File attuale: <strong>{editingApe?.file_name || 'nessuno'}</strong>
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Nuovo file *</Label>
              <Input type="file" accept=".pdf,image/*" onChange={e => setReplaceForm({...replaceForm, file: e.target.files[0]})} data-testid="input-replace-file" />
            </div>
            <div>
              <Label>Motivazione *</Label>
              <Textarea value={replaceForm.motivazione} onChange={e => setReplaceForm({...replaceForm, motivazione: e.target.value})} rows={2} placeholder="Es. Versione aggiornata con correzioni" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReplaceOpen(false)}>Annulla</Button>
            <Button onClick={handleReplace} data-testid="btn-confirm-replace">Sostituisci</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog storico */}
      <Dialog open={storicoOpen} onOpenChange={setStoricoOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Storico modifiche APE</DialogTitle>
            <DialogDescription>Cronologia delle modifiche di scadenza e sostituzione file con motivazione e autore.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {editingApe?.storico_modifiche?.length === 0 ? (
              <p className="text-sm text-slate-500">Nessuna modifica registrata</p>
            ) : editingApe?.storico_modifiche?.map((s, i) => (
              <div key={i} className="border-l-4 border-blue-500 pl-3 py-2 bg-slate-50 dark:bg-slate-800 rounded">
                <div className="flex justify-between text-sm">
                  <span className="font-medium">{s.azione}</span>
                  <span className="text-xs text-slate-500">{new Date(s.timestamp).toLocaleString('it-IT')}</span>
                </div>
                <div className="text-xs text-slate-600 dark:text-slate-300 mt-1">
                  Da <code>{s.valore_precedente}</code> → <code>{s.valore_nuovo}</code>
                </div>
                {s.motivazione && <div className="text-sm mt-1 italic">"{s.motivazione}"</div>}
                <div className="text-xs text-slate-400 mt-1">{s.user_nome}</div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
      {/* Dialog risultato AI */}
      <Dialog open={aiResultOpen} onOpenChange={setAiResultOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto" data-testid="dialog-ape-ai-result">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-500" />
              {aiResult.title}
            </DialogTitle>
            <DialogDescription>Analisi generata dall'AI sull'APE selezionato.</DialogDescription>
          </DialogHeader>
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <pre className="whitespace-pre-wrap text-sm bg-slate-50 dark:bg-slate-900 p-4 rounded-lg">{aiResult.content}</pre>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { navigator.clipboard.writeText(aiResult.content); toast.success('Copiato'); }}>Copia</Button>
            <Button onClick={() => setAiResultOpen(false)}>Chiudi</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
