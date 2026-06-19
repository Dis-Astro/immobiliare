import React, { useState } from 'react';
import { useFetch, useApi } from '../hooks';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Skeleton } from '../components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  AlertTriangle,
  Plus,
  Search,
  AlertCircle,
  Info,
  MinusCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

const gravitaColors = {
  bassa: 'bg-yellow-100 text-yellow-700',
  media: 'bg-orange-100 text-orange-700',
  alta: 'bg-red-100 text-red-700',
};

const tipoLabels = {
  lamentela_vicinato: 'Lamentela Vicinato',
  danno: 'Danno',
  contestazione: 'Contestazione',
  diffida: 'Diffida',
  incuria: 'Incuria',
  altro: 'Altro',
};

export default function EventiCriticiPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroGravita, setFiltroGravita] = useState('all');
  const [open, setOpen] = useState(false);
  const [formData, setFormData] = useState({
    affittuario_id: '',
    tipo: '',
    gravita: '',
    descrizione_breve: '',
  });
  const { request, loading: saving } = useApi();
  const { data: eventi, loading, refetch } = useFetch('/valutazioni/eventi-critici');
  const { data: soggetti } = useFetch('/soggetti');

  const filtered = eventi?.filter(e => {
    if (filtroGravita !== 'all' && e.gravita !== filtroGravita) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      return (
        (e.affittuario_nome || '').toLowerCase().includes(q) ||
        (e.descrizione_breve || '').toLowerCase().includes(q)
      );
    }
    return true;
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.affittuario_id || !formData.tipo || !formData.gravita || !formData.descrizione_breve) {
      toast.error('Compila tutti i campi obbligatori');
      return;
    }
    try {
      await request('POST', '/valutazioni/eventi-critici', {
        ...formData,
        data_evento: new Date().toISOString(),
      });
      toast.success('Evento critico registrato');
      setOpen(false);
      setFormData({ affittuario_id: '', tipo: '', gravita: '', descrizione_breve: '' });
      refetch();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Eventi Critici</h1>
          <p className="text-slate-500">Registra e monitora eventi critici sugli affittuari</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Nuovo Evento
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Registra Evento Critico</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label>Affittuario *</Label>
                <Select
                  value={formData.affittuario_id}
                  onValueChange={(v) => setFormData(p => ({ ...p, affittuario_id: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleziona affittuario" />
                  </SelectTrigger>
                  <SelectContent>
                    {soggetti?.map(s => (
                      <SelectItem key={s.id} value={s.id}>{s.nome}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Tipo *</Label>
                  <Select
                    value={formData.tipo}
                    onValueChange={(v) => setFormData(p => ({ ...p, tipo: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleziona tipo" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(tipoLabels).map(([k, v]) => (
                        <SelectItem key={k} value={k}>{v}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Gravità *</Label>
                  <Select
                    value={formData.gravita}
                    onValueChange={(v) => setFormData(p => ({ ...p, gravita: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleziona gravità" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="bassa">Bassa</SelectItem>
                      <SelectItem value="media">Media</SelectItem>
                      <SelectItem value="alta">Alta</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Descrizione *</Label>
                <Textarea
                  value={formData.descrizione_breve}
                  onChange={(e) => setFormData(p => ({ ...p, descrizione_breve: e.target.value }))}
                  placeholder="Descrivi brevemente l'evento..."
                  maxLength={500}
                  rows={3}
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                  Annulla
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving ? 'Salvataggio...' : 'Registra'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Cerca per nome affittuario o descrizione..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={filtroGravita} onValueChange={setFiltroGravita}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Tutte" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tutte le gravità</SelectItem>
                <SelectItem value="bassa">Bassa</SelectItem>
                <SelectItem value="media">Media</SelectItem>
                <SelectItem value="alta">Alta</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : filtered?.length === 0 ? (
            <div className="p-12 text-center">
              <AlertTriangle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">Nessun evento critico registrato</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Affittuario</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Gravità</TableHead>
                  <TableHead>Descrizione</TableHead>
                  <TableHead>Data</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered?.map((e) => (
                  <TableRow key={e.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        {e.gravita === 'alta' ? (
                          <AlertCircle className="w-4 h-4 text-red-500" />
                        ) : e.gravita === 'media' ? (
                          <Info className="w-4 h-4 text-orange-500" />
                        ) : (
                          <MinusCircle className="w-4 h-4 text-yellow-500" />
                        )}
                        {e.affittuario_nome || 'N/A'}
                      </div>
                    </TableCell>
                    <TableCell>{tipoLabels[e.tipo] || e.tipo}</TableCell>
                    <TableCell>
                      <Badge className={cn("capitalize", gravitaColors[e.gravita])}>
                        {e.gravita}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-slate-500">
                      {e.descrizione_breve}
                    </TableCell>
                    <TableCell className="text-sm text-slate-500">
                      {new Date(e.data_evento).toLocaleDateString('it-IT')}
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
