import React, { useState } from 'react';
import { useFetch, useApi } from '../hooks';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Skeleton } from '../components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { 
  CreditCard,
  CheckCircle,
  Clock,
  AlertTriangle,
  Euro,
  Calendar,
  Plus,
  Upload,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

const statoColors = {
  da_incassare: 'bg-slate-100 text-slate-700',
  incassato: 'bg-emerald-100 text-emerald-700',
  in_ritardo: 'bg-red-100 text-red-700',
  parziale: 'bg-amber-100 text-amber-700',
};

export default function PagamentiPage() {
  const [stato, setStato] = useState('all');
  const [periodo, setPeriodo] = useState('all');
  const [openNew, setOpenNew] = useState(false);
  const [openImport, setOpenImport] = useState(false);
  const [formData, setFormData] = useState({
    contratto_id: '',
    periodo: '',
    importo: '',
    data_scadenza: '',
    data_incasso: '',
    metodo: '',
    riferimento: '',
    note: '',
  });
  const [importFile, setImportFile] = useState(null);
  const { request } = useApi();
  
  const queryParams = new URLSearchParams();
  if (stato && stato !== 'all') queryParams.set('stato', stato);
  if (periodo && periodo !== 'all') queryParams.set('periodo_da', periodo);
  
  const { data: rate, loading, refetch } = useFetch(`/rate?${queryParams.toString()}`);
  const { data: stats } = useFetch('/rate/stats');
  const { data: contratti } = useFetch('/contratti');

  const handleIncassa = async (rataId) => {
    try {
      await request('POST', `/rate/${rataId}/incassa`);
      toast.success('Rata segnata come incassata');
      refetch();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore');
    }
  };

  const handleCreatePayment = async (e) => {
    e.preventDefault();
    if (!formData.contratto_id || !formData.periodo || !formData.importo) {
      toast.error('Compila i campi obbligatori');
      return;
    }
    try {
      await request('POST', '/rate', {
        contratto_id: formData.contratto_id,
        periodo: formData.periodo,
        importo: parseFloat(formData.importo),
        data_scadenza: formData.data_scadenza || null,
        data_incasso: formData.data_incasso || null,
        metodo: formData.metodo || null,
        riferimento: formData.riferimento || null,
        note: formData.note || null,
      });
      toast.success('Pagamento registrato');
      setOpenNew(false);
      setFormData({ contratto_id: '', periodo: '', importo: '', data_scadenza: '', data_incasso: '', metodo: '', riferimento: '', note: '' });
      refetch();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore');
    }
  };

  const handleImportCsv = async (e) => {
    e.preventDefault();
    if (!importFile) {
      toast.error('Seleziona un file CSV');
      return;
    }
    try {
      const form = new FormData();
      form.append('file', importFile);
      const res = await request('POST', '/rate/parse-bank-statement', form);
      toast.success(`Analizzati ${res.total} movimenti. ${res.rows.filter(r => r.affittuario_suggerito_id).length} associati.`);
      setOpenImport(false);
      setImportFile(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore importazione');
    }
  };

  const resetForm = () => {
    setFormData({ contratto_id: '', periodo: '', importo: '', data_scadenza: '', data_incasso: '', metodo: '', riferimento: '', note: '' });
  };

  // Generate last 12 months for filter
  const generateMonths = () => {
    const months = [];
    const now = new Date();
    for (let i = 0; i < 12; i++) {
      const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      const label = date.toLocaleDateString('it-IT', { month: 'long', year: 'numeric' });
      months.push({ value, label });
    }
    return months;
  };

  const currentMonth = new Date().toISOString().slice(0, 7);

  return (
    <div className="space-y-6" data-testid="pagamenti-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Pagamenti</h1>
          <p className="text-slate-500">Gestisci rate e incassi</p>
        </div>
        <div className="flex gap-2">
          {/* Importa CSV */}
          <Dialog open={openImport} onOpenChange={(v) => { setOpenImport(v); if (!v) setImportFile(null); }}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Upload className="w-4 h-4 mr-2" />
                Importa CSV
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Importa Estratto Conto</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleImportCsv} className="space-y-4">
                <div className="space-y-2">
                  <Label>File CSV</Label>
                  <Input
                    type="file"
                    accept=".csv"
                    onChange={(e) => setImportFile(e.target.files[0])}
                  />
                  <p className="text-xs text-slate-400">
                    Colonne attese: data, descrizione, importo
                  </p>
                </div>
                <div className="flex justify-end gap-3">
                  <Button type="button" variant="outline" onClick={() => setOpenImport(false)}>
                    Annulla
                  </Button>
                  <Button type="submit">Analizza</Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>

          {/* Nuovo Pagamento */}
          <Dialog open={openNew} onOpenChange={(v) => { setOpenNew(v); if (!v) resetForm(); }}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Nuovo Pagamento
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Registra Pagamento Manuale</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreatePayment} className="space-y-4">
                <div className="space-y-2">
                  <Label>Contratto *</Label>
                  <Select
                    value={formData.contratto_id}
                    onValueChange={(v) => setFormData(p => ({ ...p, contratto_id: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleziona contratto" />
                    </SelectTrigger>
                    <SelectContent>
                      {contratti?.map(c => (
                        <SelectItem key={c.id} value={c.id}>
                          {c.codice_contratto}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Periodo *</Label>
                    <Input
                      type="month"
                      value={formData.periodo}
                      onChange={(e) => setFormData(p => ({ ...p, periodo: e.target.value }))}
                      placeholder="YYYY-MM"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Importo *</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formData.importo}
                      onChange={(e) => setFormData(p => ({ ...p, importo: e.target.value }))}
                      placeholder="0.00"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Data Scadenza</Label>
                    <Input
                      type="date"
                      value={formData.data_scadenza}
                      onChange={(e) => setFormData(p => ({ ...p, data_scadenza: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Data Incasso</Label>
                    <Input
                      type="date"
                      value={formData.data_incasso}
                      onChange={(e) => setFormData(p => ({ ...p, data_incasso: e.target.value }))}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Metodo</Label>
                    <Select
                      value={formData.metodo}
                      onValueChange={(v) => setFormData(p => ({ ...p, metodo: v }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Seleziona" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="bonifico">Bonifico</SelectItem>
                        <SelectItem value="contanti">Contanti</SelectItem>
                        <SelectItem value="rid">RID</SelectItem>
                        <SelectItem value="altro">Altro</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Riferimento</Label>
                    <Input
                      value={formData.riferimento}
                      onChange={(e) => setFormData(p => ({ ...p, riferimento: e.target.value }))}
                      placeholder="es. causale"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <Button type="button" variant="outline" onClick={() => setOpenNew(false)}>
                    Annulla
                  </Button>
                  <Button type="submit">Registra</Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-slate-100 rounded-lg">
                <Euro className="w-5 h-5 text-slate-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Atteso Mese</p>
                <p className="text-xl font-bold">
                  € {(stats?.totale || 0).toLocaleString('it-IT')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-100 rounded-lg">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Incassato</p>
                <p className="text-xl font-bold text-emerald-600">
                  € {(stats?.incassato || 0).toLocaleString('it-IT')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Clock className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Da Incassare</p>
                <p className="text-xl font-bold text-amber-600">
                  € {(stats?.da_incassare || 0).toLocaleString('it-IT')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">In Ritardo</p>
                <p className="text-xl font-bold text-red-600">
                  € {(stats?.in_ritardo || 0).toLocaleString('it-IT')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <Select value={stato} onValueChange={setStato}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Tutti gli stati" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tutti gli stati</SelectItem>
                <SelectItem value="da_incassare">Da Incassare</SelectItem>
                <SelectItem value="incassato">Incassato</SelectItem>
                <SelectItem value="in_ritardo">In Ritardo</SelectItem>
                <SelectItem value="parziale">Parziale</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={periodo} onValueChange={setPeriodo}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Tutti i periodi" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tutti i periodi</SelectItem>
                {generateMonths().map(m => (
                  <SelectItem key={m.value} value={m.value} className="capitalize">
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : rate?.length === 0 ? (
            <div className="p-12 text-center">
              <CreditCard className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">Nessuna rata trovata</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Periodo</TableHead>
                  <TableHead>Contratto</TableHead>
                  <TableHead>Affittuario</TableHead>
                  <TableHead>Immobile</TableHead>
                  <TableHead className="text-right">Importo</TableHead>
                  <TableHead>Scadenza</TableHead>
                  <TableHead>Stato</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rate?.map((rata) => (
                  <TableRow key={rata.id}>
                    <TableCell className="font-mono font-medium">
                      {rata.periodo}
                    </TableCell>
                    <TableCell className="text-sm text-slate-500">
                      {rata.contratto_codice}
                    </TableCell>
                    <TableCell>{rata.affittuario_nome || 'N/A'}</TableCell>
                    <TableCell className="text-slate-500">
                      {rata.immobile_titolo}
                    </TableCell>
                    <TableCell className="text-right font-mono font-medium">
                      € {rata.importo?.toLocaleString('it-IT')}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-slate-400" />
                        {rata.data_scadenza}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={cn("capitalize", statoColors[rata.stato])}>
                        {rata.stato?.replace('_', ' ')}
                      </Badge>
                      {rata.giorni_ritardo > 0 && (
                        <span className="ml-2 text-xs text-red-500">
                          ({rata.giorni_ritardo}gg)
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      {rata.stato !== 'incassato' && (
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => handleIncassa(rata.id)}
                          className="gap-1"
                        >
                          <CheckCircle className="w-3 h-3" />
                          Incassa
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
