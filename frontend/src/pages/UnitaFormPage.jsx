import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useApi, useFetch } from '../hooks';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import { ArrowLeft, Loader2 } from 'lucide-react';

const schema = z.object({
  codice_unita: z.string().min(1, 'Codice obbligatorio'),
  tipo_immobile: z.string().min(1, 'Tipo obbligatorio'),
  mq: z.number().optional().nullable(),
  destinazione_uso_attuale: z.string().optional(),
  note: z.string().optional(),
  foto_urls: z.string().optional(),
});

const TIPI = [
  { value: 'appartamento', label: 'Appartamento' },
  { value: 'ufficio', label: 'Ufficio' },
  { value: 'negozio', label: 'Negozio' },
  { value: 'magazzino', label: 'Magazzino' },
  { value: 'capannone', label: 'Capannone' },
  { value: 'box_auto', label: 'Box Auto' },
  { value: 'posto_auto', label: 'Posto Auto' },
  { value: 'cantina', label: 'Cantina' },
  { value: 'terreno', label: 'Terreno' },
  { value: 'villa', label: 'Villa' },
  { value: 'loft', label: 'Loft' },
  { value: 'attico', label: 'Attico' },
  { value: 'mansarda', label: 'Mansarda' },
  { value: 'locale_commerciale', label: 'Locale Commerciale' },
  { value: 'laboratorio', label: 'Laboratorio' },
  { value: 'altro', label: 'Altro' },
];

export default function UnitaFormPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const immobileId = searchParams.get('immobile_id');
  const { request, loading } = useApi();
  const { data: immobile } = useFetch(immobileId ? `/immobili/${immobileId}` : null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      codice_unita: '',
      tipo_immobile: '',
      mq: null,
      destinazione_uso_attuale: '',
      note: '',
      foto_urls: '',
    },
  });

  const tipoValue = watch('tipo_immobile');

  const onSubmit = async (data) => {
    if (!immobileId) {
      toast.error('ID immobile mancante');
      return;
    }
    try {
      const payload = {
        ...data,
        immobile_id: immobileId,
        mq: data.mq ? parseFloat(data.mq) : null,
        foto_urls: data.foto_urls ? data.foto_urls.split('\n').map(s => s.trim()).filter(Boolean) : [],
      };
      await request('POST', '/unita', payload);
      toast.success('Unità creata con successo');
      navigate(`/immobili/${immobileId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore durante il salvataggio');
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold font-heading">Nuova Unità</h1>
          <p className="text-slate-500">
            {immobile ? `Per: ${immobile.titolo}` : 'Caricamento...'}
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Dati Principali</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="codice_unita">Codice Unità *</Label>
                <Input
                  id="codice_unita"
                  {...register('codice_unita')}
                  placeholder="es. A-1"
                />
                {errors.codice_unita && (
                  <p className="text-sm text-red-500">{errors.codice_unita.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="tipo_immobile">Tipo *</Label>
                <Select
                  value={tipoValue}
                  onValueChange={(v) => setValue('tipo_immobile', v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleziona tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    {TIPI.map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="mq">Superficie (mq)</Label>
                <Input
                  id="mq"
                  type="number"
                  step="0.1"
                  {...register('mq', { valueAsNumber: true })}
                  placeholder="es. 75.5"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="destinazione_uso_attuale">Destinazione d'Uso</Label>
                <Select
                  value={watch('destinazione_uso_attuale')}
                  onValueChange={(v) => setValue('destinazione_uso_attuale', v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleziona..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="residenziale">Residenziale</SelectItem>
                    <SelectItem value="commerciale">Commerciale</SelectItem>
                    <SelectItem value="ufficio">Ufficio</SelectItem>
                    <SelectItem value="industriale">Industriale</SelectItem>
                    <SelectItem value="deposito">Deposito</SelectItem>
                    <SelectItem value="parcheggio">Parcheggio</SelectItem>
                    <SelectItem value="misto">Misto</SelectItem>
                    <SelectItem value="altro">Altro</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="foto_urls">URL Foto (uno per riga)</Label>
              <Textarea
                id="foto_urls"
                {...register('foto_urls')}
                placeholder="https://..."
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Note</CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea
              {...register('note')}
              placeholder="Note sull'unità..."
              rows={4}
            />
          </CardContent>
        </Card>

        <div className="flex justify-end gap-4">
          <Button type="button" variant="outline" onClick={() => navigate(-1)}>
            Annulla
          </Button>
          <Button type="submit" disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creazione...
              </>
            ) : (
              'Crea Unità'
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
