import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import api from '../stores';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Wrench, Plus, Pencil, Euro } from 'lucide-react';

const PRIORITA = { bassa: 'bg-slate-400', media: 'bg-blue-500', alta: 'bg-amber-500', urgente: 'bg-red-600' };
const STATO = {
  richiesto: 'bg-slate-400',
  pianificato: 'bg-blue-500',
  in_corso: 'bg-amber-500',
  completato: 'bg-emerald-500',
  annullato: 'bg-red-400'
};

export default function ManutenzionePage() {
  const [items, setItems] = useState([]);
  const [immobili, setImmobili] = useState([]);
  const [unita, setUnita] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stato, setStato] = useState('all');
  const [createOpen, setCreateOpen] = useState(false);
  const [statoEditOpen, setStatoEditOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [newStato, setNewStato] = useState('');

  const [form, setForm] = useState({
    immobile_id: '',
    unita_id: '',
    titolo: '',
    descrizione: '',
    priorita: 'media',
    stato: 'richiesto',
    costo_stimato: '',
    fornitore: '',
    data_pianificata: ''
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = stato !== 'all' ? `?stato=${stato}` : '';
      const [iRes, imRes, uRes] = await Promise.all([
        api.get('/interventi' + params),
        api.get('/immobili'),
        api.get('/unita')
      ]);
      setItems(iRes.data);
      setImmobili(imRes.data);
      setUnita(uRes.data);
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [stato]);

  const handleCreate = async () => {
    if (!form.immobile_id || !form.titolo) return toast.error('Compila immobile e titolo');
    try {
      await api.post('/interventi', {
        immobile_id: form.immobile_id,
        unita_id: form.unita_id || null,
        titolo: form.titolo,
        descrizione: form.descrizione || null,
        priorita: form.priorita,
        stato: form.stato,
        costo_stimato: form.costo_stimato ? parseFloat(form.costo_stimato) : null,
        fornitore: form.fornitore || null,
        data_pianificata: form.data_pianificata || null,
        data_richiesta: new Date().toISOString().split('T')[0]
      });
      toast.success('Intervento creato');
      setCreateOpen(false);
      setForm({ immobile_id: '', unita_id: '', titolo: '', descrizione: '', priorita: 'media', stato: 'richiesto', costo_stimato: '', fornitore: '', data_pianificata: '' });
      fetchData();
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleStatoChange = async () => {
    if (!newStato) return;
    try {
      await api.post(`/interventi/${editingItem.id}/stato`, null, { params: { nuovo_stato: newStato } });
      toast.success('Stato aggiornato');
      setStatoEditOpen(false);
      fetchData();
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  const filteredUnita = form.immobile_id ? unita.filter(u => u.immobile_id === form.immobile_id) : [];

  return (
    <div className="space-y-6" data-testid="manutenzione-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-heading">Manutenzione</h1>
          <p className="text-slate-500">Interventi di manutenzione su immobili e unità</p>
        </div>
        <Button onClick={() => setCreateOpen(true)} data-testid="btn-new-intervento">
          <Plus className="w-4 h-4 mr-2" /> Nuovo intervento
        </Button>
      </div>

      <div className="flex gap-2 items-center">
        <Select value={stato} onValueChange={setStato}>
          <SelectTrigger className="w-48" data-testid="filter-stato"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tutti gli stati</SelectItem>
            <SelectItem value="richiesto">Richiesti</SelectItem>
            <SelectItem value="pianificato">Pianificati</SelectItem>
            <SelectItem value="in_corso">In corso</SelectItem>
            <SelectItem value="completato">Completati</SelectItem>
            <SelectItem value="annullato">Annullati</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-sm text-slate-500">{items.length} interventi</span>
      </div>

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-center text-slate-500 py-8">Caricamento...</p>
          ) : items.length === 0 ? (
            <div className="text-center py-12">
              <Wrench className="w-12 h-12 mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500">Nessun intervento</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Titolo</TableHead>
                  <TableHead>Immobile/Unità</TableHead>
                  <TableHead>Priorità</TableHead>
                  <TableHead>Stato</TableHead>
                  <TableHead>Data richiesta</TableHead>
                  <TableHead>Costo</TableHead>
                  <TableHead>Fornitore</TableHead>
                  <TableHead className="text-right">Azioni</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map(i => (
                  <TableRow key={i.id} data-testid={`int-row-${i.id}`}>
                    <TableCell className="max-w-xs">
                      <div className="font-medium">{i.titolo}</div>
                      {i.descrizione && <div className="text-xs text-slate-500 truncate" title={i.descrizione}>{i.descrizione}</div>}
                    </TableCell>
                    <TableCell className="text-sm">
                      <div>{i.immobile_titolo || '-'}</div>
                      {i.unita_codice && <div className="text-xs text-slate-500">{i.unita_codice}</div>}
                    </TableCell>
                    <TableCell>
                      <Badge className={`${PRIORITA[i.priorita]} text-white border-0`}>{i.priorita}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={`${STATO[i.stato]} text-white border-0`}>{i.stato.replace('_',' ')}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">{i.data_richiesta}</TableCell>
                    <TableCell className="text-sm">
                      {i.costo_finale ? (
                        <span className="font-medium">€{i.costo_finale}</span>
                      ) : i.costo_stimato ? (
                        <span className="text-slate-500">~€{i.costo_stimato}</span>
                      ) : '-'}
                    </TableCell>
                    <TableCell className="text-sm">{i.fornitore || '-'}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => { setEditingItem(i); setNewStato(i.stato); setStatoEditOpen(true); }} title="Cambia stato">
                        <Pencil className="w-4 h-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Dialog crea */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Nuovo intervento</DialogTitle>
            <DialogDescription>Apri una richiesta di manutenzione per immobile o unità specifica.</DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Label>Immobile *</Label>
              <Select value={form.immobile_id} onValueChange={v => setForm({...form, immobile_id: v, unita_id: ''})}>
                <SelectTrigger data-testid="select-immobile"><SelectValue placeholder="Seleziona" /></SelectTrigger>
                <SelectContent>
                  {immobili.map(im => <SelectItem key={im.id} value={im.id}>{im.codice} - {im.titolo}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="col-span-2">
              <Label>Unità (opzionale)</Label>
              <Select value={form.unita_id} onValueChange={v => setForm({...form, unita_id: v})} disabled={!form.immobile_id}>
                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                <SelectContent>
                  {filteredUnita.map(u => <SelectItem key={u.id} value={u.id}>{u.codice_unita}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="col-span-2">
              <Label>Titolo *</Label>
              <Input value={form.titolo} onChange={e => setForm({...form, titolo: e.target.value})} placeholder="Es. Riparazione caldaia" data-testid="input-titolo" />
            </div>
            <div className="col-span-2">
              <Label>Descrizione</Label>
              <Textarea value={form.descrizione} onChange={e => setForm({...form, descrizione: e.target.value})} rows={3} />
            </div>
            <div>
              <Label>Priorità</Label>
              <Select value={form.priorita} onValueChange={v => setForm({...form, priorita: v})}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="bassa">Bassa</SelectItem>
                  <SelectItem value="media">Media</SelectItem>
                  <SelectItem value="alta">Alta</SelectItem>
                  <SelectItem value="urgente">Urgente</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Stato iniziale</Label>
              <Select value={form.stato} onValueChange={v => setForm({...form, stato: v})}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="richiesto">Richiesto</SelectItem>
                  <SelectItem value="pianificato">Pianificato</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Costo stimato (€)</Label>
              <Input type="number" step="0.01" value={form.costo_stimato} onChange={e => setForm({...form, costo_stimato: e.target.value})} />
            </div>
            <div>
              <Label>Data pianificata</Label>
              <Input type="date" value={form.data_pianificata} onChange={e => setForm({...form, data_pianificata: e.target.value})} />
            </div>
            <div className="col-span-2">
              <Label>Fornitore</Label>
              <Input value={form.fornitore} onChange={e => setForm({...form, fornitore: e.target.value})} placeholder="Es. Idraulico Rossi srl" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Annulla</Button>
            <Button onClick={handleCreate} data-testid="btn-save-intervento">Crea</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog cambio stato */}
      <Dialog open={statoEditOpen} onOpenChange={setStatoEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cambia stato intervento</DialogTitle>
            <DialogDescription>{editingItem?.titolo}</DialogDescription>
          </DialogHeader>
          <div>
            <Label>Nuovo stato</Label>
            <Select value={newStato} onValueChange={setNewStato}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="richiesto">Richiesto</SelectItem>
                <SelectItem value="pianificato">Pianificato</SelectItem>
                <SelectItem value="in_corso">In corso</SelectItem>
                <SelectItem value="completato">Completato</SelectItem>
                <SelectItem value="annullato">Annullato</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStatoEditOpen(false)}>Annulla</Button>
            <Button onClick={handleStatoChange}>Conferma</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
