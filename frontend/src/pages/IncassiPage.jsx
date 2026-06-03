import React, { useState } from 'react';
import api from '../stores';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Upload, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';

const badgeVariant = {
  match_certo: 'default',
  match_probabile: 'secondary',
  da_revisionare: 'outline',
  non_abbinato: 'destructive',
};

export default function IncassiPage() {
  const [file, setFile] = useState(null);
  const [matches, setMatches] = useState([]);
  const [rate, setRate] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchSupportData = async () => {
    const [rateRes, logsRes] = await Promise.all([
      api.get('/incassi/rate-pendenti'),
      api.get('/incassi/import-log'),
    ]);
    setRate(rateRes.data || []);
    setLogs(logsRes.data || []);
  };

  React.useEffect(() => {
    fetchSupportData().catch(() => {});
  }, []);

  const preview = async () => {
    if (!file) return toast.error('Seleziona un file CSV o XLSX');
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await api.post('/incassi/import-preview', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setMatches(res.data.matches || []);
      toast.success(`Analizzati ${res.data.total_movimenti} movimenti`);
      fetchSupportData().catch(() => {});
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Errore import incassi');
    } finally {
      setLoading(false);
    }
  };

  const conferma = async (match) => {
    if (!match.rata_id) return;
    try {
      await api.post('/incassi/conferma', {
        rata_id: match.rata_id,
        importo: match.movimento.importo,
        data_incasso: match.movimento.data_movimento,
        metodo: 'bonifico',
        riferimento: match.movimento.riferimento,
        note: match.movimento.causale,
      });
      toast.success('Incasso confermato');
      setMatches(prev => prev.filter(m => m !== match));
      fetchSupportData().catch(() => {});
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Errore conferma incasso');
    }
  };

  const changeRata = (index, rataId) => {
    const selected = rate.find(r => r.id === rataId);
    setMatches(prev => prev.map((m, i) => i === index ? {
      ...m,
      rata_id: rataId || null,
      rata: selected || null,
      stato_match: rataId ? 'da_revisionare' : 'non_abbinato',
    } : m));
  };

  return (
    <div className="space-y-6" data-testid="incassi-page">
      <div>
        <h1 className="text-2xl font-bold font-heading">Incassi</h1>
        <p className="text-slate-500">Importa estratti conto CSV/XLSX e abbina i movimenti alle rate</p>
      </div>

      <Card>
        <CardContent className="pt-6 flex flex-col md:flex-row gap-3 md:items-end">
          <div className="md:w-96">
            <Label>File movimenti</Label>
            <Input type="file" accept=".csv,.xlsx,.xlsm" onChange={e => setFile(e.target.files?.[0])} />
          </div>
          <Button onClick={preview} disabled={loading}>
            <Upload className="w-4 h-4 mr-2" /> Analizza
          </Button>
        </CardContent>
      </Card>

      {logs.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <h2 className="font-semibold mb-3">Ultimi import</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm">
              {logs.slice(0, 6).map(log => (
                <div key={log.id} className="border rounded p-3">
                  <div className="font-medium truncate">{log.filename}</div>
                  <div className="text-slate-500">{log.created_at?.substring(0, 16).replace('T', ' ')}</div>
                  <div className="mt-1">
                    {log.matched_count}/{log.total_movimenti} match
                    {log.duplicate_count > 0 && <Badge variant="outline" className="ml-2">{log.duplicate_count} duplicati</Badge>}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Movimento</TableHead>
                <TableHead>Importo</TableHead>
                <TableHead>Match</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Motivi</TableHead>
                <TableHead className="text-right">Azioni</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {matches.map((m, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <div className="font-medium">{m.movimento.causale}</div>
                    <div className="text-xs text-slate-500">{m.movimento.data_movimento || '-'} {m.movimento.ordinante || ''}</div>
                  </TableCell>
                  <TableCell className="font-mono">€ {m.movimento.importo?.toLocaleString('it-IT')}</TableCell>
                  <TableCell>
                    <Badge variant={badgeVariant[m.stato_match]}>{m.stato_match.replace('_', ' ')}</Badge>
                    {m.duplicato && <Badge variant="outline" className="ml-1">Duplicato</Badge>}
                    <select
                      className="mt-2 w-full h-9 rounded-md border border-input bg-background px-2 text-xs"
                      value={m.rata_id || ''}
                      onChange={e => changeRata(i, e.target.value)}
                    >
                      <option value="">Nessun abbinamento</option>
                      {rate.map(r => (
                        <option key={r.id} value={r.id}>
                          {r.contratto_codice || r.contratto_id?.slice(0, 8)} - {r.affittuario_nome || 'N/D'} - {r.periodo} - € {r.importo}
                        </option>
                      ))}
                    </select>
                  </TableCell>
                  <TableCell>{m.score}/100</TableCell>
                  <TableCell className="text-sm text-slate-500">{(m.motivi || []).join(', ') || '-'}</TableCell>
                  <TableCell className="text-right">
                    {m.rata_id && (
                      <Button size="sm" onClick={() => conferma(m)} disabled={m.duplicato}>
                        <CheckCircle className="w-4 h-4 mr-1" /> Conferma
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
