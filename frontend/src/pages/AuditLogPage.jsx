import React, { useState, useEffect } from 'react';
import api from '../stores';
import { useAuthStore } from '../stores';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription
} from '../components/ui/dialog';
import {
  ScrollText, ChevronLeft, ChevronRight, Eye, Lock, RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';

const TABELLE = [
  'immobili', 'unita', 'soggetti', 'contratti', 'rate', 'verbali',
  'documenti', 'interventi', 'ape', 'spese', 'eventi_critici', 'users'
];
const AZIONI = ['create', 'update', 'delete'];

const azioneColors = {
  create: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  update: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  delete: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

export default function AuditLogPage() {
  const { user } = useAuthStore();
  const isSupervisore = user?.ruolo === 'supervisore';
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tabella, setTabella] = useState('');
  const [azione, setAzione] = useState('');
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState(null);
  const limit = 25;

  const fetchLogs = async () => {
    if (!isSupervisore) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('skip', page * limit);
      params.set('limit', limit);
      if (tabella) params.set('tabella', tabella);
      if (azione) params.set('azione', azione);

      const [logsRes, countRes] = await Promise.all([
        api.get(`/audit?${params.toString()}`),
        api.get(`/audit/count${tabella ? `?tabella=${tabella}` : ''}`)
      ]);
      setLogs(logsRes.data);
      setTotal(countRes.data.count);
    } catch (err) {
      toast.error('Errore caricamento log');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLogs(); }, [page, tabella, azione]);

  if (!isSupervisore) {
    return (
      <div className="flex items-center justify-center h-[60vh]" data-testid="audit-forbidden">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center space-y-3">
            <Lock className="w-12 h-12 text-amber-500 mx-auto" />
            <h2 className="text-xl font-bold">Accesso negato</h2>
            <p className="text-slate-500">Solo i supervisori possono visualizzare l'audit log.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6" data-testid="audit-log-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-heading flex items-center gap-2">
            <ScrollText className="w-8 h-8 text-slate-700" /> Audit Log
          </h1>
          <p className="text-slate-500">Cronologia di tutte le modifiche al sistema</p>
        </div>
        <Button variant="outline" onClick={fetchLogs} data-testid="btn-refresh">
          <RefreshCw className="w-4 h-4 mr-2" /> Aggiorna
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filtri</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-3">
            <Select value={tabella || 'all'} onValueChange={v => { setTabella(v === 'all' ? '' : v); setPage(0); }}>
              <SelectTrigger className="w-[200px]" data-testid="select-tabella"><SelectValue placeholder="Tutte le tabelle" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tutte le tabelle</SelectItem>
                {TABELLE.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={azione || 'all'} onValueChange={v => { setAzione(v === 'all' ? '' : v); setPage(0); }}>
              <SelectTrigger className="w-[180px]" data-testid="select-azione"><SelectValue placeholder="Tutte le azioni" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tutte le azioni</SelectItem>
                {AZIONI.map(a => <SelectItem key={a} value={a} className="capitalize">{a}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-3">
              {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : logs.length === 0 ? (
            <div className="p-12 text-center">
              <ScrollText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">Nessun log trovato</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Utente</TableHead>
                  <TableHead>Azione</TableHead>
                  <TableHead>Tabella</TableHead>
                  <TableHead>Record ID</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map(log => (
                  <TableRow key={log.id} data-testid={`log-row-${log.id}`}>
                    <TableCell className="font-mono text-xs whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString('it-IT')}
                    </TableCell>
                    <TableCell>{log.user_nome || <span className="text-slate-400">—</span>}</TableCell>
                    <TableCell>
                      <Badge className={`capitalize ${azioneColors[log.azione] || ''}`} variant="outline">
                        {log.azione}
                      </Badge>
                    </TableCell>
                    <TableCell><code className="text-xs">{log.tabella}</code></TableCell>
                    <TableCell className="font-mono text-xs text-slate-500 max-w-[200px] truncate">{log.record_id}</TableCell>
                    <TableCell>
                      <Button variant="ghost" size="icon" onClick={() => setSelected(log)} data-testid={`btn-view-log-${log.id}`}>
                        <Eye className="w-4 h-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-500">
            Pagina {page + 1} di {totalPages} ({total} totali)
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline" size="sm"
              disabled={page === 0}
              onClick={() => setPage(p => Math.max(0, p - 1))}
              data-testid="btn-prev"
            >
              <ChevronLeft className="w-4 h-4" /> Precedente
            </Button>
            <Button
              variant="outline" size="sm"
              disabled={page >= totalPages - 1}
              onClick={() => setPage(p => p + 1)}
              data-testid="btn-next"
            >
              Successiva <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Dettaglio Log</DialogTitle>
            <DialogDescription>Informazioni complete sull'evento di audit, inclusi i valori prima e dopo la modifica.</DialogDescription>
          </DialogHeader>
          {selected && (
            <div className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <div><span className="text-slate-500">Tabella:</span> <code>{selected.tabella}</code></div>
                <div><span className="text-slate-500">Azione:</span> <Badge className={`capitalize ${azioneColors[selected.azione]}`} variant="outline">{selected.azione}</Badge></div>
                <div><span className="text-slate-500">Record ID:</span> <code className="text-xs">{selected.record_id}</code></div>
                <div><span className="text-slate-500">Utente:</span> {selected.user_nome || '—'}</div>
                <div className="col-span-2"><span className="text-slate-500">Timestamp:</span> {new Date(selected.timestamp).toLocaleString('it-IT')}</div>
              </div>
              {selected.old_values && (
                <div>
                  <p className="font-medium mb-1">Valori precedenti</p>
                  <pre className="bg-slate-100 dark:bg-slate-900 p-3 rounded text-xs overflow-x-auto">
                    {JSON.stringify(selected.old_values, null, 2)}
                  </pre>
                </div>
              )}
              {selected.new_values && (
                <div>
                  <p className="font-medium mb-1">Valori nuovi</p>
                  <pre className="bg-slate-100 dark:bg-slate-900 p-3 rounded text-xs overflow-x-auto">
                    {JSON.stringify(selected.new_values, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
