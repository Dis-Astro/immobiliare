import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import api from '../stores';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { FileWarning, Upload, Trash2, AlertTriangle, FileText, Sparkles, Loader2 } from 'lucide-react';

const TIPI = [
  'contratto', 'visura_catastale', 'planimetria', 'certificazione_impianto',
  'agibilita', 'fattura', 'documento_identita', 'altro'
];

export default function DocumentiPage() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [filter, setFilter] = useState('all');
  const [aiLoading, setAiLoading] = useState(null);

  const [form, setForm] = useState({
    file: null,
    tipo: 'altro',
    descrizione: '',
    immobile_id: '',
    unita_id: '',
    contratto_id: '',
    soggetto_id: '',
    data_scadenza: ''
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const url = filter === 'in_scadenza' ? '/documenti/in-scadenza?giorni=90' : '/documenti';
      const res = await api.get(url);
      setDocs(res.data);
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [filter]);

  const handleUpload = async () => {
    if (!form.file) return toast.error('Seleziona un file');
    try {
      const fd = new FormData();
      fd.append('file', form.file);
      fd.append('tipo', form.tipo);
      if (form.descrizione) fd.append('descrizione', form.descrizione);
      if (form.immobile_id) fd.append('immobile_id', form.immobile_id);
      if (form.unita_id) fd.append('unita_id', form.unita_id);
      if (form.contratto_id) fd.append('contratto_id', form.contratto_id);
      if (form.soggetto_id) fd.append('soggetto_id', form.soggetto_id);
      if (form.data_scadenza) fd.append('data_scadenza', form.data_scadenza);
      await api.post('/documenti/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success('Documento caricato');
      setUploadOpen(false);
      setForm({ file: null, tipo: 'altro', descrizione: '', immobile_id: '', unita_id: '', contratto_id: '', soggetto_id: '', data_scadenza: '' });
      fetchData();
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Eliminare questo documento?')) return;
    try {
      await api.delete(`/documenti/${id}`);
      toast.success('Eliminato');
      fetchData();
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleAi = async (doc) => {
    setAiLoading(doc.id);
    try {
      const res = await api.post('/ai/analyze-document', {
        documento_id: doc.id,
        prompt: 'Analizza questo documento ed estrai i dati principali in formato strutturato (date, importi, parti coinvolte, scadenze). Segnala eventuali criticità.'
      });
      alert('Analisi AI:\n\n' + res.data.content);
    } catch (err) {
      toast.error('Errore AI: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAiLoading(null);
    }
  };

  return (
    <div className="space-y-6" data-testid="documenti-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-heading">Documenti</h1>
          <p className="text-slate-500">Archivio documenti immobili, contratti, soggetti</p>
        </div>
        <Button onClick={() => setUploadOpen(true)} data-testid="btn-upload-doc">
          <Upload className="w-4 h-4 mr-2" /> Carica documento
        </Button>
      </div>

      <div className="flex gap-2">
        <Button variant={filter==='all'?'default':'outline'} size="sm" onClick={() => setFilter('all')} data-testid="filter-all">Tutti</Button>
        <Button variant={filter==='in_scadenza'?'default':'outline'} size="sm" onClick={() => setFilter('in_scadenza')} data-testid="filter-scadenza">In scadenza (90gg)</Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-center text-slate-500 py-8">Caricamento...</p>
          ) : docs.length === 0 ? (
            <div className="text-center py-12">
              <FileWarning className="w-12 h-12 mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500">Nessun documento</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Collegato a</TableHead>
                  <TableHead>Data caricamento</TableHead>
                  <TableHead>Scadenza</TableHead>
                  <TableHead className="text-right">Azioni</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {docs.map(d => (
                  <TableRow key={d.id} data-testid={`doc-row-${d.id}`}>
                    <TableCell className="font-medium max-w-xs truncate">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-slate-400 flex-shrink-0" />
                        <span title={d.filename}>{d.filename}</span>
                      </div>
                      {d.descrizione && <div className="text-xs text-slate-500 ml-6 truncate">{d.descrizione}</div>}
                    </TableCell>
                    <TableCell><Badge variant="outline">{d.tipo}</Badge></TableCell>
                    <TableCell className="text-sm">
                      {d.immobile_titolo && <div>{d.immobile_titolo}</div>}
                      {d.unita_codice && <div className="text-xs text-slate-500">{d.unita_codice}</div>}
                      {d.contratto_codice && <div className="text-xs">{d.contratto_codice}</div>}
                      {!d.immobile_titolo && !d.contratto_codice && '-'}
                    </TableCell>
                    <TableCell className="text-sm">{d.created_at?.substring(0,10)}</TableCell>
                    <TableCell>
                      {d.data_scadenza ? (
                        <Badge variant={new Date(d.data_scadenza) < new Date() ? 'destructive' : 'outline'}>
                          {d.data_scadenza}
                        </Badge>
                      ) : <span className="text-slate-400 text-sm">-</span>}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon" onClick={() => handleAi(d)} disabled={aiLoading===d.id} title="Analizza con AI">
                          {aiLoading===d.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 text-purple-500" />}
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleDelete(d.id)} title="Elimina">
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

      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Carica nuovo documento</DialogTitle>
            <DialogDescription>I collegamenti a immobile/unità/contratto/soggetto sono opzionali.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>File * (max 50MB)</Label>
              <Input type="file" onChange={e => setForm({...form, file: e.target.files[0]})} data-testid="input-file" />
            </div>
            <div>
              <Label>Tipo</Label>
              <Select value={form.tipo} onValueChange={v => setForm({...form, tipo: v})}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TIPI.map(t => <SelectItem key={t} value={t}>{t.replace('_', ' ')}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Descrizione</Label>
              <Textarea value={form.descrizione} onChange={e => setForm({...form, descrizione: e.target.value})} rows={2} />
            </div>
            <div>
              <Label>Data scadenza (opzionale)</Label>
              <Input type="date" value={form.data_scadenza} onChange={e => setForm({...form, data_scadenza: e.target.value})} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUploadOpen(false)}>Annulla</Button>
            <Button onClick={handleUpload} data-testid="btn-confirm-upload">Carica</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
