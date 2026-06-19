import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import api from '../stores';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
  Upload, Plus, FileText, Trash2, Pencil, Download, Eye, Loader2, Sparkles
} from 'lucide-react';

const TIPI = [
  { value: 'residenziale', label: 'Residenziale' },
  { value: 'commerciale', label: 'Commerciale' },
  { value: 'transitorio', label: 'Transitorio' },
  { value: 'studenti', label: 'Studenti' },
  { value: 'personalizzato', label: 'Personalizzato' },
];

const DEFAULT_HTML = `<h1>Contratto di locazione</h1>
<p>Con la presente scrittura privata tra <strong>{{ locatore.nome }}</strong> e <strong>{{ affittuario.nome }}</strong> si stipula il contratto {{ contratto.codice_contratto }}.</p>
<p>L'unita oggetto del contratto e identificata come <strong>{{ unita.codice_unita }}</strong> presso {{ immobile.titolo }}, {{ immobile.indirizzo }}.</p>
<p>Il contratto decorre dal {{ contratto.data_inizio|data_it }} al {{ contratto.data_scadenza|data_it }}.</p>
<p>Il canone pattuito e pari a <strong>{{ contratto.canone_importo|euro }}</strong> con periodicita {{ contratto.periodicita }}.</p>
<div class="signature-row">
  <div class="signature-box">Locatore</div>
  <div class="signature-box">Affittuario</div>
</div>`;

const emptyForm = {
  nome: '',
  tipo: 'personalizzato',
  descrizione: '',
  contenuto_html: DEFAULT_HTML,
  attivo: true,
};

function downloadBlob(response, fallbackName) {
  const disposition = response.headers?.['content-disposition'] || '';
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || fallbackName;
  const blob = new Blob([response.data], { type: response.headers?.['content-type'] || 'application/octet-stream' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default function ModelliContrattoPage() {
  const [searchParams] = useSearchParams();
  const initialContrattoId = searchParams.get('contrattoId') || '';

  const [modelli, setModelli] = useState([]);
  const [contratti, setContratti] = useState([]);
  const [variabili, setVariabili] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [file, setFile] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [generateForm, setGenerateForm] = useState({
    modello_id: '',
    contratto_id: initialContrattoId,
    formato: 'pdf',
    salva_documento: true,
  });

  const activeModelCount = useMemo(() => modelli.filter(m => m.attivo).length, [modelli]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [modelliRes, contrattiRes, variabiliRes] = await Promise.all([
        api.get('/modelli-contratto'),
        api.get('/contratti?limit=100'),
        api.get('/modelli-contratto/variabili')
      ]);
      setModelli(modelliRes.data || []);
      setContratti(contrattiRes.data || []);
      setVariabili(variabiliRes.data?.variabili || []);
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const openCreate = () => {
    setSelected(null);
    setFile(null);
    setForm(emptyForm);
    setEditOpen(true);
  };

  const openEdit = (modello) => {
    setSelected(modello);
    setFile(null);
    setForm({
      nome: modello.nome || '',
      tipo: modello.tipo || 'personalizzato',
      descrizione: modello.descrizione || '',
      contenuto_html: modello.contenuto_html || DEFAULT_HTML,
      attivo: modello.attivo !== false,
    });
    setEditOpen(true);
  };

  const openGenerate = (modello) => {
    setSelected(modello);
    setGenerateForm({
      modello_id: modello.id,
      contratto_id: initialContrattoId || contratti[0]?.id || '',
      formato: 'pdf',
      salva_documento: true,
    });
    setGenerateOpen(true);
  };

  const handleSave = async () => {
    if (!form.nome.trim() && !file) return toast.error('Inserisci un nome o carica un file');
    setSaving(true);
    try {
      if (!selected && file) {
        const fd = new FormData();
        fd.append('file', file);
        if (form.nome.trim()) fd.append('nome', form.nome.trim());
        fd.append('tipo', form.tipo);
        if (form.descrizione.trim()) fd.append('descrizione', form.descrizione.trim());
        fd.append('attivo', form.attivo ? 'true' : 'false');
        await api.post('/modelli-contratto/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      } else if (selected) {
        await api.put(`/modelli-contratto/${selected.id}`, form);
      } else {
        await api.post('/modelli-contratto', form);
      }
      toast.success(selected ? 'Modello aggiornato' : 'Modello creato');
      setEditOpen(false);
      fetchData();
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (modello) => {
    if (!confirm(`Eliminare il modello "${modello.nome}"?`)) return;
    try {
      await api.delete(`/modelli-contratto/${modello.id}`);
      toast.success('Modello eliminato');
      fetchData();
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleToggle = async (modello, checked) => {
    try {
      await api.put(`/modelli-contratto/${modello.id}`, { attivo: checked });
      setModelli(current => current.map(m => m.id === modello.id ? { ...m, attivo: checked } : m));
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handlePreview = async (modello) => {
    try {
      const query = initialContrattoId ? `?contratto_id=${initialContrattoId}` : '';
      const res = await api.get(`/modelli-contratto/${modello.id}/preview${query}`, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener,noreferrer');
      setTimeout(() => window.URL.revokeObjectURL(url), 30000);
    } catch (err) {
      toast.error('Errore anteprima: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleGenerate = async () => {
    if (!generateForm.contratto_id) return toast.error('Seleziona un contratto');
    setGenerating(true);
    try {
      const res = await api.post('/modelli-contratto/genera', generateForm, { responseType: 'blob' });
      downloadBlob(res, `contratto_generato.${generateForm.formato}`);
      toast.success(generateForm.salva_documento && generateForm.formato === 'pdf' ? 'Documento generato e salvato' : 'Documento generato');
      setGenerateOpen(false);
    } catch (err) {
      toast.error('Errore generazione: ' + (err.response?.data?.detail || err.message));
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="modelli-contratto-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-heading">Modelli Contratto</h1>
          <p className="text-slate-500">{modelli.length} modelli, {activeModelCount} attivi</p>
        </div>
        <Button onClick={openCreate} data-testid="btn-new-modello-contratto">
          <Plus className="w-4 h-4 mr-2" /> Nuovo modello
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-slate-500">Caricamento...</div>
          ) : modelli.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-500">Nessun modello contratto</p>
              <Button className="mt-4" onClick={openCreate}>
                <Upload className="w-4 h-4 mr-2" /> Carica modello
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Placeholder</TableHead>
                  <TableHead>Origine</TableHead>
                  <TableHead>Attivo</TableHead>
                  <TableHead className="text-right">Azioni</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {modelli.map((modello) => (
                  <TableRow key={modello.id}>
                    <TableCell>
                      <div className="font-medium">{modello.nome}</div>
                      {modello.descrizione && <div className="text-xs text-slate-500 max-w-sm truncate">{modello.descrizione}</div>}
                    </TableCell>
                    <TableCell><Badge variant="outline" className="capitalize">{modello.tipo}</Badge></TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1 max-w-md">
                        {(modello.variabili_richieste || []).slice(0, 4).map(v => (
                          <Badge key={v} variant="secondary" className="font-mono text-[11px]">{v}</Badge>
                        ))}
                        {(modello.variabili_richieste || []).length > 4 && (
                          <Badge variant="outline">+{modello.variabili_richieste.length - 4}</Badge>
                        )}
                        {(modello.variabili_richieste || []).length === 0 && (
                          <span className="text-sm text-slate-400">-</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">
                      {modello.formato_origine || 'html'}
                      {modello.filename_originale && <div className="text-xs text-slate-500 max-w-[180px] truncate">{modello.filename_originale}</div>}
                    </TableCell>
                    <TableCell>
                      <Switch checked={modello.attivo !== false} onCheckedChange={(checked) => handleToggle(modello, checked)} />
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon" onClick={() => handlePreview(modello)} title="Anteprima">
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => openGenerate(modello)} title="Genera">
                          <Sparkles className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => openEdit(modello)} title="Modifica">
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleDelete(modello)} title="Elimina">
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

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-4xl max-h-[88vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selected ? 'Modifica modello' : 'Nuovo modello contratto'}</DialogTitle>
            <DialogDescription>HTML, TXT o DOCX con placeholder Jinja.</DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-5">
            <div className="space-y-4">
              {!selected && (
                <div>
                  <Label>File modello</Label>
                  <Input type="file" accept=".html,.htm,.txt,.md,.docx" onChange={e => setFile(e.target.files?.[0] || null)} />
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <Label>Nome</Label>
                  <Input value={form.nome} onChange={e => setForm({ ...form, nome: e.target.value })} />
                </div>
                <div>
                  <Label>Tipo</Label>
                  <Select value={form.tipo} onValueChange={value => setForm({ ...form, tipo: value })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {TIPI.map(tipo => <SelectItem key={tipo.value} value={tipo.value}>{tipo.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <Label>Descrizione</Label>
                <Input value={form.descrizione} onChange={e => setForm({ ...form, descrizione: e.target.value })} />
              </div>
              <div>
                <Label>Contenuto HTML</Label>
                <Textarea
                  value={form.contenuto_html}
                  onChange={e => setForm({ ...form, contenuto_html: e.target.value })}
                  rows={15}
                  className="font-mono text-sm"
                  disabled={!selected && !!file}
                />
              </div>
              <div className="flex items-center gap-3">
                <Switch checked={form.attivo} onCheckedChange={checked => setForm({ ...form, attivo: checked })} />
                <Label>Attivo</Label>
              </div>
            </div>

            <div className="border rounded-lg p-3 bg-slate-50 dark:bg-slate-900 h-fit">
              <div className="font-medium text-sm mb-2">Placeholder</div>
              <div className="space-y-1 max-h-[420px] overflow-auto">
                {variabili.map(item => (
                  <button
                    key={item.path}
                    type="button"
                    className="block w-full text-left text-xs rounded px-2 py-1 hover:bg-white dark:hover:bg-slate-800"
                    onClick={() => navigator.clipboard.writeText(`{{ ${item.path} }}`).then(() => toast.success('Placeholder copiato'))}
                  >
                    <span className="font-mono">{item.path}</span>
                    <span className="block text-slate-500">{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>Annulla</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Salva
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={generateOpen} onOpenChange={setGenerateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Genera contratto</DialogTitle>
            <DialogDescription>{selected?.nome}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Contratto</Label>
              <Select
                value={generateForm.contratto_id || 'none'}
                onValueChange={value => setGenerateForm({ ...generateForm, contratto_id: value === 'none' ? '' : value })}
              >
                <SelectTrigger><SelectValue placeholder="Seleziona contratto" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none" disabled>Nessun contratto selezionato</SelectItem>
                  {contratti.map(contratto => (
                    <SelectItem key={contratto.id} value={contratto.id}>
                      {contratto.codice_contratto} - {contratto.affittuario_nome || 'N/A'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Formato</Label>
              <Select value={generateForm.formato} onValueChange={value => setGenerateForm({ ...generateForm, formato: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="html">HTML</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-3">
              <Switch
                checked={generateForm.salva_documento}
                onCheckedChange={checked => setGenerateForm({ ...generateForm, salva_documento: checked })}
                disabled={generateForm.formato !== 'pdf'}
              />
              <Label>Salva nei documenti del contratto</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setGenerateOpen(false)}>Annulla</Button>
            <Button onClick={handleGenerate} disabled={generating}>
              {generating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
              Genera
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
