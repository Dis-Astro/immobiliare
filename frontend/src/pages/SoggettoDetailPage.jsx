import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useFetch, useApi } from '../hooks';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
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
import {
  ArrowLeft, Edit, Trash2, User, Building, Mail, Phone, MapPin,
  CreditCard, Star, FileText, Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

export default function SoggettoDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: soggetto, loading } = useFetch(`/soggetti/${id}`);
  const { data: contratti } = useFetch(`/contratti?affittuario_id=${id}`);
  const { data: contrattiLocatore } = useFetch(`/contratti?locatore_id=${id}`);
  const { request } = useApi();
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await request('DELETE', `/soggetti/${id}`);
      toast.success('Soggetto eliminato');
      navigate('/soggetti');
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 max-w-5xl">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[300px] w-full" />
      </div>
    );
  }

  if (!soggetto) {
    return <p className="text-red-500 p-8">Soggetto non trovato</p>;
  }

  const renderRating = (rating) => {
    if (!rating) return <span className="text-slate-400">N/A</span>;
    return (
      <div className="flex items-center gap-1">
        {[...Array(5)].map((_, i) => (
          <Star key={i} className={cn("w-4 h-4", i < Math.round(rating) ? "fill-amber-400 text-amber-400" : "text-slate-300")} />
        ))}
        <span className="text-sm text-slate-500 ml-1">({rating.toFixed(1)})</span>
      </div>
    );
  };

  const tuttiContratti = [
    ...(contratti || []).map(c => ({ ...c, ruolo: 'affittuario' })),
    ...(contrattiLocatore || []).map(c => ({ ...c, ruolo: 'locatore' })),
  ];

  return (
    <div className="space-y-6 max-w-5xl" data-testid="soggetto-detail-page">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div className="flex items-center gap-3">
            <div className={cn(
              "w-12 h-12 rounded-full flex items-center justify-center",
              soggetto.tipo === 'azienda' ? "bg-blue-100" : "bg-slate-100"
            )}>
              {soggetto.tipo === 'azienda'
                ? <Building className="w-6 h-6 text-blue-600" />
                : <User className="w-6 h-6 text-slate-600" />}
            </div>
            <div>
              <h1 className="text-2xl font-bold font-heading">{soggetto.nome}</h1>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className="capitalize">{soggetto.tipo}</Badge>
                {renderRating(soggetto.rating_medio)}
              </div>
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          <Link to={`/soggetti/${id}/modifica`}>
            <Button variant="outline" data-testid="btn-edit-soggetto"><Edit className="w-4 h-4 mr-2" /> Modifica</Button>
          </Link>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" data-testid="btn-delete-soggetto"><Trash2 className="w-4 h-4 mr-2" /> Elimina</Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Eliminare il soggetto?</AlertDialogTitle>
                <AlertDialogDescription>
                  Non sarà possibile eliminare se il soggetto ha contratti attivi.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Annulla</AlertDialogCancel>
                <AlertDialogAction onClick={handleDelete} disabled={deleting}>
                  {deleting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Elimina
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <Tabs defaultValue="anagrafica">
        <TabsList>
          <TabsTrigger value="anagrafica" data-testid="tab-anagrafica">Anagrafica</TabsTrigger>
          <TabsTrigger value="contratti" data-testid="tab-contratti">
            Contratti ({tuttiContratti.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="anagrafica">
          <Card>
            <CardHeader><CardTitle>Dati identificativi</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoRow icon={CreditCard} label="Codice Fiscale" value={soggetto.cf} />
              <InfoRow icon={CreditCard} label="Partita IVA" value={soggetto.piva} />
              <InfoRow icon={Mail} label="Email" value={soggetto.email} link={soggetto.email && `mailto:${soggetto.email}`} />
              <InfoRow icon={Mail} label="PEC" value={soggetto.pec} link={soggetto.pec && `mailto:${soggetto.pec}`} />
              <InfoRow icon={Phone} label="Telefono" value={soggetto.telefono} link={soggetto.telefono && `tel:${soggetto.telefono}`} />
              <InfoRow icon={MapPin} label="Indirizzo" value={soggetto.indirizzo} />
              <InfoRow icon={CreditCard} label="IBAN" value={soggetto.iban} mono />
            </CardContent>
          </Card>

          {soggetto.note && (
            <Card className="mt-4">
              <CardHeader><CardTitle>Note</CardTitle></CardHeader>
              <CardContent>
                <p className="text-sm bg-slate-50 dark:bg-slate-900 p-3 rounded whitespace-pre-wrap">{soggetto.note}</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="contratti">
          <Card>
            <CardContent className="p-0">
              {tuttiContratti.length === 0 ? (
                <div className="p-12 text-center">
                  <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-500">Nessun contratto associato</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Codice</TableHead>
                      <TableHead>Ruolo</TableHead>
                      <TableHead>Immobile / Unità</TableHead>
                      <TableHead>Stato</TableHead>
                      <TableHead className="text-right">Canone</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tuttiContratti.map(c => (
                      <TableRow key={`${c.id}-${c.ruolo}`}>
                        <TableCell className="font-mono">{c.codice_contratto}</TableCell>
                        <TableCell><Badge variant="outline" className="capitalize">{c.ruolo}</Badge></TableCell>
                        <TableCell>{c.immobile_titolo || '—'} / {c.unita_codice || '—'}</TableCell>
                        <TableCell><Badge variant="outline" className="capitalize">{c.stato}</Badge></TableCell>
                        <TableCell className="text-right">€ {(c.canone_importo || 0).toLocaleString('it-IT', {minimumFractionDigits: 2})}</TableCell>
                        <TableCell>
                          <Link to={`/contratti/${c.id}`}>
                            <Button variant="ghost" size="sm">Apri</Button>
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

function InfoRow({ icon: Icon, label, value, link, mono }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-slate-100 dark:border-slate-800">
      <Icon className="w-4 h-4 text-slate-400 mt-0.5" />
      <div className="flex-1">
        <p className="text-xs text-slate-500">{label}</p>
        {value ? (
          link ? (
            <a href={link} className={`text-sm ${mono ? 'font-mono' : ''} text-blue-600 hover:underline`}>{value}</a>
          ) : (
            <p className={`text-sm ${mono ? 'font-mono' : ''}`}>{value}</p>
          )
        ) : (
          <p className="text-sm text-slate-400">—</p>
        )}
      </div>
    </div>
  );
}
