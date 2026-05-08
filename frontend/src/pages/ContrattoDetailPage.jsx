import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useFetch, useApi } from '../hooks';
import api from '../stores';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import {
  Tabs, TabsContent, TabsList, TabsTrigger
} from '../components/ui/tabs';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger
} from '../components/ui/alert-dialog';
import { toast } from 'sonner';
import {
  ArrowLeft, FileText, Download, Building2, User, Calendar, Euro,
  ClipboardList, FileCheck, Wallet, XCircle, Plus, ExternalLink, Loader2
} from 'lucide-react';

const statoBadge = {
  attivo: 'bg-emerald-100 text-emerald-700',
  chiuso: 'bg-slate-200 text-slate-700',
  scaduto: 'bg-amber-100 text-amber-700',
};
const statoRataBadge = {
  incassato: 'bg-emerald-100 text-emerald-700',
  da_incassare: 'bg-blue-100 text-blue-700',
  in_ritardo: 'bg-red-100 text-red-700',
};

export default function ContrattoDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: contratto, loading, refetch } = useFetch(`/contratti/${id}`);
  const { data: rate } = useFetch(`/contratti/${id}/rate`);
  const { data: verbali } = useFetch(`/verbali?contratto_id=${id}`);
  const { request } = useApi();
  const [downloading, setDownloading] = useState(false);
  const [closing, setClosing] = useState(false);

  const handleDownloadPdf = async () => {
    setDownloading(true);
    try {
      const res = await api.get(`/reports/contratto/${id}/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `contratto_${contratto.codice_contratto}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('PDF scaricato');
    } catch (err) {
      toast.error('Errore download PDF: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDownloading(false);
    }
  };

  const handleClose = async () => {
    setClosing(true);
    try {
      await request('POST', `/contratti/${id}/chiudi`);
      toast.success('Contratto chiuso');
      refetch();
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setClosing(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 max-w-5xl">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[200px] w-full" />
        <Skeleton className="h-[300px] w-full" />
      </div>
    );
  }

  if (!contratto) {
    return <p className="text-red-500 p-8">Contratto non trovato</p>;
  }

  const totRate = rate?.length || 0;
  const incassate = rate?.filter(r => r.stato === 'incassato').length || 0;
  const ritardo = rate?.filter(r => r.stato === 'in_ritardo').length || 0;

  return (
    <div className="space-y-6 max-w-6xl" data-testid="contratto-detail-page">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold font-heading">
              Contratto {contratto.codice_contratto}
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className={`capitalize ${statoBadge[contratto.stato] || ''}`}>
                {contratto.stato}
              </Badge>
              <span className="text-sm text-slate-500">
                {contratto.tipo_contratto}
              </span>
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={handleDownloadPdf} disabled={downloading} data-testid="btn-download-pdf">
            {downloading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
            Scarica PDF
          </Button>
          <Link to={`/verbali/nuovo/${id}`}>
            <Button data-testid="btn-new-verbale">
              <FileCheck className="w-4 h-4 mr-2" /> Nuovo verbale
            </Button>
          </Link>
          {contratto.stato === 'attivo' && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" data-testid="btn-close-contratto">
                  <XCircle className="w-4 h-4 mr-2" /> Chiudi
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Chiudere il contratto?</AlertDialogTitle>
                  <AlertDialogDescription>
                    L'unità verrà liberata e il contratto marcato come chiuso. L'azione è reversibile solo manualmente.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Annulla</AlertDialogCancel>
                  <AlertDialogAction onClick={handleClose} disabled={closing}>
                    {closing && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    Chiudi contratto
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiBox icon={Euro} label="Canone mensile" value={`€ ${(contratto.canone_importo || 0).toLocaleString('it-IT', {minimumFractionDigits: 2})}`} />
        <KpiBox icon={Calendar} label="Durata" value={`${contratto.durata_mesi} mesi`} />
        <KpiBox icon={Wallet} label="Rate incassate" value={`${incassate}/${totRate}`} accent="emerald" />
        <KpiBox icon={ClipboardList} label="Rate in ritardo" value={ritardo} accent={ritardo > 0 ? 'red' : 'slate'} />
      </div>

      <Tabs defaultValue="anagrafica">
        <TabsList>
          <TabsTrigger value="anagrafica" data-testid="tab-anagrafica">Anagrafica</TabsTrigger>
          <TabsTrigger value="rate" data-testid="tab-rate">Rate ({totRate})</TabsTrigger>
          <TabsTrigger value="verbali" data-testid="tab-verbali">Verbali ({verbali?.length || 0})</TabsTrigger>
        </TabsList>

        <TabsContent value="anagrafica">
          <Card>
            <CardHeader>
              <CardTitle>Dati Contratto</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Section title="Immobile" icon={Building2}>
                <Row label="Titolo" value={contratto.immobile_titolo || '—'} />
                <Row label="Unità" value={contratto.unita_codice || '—'} />
              </Section>
              <Section title="Soggetti" icon={User}>
                <Row label="Locatore" value={contratto.locatore_nome || '—'} />
                <Row label="Affittuario" value={contratto.affittuario_nome || '—'} />
              </Section>
              <Section title="Date" icon={Calendar}>
                <Row label="Firma" value={contratto.data_firma || '—'} />
                <Row label="Inizio" value={contratto.data_inizio || '—'} />
                <Row label="Scadenza" value={contratto.data_scadenza || '—'} />
              </Section>
              <Section title="Economia" icon={Euro}>
                <Row label="Canone" value={`€ ${(contratto.canone_importo || 0).toLocaleString('it-IT', {minimumFractionDigits: 2})}`} />
                <Row label="Periodicità" value={contratto.periodicita} />
                <Row label="Giorno scadenza rate" value={contratto.giorno_scadenza} />
                <Row label="Deposito" value={contratto.deposito_importo ? `€ ${contratto.deposito_importo.toLocaleString('it-IT')}` : '—'} />
              </Section>
              {contratto.note && (
                <div className="md:col-span-2">
                  <p className="text-sm font-medium text-slate-500 mb-1">Note</p>
                  <p className="text-sm bg-slate-50 dark:bg-slate-900 p-3 rounded">{contratto.note}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rate">
          <Card>
            <CardContent className="p-0">
              {!rate || rate.length === 0 ? (
                <div className="p-12 text-center text-slate-500">Nessuna rata generata</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Periodo</TableHead>
                      <TableHead>Scadenza</TableHead>
                      <TableHead className="text-right">Importo</TableHead>
                      <TableHead>Stato</TableHead>
                      <TableHead>Data Incasso</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rate.map(r => (
                      <TableRow key={r.id} data-testid={`rata-row-${r.id}`}>
                        <TableCell className="font-mono">{r.periodo}</TableCell>
                        <TableCell>{r.data_scadenza || '—'}</TableCell>
                        <TableCell className="text-right">€ {r.importo.toLocaleString('it-IT', {minimumFractionDigits: 2})}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={`capitalize ${statoRataBadge[r.stato] || ''}`}>
                            {r.stato.replace('_', ' ')}
                          </Badge>
                        </TableCell>
                        <TableCell>{r.data_incasso || '—'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="verbali">
          <Card>
            <CardContent className="p-0">
              {!verbali || verbali.length === 0 ? (
                <div className="p-12 text-center">
                  <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-500">Nessun verbale presente</p>
                  <Link to={`/verbali/nuovo/${id}`}>
                    <Button className="mt-4" size="sm">
                      <Plus className="w-4 h-4 mr-2" /> Crea primo verbale
                    </Button>
                  </Link>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Data</TableHead>
                      <TableHead>Ambienti</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {verbali.map(v => (
                      <TableRow key={v.id}>
                        <TableCell><Badge variant="outline" className="capitalize">{v.tipo}</Badge></TableCell>
                        <TableCell>{v.data}</TableCell>
                        <TableCell>{v.checklist?.length || 0}</TableCell>
                        <TableCell>
                          <Link to="/verbali">
                            <Button variant="ghost" size="sm"><ExternalLink className="w-4 h-4" /></Button>
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function KpiBox({ icon: Icon, label, value, accent = 'slate' }) {
  const accentClass = {
    emerald: 'text-emerald-600',
    red: 'text-red-600',
    slate: 'text-slate-900 dark:text-slate-100',
  }[accent];
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-slate-500">{label}</p>
            <p className={`text-xl font-bold mt-1 ${accentClass}`}>{value}</p>
          </div>
          <Icon className={`w-5 h-5 ${accentClass}`} />
        </div>
      </CardContent>
    </Card>
  );
}

function Section({ title, icon: Icon, children }) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2">
        <Icon className="w-4 h-4" /> {title}
      </h3>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between text-sm py-1 border-b border-slate-100 dark:border-slate-800">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-right">{value}</span>
    </div>
  );
}
