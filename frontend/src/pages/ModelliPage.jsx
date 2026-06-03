import React, { useEffect, useState } from 'react';
import api from '../stores';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Upload, FileText, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

export default function ModelliPage() {
  const [modelli, setModelli] = useState([]);
  const [contratti, setContratti] = useState([]);
  const [selectedContratto, setSelectedContratto] = useState('');
  const [preview, setPreview] = useState(null);
  const [form, setForm] = useState({ nome: '', tipo: 'contratto', descrizione: '', file: null });
  const [loading, setLoading] = useState(false);

  const fetchModelli = async () => {
    const res = await api.get('/modelli');
    setModelli(res.data || []);
  };

  useEffect(() => {
    fetchModelli().catch(() => toast.error('Errore caricamento modelli'));
    api.get('/contratti?limit=100').then(res => setContratti(res.data || [])).catch(() => {});
  }, []);

  const upload = async () => {
    if (!form.nome || !form.file) return toast.error('Nome e file sono obbligatori');
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('nome', form.nome);
      fd.append('tipo', form.tipo);
      if (form.descrizione) fd.append('descrizione', form.descrizione);
      fd.append('file', form.file);
      await api.post('/modelli/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success('Modello caricato');
      setForm({ nome: '', tipo: 'contratto', descrizione: '', file: null });
      await fetchModelli();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Errore upload modello');
    } finally {
      setLoading(false);
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Eliminare questo modello?')) return;
    await api.delete(`/modelli/${id}`);
    toast.success('Modello eliminato');
    fetchModelli();
  };

  const showPreview = async (modello) => {
    if (!selectedContratto) return toast.error('Seleziona un contratto');
    if (modello.formato !== 'docx') return toast.error('La compilazione automatica è disponibile per DOCX');
    try {
      const res = await api.post(`/modelli/${modello.id}/preview`, {
        ref_tipo: 'contratto',
        ref_id: selectedContratto,
        valori_extra: {},
      });
      setPreview(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Errore preview');
    }
  };

  const compila = async (modello) => {
    if (!selectedContratto) return toast.error('Seleziona un contratto');
    try {
      const res = await api.post(`/modelli/${modello.id}/compila`, {
        ref_tipo: 'contratto',
        ref_id: selectedContratto,
        formato_output: 'docx',
        valori_extra: {},
        salva_documento: true,
      }, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `${modello.nome}_${selectedContratto.slice(0, 8)}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Documento compilato e salvato');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Errore compilazione');
    }
  };

  return (
    <div className="space-y-6" data-testid="modelli-page">
      <div>
        <h1 className="text-2xl font-bold font-heading">Modelli</h1>
        <p className="text-slate-500">Carica DOCX compilabili o PDF guida per contratti e documenti</p>
      </div>

      <Card>
        <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
          <div>
            <Label>Nome</Label>
            <Input value={form.nome} onChange={e => setForm({ ...form, nome: e.target.value })} />
          </div>
          <div>
            <Label>Tipo</Label>
            <Input value={form.tipo} onChange={e => setForm({ ...form, tipo: e.target.value })} />
          </div>
          <div>
            <Label>Descrizione</Label>
            <Input value={form.descrizione} onChange={e => setForm({ ...form, descrizione: e.target.value })} />
          </div>
          <div>
            <Label>File DOCX/PDF</Label>
            <Input type="file" accept=".docx,.pdf" onChange={e => setForm({ ...form, file: e.target.files?.[0] })} />
          </div>
          <Button onClick={upload} disabled={loading}>
            <Upload className="w-4 h-4 mr-2" /> Carica
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label>Contratto per compilazione</Label>
            <select
              className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
              value={selectedContratto}
              onChange={e => { setSelectedContratto(e.target.value); setPreview(null); }}
            >
              <option value="">Seleziona contratto</option>
              {contratti.map(c => (
                <option key={c.id} value={c.id}>
                  {c.codice_contratto} - {c.affittuario_nome || 'N/D'} - {c.immobile_titolo || 'N/D'}
                </option>
              ))}
            </select>
          </div>
          <div className="text-sm text-slate-500 flex items-end">
            I DOCX vengono compilati usando i placeholder rilevati e salvati nei documenti del contratto.
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Formato</TableHead>
                <TableHead>Placeholder</TableHead>
                <TableHead>Caricato</TableHead>
                <TableHead className="text-right">Azioni</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {modelli.map(m => (
                <TableRow key={m.id}>
                  <TableCell>
                    <div className="font-medium flex items-center gap-2">
                      <FileText className="w-4 h-4 text-slate-400" /> {m.nome}
                    </div>
                    <div className="text-xs text-slate-500">{m.filename}</div>
                  </TableCell>
                  <TableCell><Badge variant="outline">{m.formato}</Badge></TableCell>
                  <TableCell className="max-w-md">
                    {(m.placeholders || []).length ? (
                      <div className="flex flex-wrap gap-1">
                        {m.placeholders.slice(0, 10).map(p => <Badge key={p} variant="secondary">{p}</Badge>)}
                      </div>
                    ) : <span className="text-sm text-slate-400">Nessuno</span>}
                  </TableCell>
                  <TableCell>{m.uploaded_at?.substring(0, 10)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                    <Button variant="outline" size="sm" onClick={() => showPreview(m)} disabled={m.formato !== 'docx'}>
                      Preview
                    </Button>
                    <Button size="sm" onClick={() => compila(m)} disabled={m.formato !== 'docx'}>
                      Compila
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => remove(m.id)}>
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {preview && (
        <Card>
          <CardContent className="pt-6 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">Preview campi</h2>
              <Badge variant={preview.mancanti?.length ? 'destructive' : 'default'}>
                {preview.mancanti?.length ? `${preview.mancanti.length} mancanti` : 'Completo'}
              </Badge>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
              {preview.placeholders.map(p => (
                <div key={p} className="border rounded p-2">
                  <div className="font-mono text-xs text-slate-500">{p}</div>
                  <div className={preview.valori[p] ? '' : 'text-red-600'}>
                    {preview.valori[p] || 'Valore mancante'}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
