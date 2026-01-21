import React, { useState } from 'react';
import { useFetch, useApi } from '../../hooks';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Skeleton } from '../ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { 
  CreditCard,
  CheckCircle,
  Clock,
  AlertTriangle,
  Euro,
  Calendar
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';

const statoColors = {
  da_incassare: 'bg-slate-100 text-slate-700',
  incassato: 'bg-emerald-100 text-emerald-700',
  in_ritardo: 'bg-red-100 text-red-700',
  parziale: 'bg-amber-100 text-amber-700',
};

export default function PagamentiPage() {
  const [stato, setStato] = useState('');
  const [periodo, setPeriodo] = useState('');
  const { request } = useApi();
  
  const queryParams = new URLSearchParams();
  if (stato) queryParams.set('stato', stato);
  if (periodo) queryParams.set('periodo_da', periodo);
  
  const { data: rate, loading, refetch } = useFetch(`/rate?${queryParams.toString()}`);
  const { data: stats } = useFetch('/rate/stats');

  const handleIncassa = async (rataId) => {
    try {
      await request('POST', `/rate/${rataId}/incassa`);
      toast.success('Rata segnata come incassata');
      refetch();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore');
    }
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

  return (
    <div className="space-y-6" data-testid="pagamenti-page">
      <div>
        <h1 className="text-2xl font-bold font-heading">Pagamenti</h1>
        <p className="text-slate-500">Gestisci rate e incassi</p>
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
                <SelectItem value="">Tutti gli stati</SelectItem>
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
                <SelectItem value="">Tutti i periodi</SelectItem>
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
