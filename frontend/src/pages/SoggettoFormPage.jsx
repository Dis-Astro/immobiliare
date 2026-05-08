import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../stores';
import { useApi } from '../hooks';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Skeleton } from '../components/ui/skeleton';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { ArrowLeft, Save, Loader2, User, Building } from 'lucide-react';
import { toast } from 'sonner';

export default function SoggettoFormPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;
  const { request, loading: submitting } = useApi();
  const [loading, setLoading] = useState(isEdit);

  const [form, setForm] = useState({
    tipo: 'persona',
    nome: '',
    cf: '',
    piva: '',
    indirizzo: '',
    pec: '',
    email: '',
    telefono: '',
    iban: '',
    note: '',
  });

  useEffect(() => {
    if (!isEdit) return;
    (async () => {
      try {
        const res = await api.get(`/soggetti/${id}`);
        setForm({
          tipo: res.data.tipo || 'persona',
          nome: res.data.nome || '',
          cf: res.data.cf || '',
          piva: res.data.piva || '',
          indirizzo: res.data.indirizzo || '',
          pec: res.data.pec || '',
          email: res.data.email || '',
          telefono: res.data.telefono || '',
          iban: res.data.iban || '',
          note: res.data.note || '',
        });
      } catch (err) {
        toast.error('Errore caricamento soggetto');
      } finally {
        setLoading(false);
      }
    })();
  }, [id, isEdit]);

  const update = (key, value) => setForm(prev => ({ ...prev, [key]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.nome.trim()) {
      toast.error('Nome / Ragione sociale obbligatorio');
      return;
    }
    if (form.tipo === 'persona' && !form.cf) {
      toast.error('Codice fiscale obbligatorio per persona fisica');
      return;
    }
    if (form.tipo === 'azienda' && !form.piva) {
      toast.error('Partita IVA obbligatoria per azienda');
      return;
    }

    const payload = Object.fromEntries(
      Object.entries(form).map(([k, v]) => [k, v === '' ? null : v])
    );
    payload.tipo = form.tipo;
    payload.nome = form.nome;

    try {
      if (isEdit) {
        await request('PUT', `/soggetti/${id}`, payload);
        toast.success('Soggetto aggiornato');
        navigate(`/soggetti/${id}`);
      } else {
        const res = await request('POST', '/soggetti', payload);
        toast.success('Soggetto creato');
        navigate(`/soggetti/${res.id}`);
      }
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 max-w-3xl">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-6" data-testid="soggetto-form-page">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold font-heading">
            {isEdit ? 'Modifica Soggetto' : 'Nuovo Soggetto'}
          </h1>
          <p className="text-slate-500">
            {isEdit ? 'Aggiorna i dati del soggetto' : 'Inserisci i dati di un nuovo locatore o affittuario'}
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Tipo</CardTitle>
          </CardHeader>
          <CardContent>
            <Select value={form.tipo} onValueChange={v => update('tipo', v)}>
              <SelectTrigger data-testid="select-tipo"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="persona">
                  <div className="flex items-center gap-2"><User className="w-4 h-4" /> Persona Fisica</div>
                </SelectItem>
                <SelectItem value="azienda">
                  <div className="flex items-center gap-2"><Building className="w-4 h-4" /> Azienda</div>
                </SelectItem>
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Dati anagrafici</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="nome">{form.tipo === 'azienda' ? 'Ragione sociale' : 'Nome e Cognome'} *</Label>
              <Input id="nome" value={form.nome} onChange={e => update('nome', e.target.value)} data-testid="input-nome" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="cf">Codice Fiscale {form.tipo === 'persona' && '*'}</Label>
                <Input id="cf" value={form.cf} onChange={e => update('cf', e.target.value.toUpperCase())} placeholder="RSSMRA80A01H501Z" data-testid="input-cf" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="piva">Partita IVA {form.tipo === 'azienda' && '*'}</Label>
                <Input id="piva" value={form.piva} onChange={e => update('piva', e.target.value)} placeholder="12345678901" data-testid="input-piva" />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="indirizzo">Indirizzo</Label>
              <Input id="indirizzo" value={form.indirizzo} onChange={e => update('indirizzo', e.target.value)} placeholder="Via Roma 1, 00100 Roma" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Contatti</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={form.email} onChange={e => update('email', e.target.value)} data-testid="input-email" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pec">PEC</Label>
                <Input id="pec" type="email" value={form.pec} onChange={e => update('pec', e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="telefono">Telefono</Label>
                <Input id="telefono" value={form.telefono} onChange={e => update('telefono', e.target.value)} placeholder="+39 333 1234567" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="iban">IBAN</Label>
                <Input id="iban" value={form.iban} onChange={e => update('iban', e.target.value.toUpperCase())} placeholder="IT60X0542811101000000123456" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Note</CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea value={form.note} onChange={e => update('note', e.target.value)} rows={4} placeholder="Note aggiuntive..." />
          </CardContent>
        </Card>

        <div className="flex justify-end gap-4">
          <Button type="button" variant="outline" onClick={() => navigate(-1)}>Annulla</Button>
          <Button type="submit" disabled={submitting} data-testid="btn-submit-soggetto">
            {submitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
            {isEdit ? 'Aggiorna' : 'Crea soggetto'}
          </Button>
        </div>
      </form>
    </div>
  );
}
