import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import api from '../stores';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { ClipboardList, Plus, FileDown, ArrowLeftRight, Eye } from 'lucide-react';

const TIPO_BADGE = {
  consegna: { label: 'Consegna', cls: 'bg-emerald-500' },
  riconsegna: { label: 'Riconsegna', cls: 'bg-blue-500' }
};

export default function VerbaliListPage() {
  const navigate = useNavigate();
  const [verbali, setVerbali] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tipoFilter, setTipoFilter] = useState('all');

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api.get('/verbali');
      setVerbali(res.data);
    } catch (err) {
      toast.error('Errore caricamento: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const filtered = tipoFilter === 'all' ? verbali : verbali.filter(v => v.tipo === tipoFilter);

  const downloadPdf = async (id, codice) => {
    try {
      const res = await api.get(`/reports/verbale/${id}/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `verbale_${codice}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      toast.error('Errore download PDF: ' + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="space-y-6" data-testid="verbali-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-heading">Verbali</h1>
          <p className="text-slate-500">Verbali di consegna e riconsegna immobili</p>
        </div>
        <Button onClick={() => navigate('/verbali/nuovo')} data-testid="btn-new-verbale">
          <Plus className="w-4 h-4 mr-2" /> Nuovo verbale
        </Button>
      </div>

      <div className="flex gap-2 items-center">
        <Select value={tipoFilter} onValueChange={setTipoFilter}>
          <SelectTrigger className="w-48" data-testid="filter-tipo"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tutti i tipi</SelectItem>
            <SelectItem value="consegna">Solo consegna</SelectItem>
            <SelectItem value="riconsegna">Solo riconsegna</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-sm text-slate-500">{filtered.length} verbali</span>
      </div>

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-center text-slate-500 py-8">Caricamento...</p>
          ) : filtered.length === 0 ? (
            <div className="text-center py-12">
              <ClipboardList className="w-12 h-12 mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500">Nessun verbale registrato</p>
              <Button variant="link" onClick={() => navigate('/verbali/nuovo')}>Crea il primo verbale</Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Contratto</TableHead>
                  <TableHead>Affittuario</TableHead>
                  <TableHead>Unità</TableHead>
                  <TableHead>Ambienti</TableHead>
                  <TableHead className="text-right">Azioni</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map(v => {
                  const tipoCfg = TIPO_BADGE[v.tipo] || { label: v.tipo, cls: 'bg-slate-500' };
                  return (
                    <TableRow key={v.id} data-testid={`verbale-row-${v.id}`}>
                      <TableCell>{v.data}</TableCell>
                      <TableCell><Badge className={`${tipoCfg.cls} text-white border-0`}>{tipoCfg.label}</Badge></TableCell>
                      <TableCell className="font-mono text-sm">{v.contratto_codice || v.contratto_id?.substring(0,8)}</TableCell>
                      <TableCell>{v.affittuario_nome || '-'}</TableCell>
                      <TableCell>{v.unita_codice || '-'}</TableCell>
                      <TableCell>
                        <span className="text-sm">{v.checklist?.length || 0} ambienti</span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon" onClick={() => downloadPdf(v.id, v.contratto_codice || v.id.substring(0,8))} data-testid={`btn-pdf-${v.id}`} title="Scarica PDF">
                            <FileDown className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
