import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useFetch, useApi } from '../hooks';
import {
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
} from '../components/ui/alert-dialog';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
  ArrowLeft, 
  Edit, 
  Download, 
  Plus,
  Building2,
  Home,
  MapPin,
  FileText,
  Euro,
  Calendar,
  Trash2,
  ExternalLink
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import { useAuthStore } from '../stores';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet marker
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

export default function ImmobileDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { request } = useApi();
  const { user } = useAuthStore();
  const [downloading, setDownloading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  
  const { data: immobile, loading } = useFetch(`/immobili/${id}`);
  const { data: unita, refetch: refetchUnita } = useFetch(`/unita?immobile_id=${id}`);
  const { data: spese } = useFetch(`/spese?immobile_id=${id}&limit=20`);
  const { data: documenti } = useFetch(`/documenti?livello=immobile&ref_id=${id}`);

  const handleDownloadPDF = async () => {
    setDownloading(true);
    try {
      const response = await request('GET', `/reports/immobile/${id}/pdf`, null, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `immobile_${immobile?.codice}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('PDF scaricato');
    } catch (error) {
      toast.error('Errore nel download del PDF');
    } finally {
      setDownloading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Eliminare l'immobile "${immobile?.titolo}"? L'operazione è irreversibile.`)) return;
    setDeleting(true);
    try {
      await request('DELETE', `/immobili/${id}`);
      toast.success('Immobile eliminato');
      navigate('/immobili');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore durante l\'eliminazione');
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  if (!immobile) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">Immobile non trovato</p>
        <Button onClick={() => navigate('/immobili')} className="mt-4">
          Torna agli Immobili
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="immobile-detail">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/immobili')}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold font-heading">{immobile.titolo}</h1>
            <p className="text-slate-500">{immobile.codice} • {immobile.indirizzo}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleDownloadPDF} disabled={downloading}>
            <Download className="w-4 h-4 mr-2" />
            {downloading ? 'Scaricamento...' : 'Scarica PDF'}
          </Button>
          <Button onClick={() => navigate(`/immobili/${id}/modifica`)}>
            <Edit className="w-4 h-4 mr-2" />
            Modifica
          </Button>
          {user?.ruolo === 'supervisore' && (
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              <Trash2 className="w-4 h-4 mr-2" />
              {deleting ? 'Eliminazione...' : 'Elimina'}
            </Button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-slate-100 rounded-lg">
                <Home className="w-5 h-5 text-slate-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Unità</p>
                <p className="text-xl font-bold">{immobile.unita_count || unita?.length || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-100 rounded-lg">
                <FileText className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Contratti Attivi</p>
                <p className="text-xl font-bold">{immobile.contratti_attivi || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Euro className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Rendita</p>
                <p className="text-xl font-bold">€ {(immobile.rendita || 0).toLocaleString('it-IT')}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 rounded-lg">
                <MapPin className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Coordinate</p>
                <p className="text-sm font-medium">
                  {immobile.lat && immobile.lon 
                    ? `${immobile.lat.toFixed(4)}, ${immobile.lon.toFixed(4)}`
                    : 'N/A'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="info">
        <TabsList>
          <TabsTrigger value="info">Informazioni</TabsTrigger>
          <TabsTrigger value="unita">Unità ({unita?.length || 0})</TabsTrigger>
          <TabsTrigger value="spese">Spese</TabsTrigger>
          <TabsTrigger value="documenti">Documenti</TabsTrigger>
          <TabsTrigger value="mappa">Mappa</TabsTrigger>
        </TabsList>

        <TabsContent value="info" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Dati Generali</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-slate-500">Codice</p>
                    <p className="font-medium font-mono">{immobile.codice}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Titolo</p>
                    <p className="font-medium">{immobile.titolo}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm text-slate-500">Indirizzo</p>
                    <p className="font-medium">{immobile.indirizzo}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Dati Catastali</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-slate-500">Comune</p>
                    <p className="font-medium">{immobile.catastale_comune || 'N/D'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Foglio</p>
                    <p className="font-medium">{immobile.foglio || 'N/D'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Particella</p>
                    <p className="font-medium">{immobile.particella || 'N/D'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Subalterno</p>
                    <p className="font-medium">{immobile.subalterno || 'N/D'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Categoria</p>
                    <p className="font-medium">{immobile.categoria || 'N/D'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Rendita</p>
                    <p className="font-medium">€ {(immobile.rendita || 0).toLocaleString('it-IT')}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {immobile.note && (
              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle>Note</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-slate-600">{immobile.note}</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="unita" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Unità Immobiliari</CardTitle>
              <Link to={`/unita/nuovo?immobile_id=${id}`}>
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  Nuova Unità
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {unita?.length === 0 ? (
                <p className="text-center text-slate-500 py-8">Nessuna unità registrata</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {unita?.map(u => (
                    <Card key={u.id} className="hover:shadow-md transition-shadow">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-semibold">{u.codice_unita}</p>
                            <p className="text-sm text-slate-500 capitalize">
                              {u.tipo_immobile?.replace('_', ' ')}
                            </p>
                            <p className="text-sm text-slate-500">{u.mq} mq</p>
                          </div>
                          <Badge className={cn(
                            u.stato === 'locata' && "bg-emerald-100 text-emerald-700",
                            u.stato === 'libera' && "bg-slate-100 text-slate-700",
                            u.stato === 'in_manutenzione' && "bg-amber-100 text-amber-700"
                          )}>
                            {u.stato}
                          </Badge>
                        </div>
                        {u.affittuario_nome && (
                          <p className="text-sm mt-2">
                            Affittuario: <span className="font-medium">{u.affittuario_nome}</span>
                          </p>
                        )}
                        <div className="mt-3 flex items-center justify-end gap-2">
                          {user?.ruolo === 'supervisore' && (
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700">
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Elimina unità?</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    L'unità <strong>{u.codice_unita}</strong> verrà eliminata definitivamente.
                                    Questa azione non può essere annullata.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Annulla</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={async () => {
                                      try {
                                        await request('DELETE', `/unita/${u.id}`);
                                        toast.success('Unità eliminata');
                                        refetchUnita();
                                      } catch (err) {
                                        toast.error(err.response?.data?.detail || 'Errore');
                                      }
                                    }}
                                  >
                                    Elimina
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="spese" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Spese</CardTitle>
              <Link to={`/spese/nuovo?immobile_id=${id}`}>
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  Nuova Spesa
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {spese?.length === 0 ? (
                <p className="text-center text-slate-500 py-8">Nessuna spesa registrata</p>
              ) : (
                <div className="space-y-3">
                  {spese?.map(s => (
                    <div key={s.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                      <div>
                        <p className="font-medium capitalize">{s.categoria?.replace('_', ' ')}</p>
                        <p className="text-sm text-slate-500">{s.data} • {s.fornitore || 'N/D'}</p>
                      </div>
                      <p className="font-mono font-semibold">€ {s.importo?.toLocaleString('it-IT')}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="documenti" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Documenti</CardTitle>
              <Link to={`/documenti/upload?livello=immobile&ref_id=${id}`}>
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  Carica Documento
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {documenti?.length === 0 ? (
                <p className="text-center text-slate-500 py-8">Nessun documento caricato</p>
              ) : (
                <div className="space-y-3">
                  {documenti?.map(d => (
                    <div key={d.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-slate-400" />
                        <div>
                          <p className="font-medium">{d.filename}</p>
                          <p className="text-sm text-slate-500">{d.tipo} • {d.uploaded_at?.split('T')[0]}</p>
                        </div>
                      </div>
                      {d.expiry_date && (
                        <Badge variant="outline">Scade: {d.expiry_date}</Badge>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="mappa" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Posizione</CardTitle>
            </CardHeader>
            <CardContent>
              {immobile.lat && immobile.lon ? (
                <div className="h-[400px] rounded-lg overflow-hidden">
                  <MapContainer
                    center={[immobile.lat, immobile.lon]}
                    zoom={15}
                    className="h-full w-full"
                  >
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <Marker position={[immobile.lat, immobile.lon]}>
                      <Popup>
                        <strong>{immobile.titolo}</strong>
                        <br />
                        {immobile.indirizzo}
                      </Popup>
                    </Marker>
                  </MapContainer>
                </div>
              ) : (
                <div className="h-[400px] flex items-center justify-center bg-slate-100 dark:bg-slate-800 rounded-lg">
                  <div className="text-center">
                    <MapPin className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                    <p className="text-slate-500">Coordinate non disponibili</p>
                    <Button variant="outline" className="mt-4" onClick={() => navigate(`/immobili/${id}/modifica`)}>
                      Aggiungi Coordinate
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
