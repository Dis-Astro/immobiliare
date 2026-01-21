import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useApi } from '../../hooks';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { ArrowLeft, MapPin, Loader2 } from 'lucide-react';

const schema = z.object({
  codice: z.string().min(1, 'Codice obbligatorio'),
  titolo: z.string().min(1, 'Titolo obbligatorio'),
  indirizzo: z.string().min(1, 'Indirizzo obbligatorio'),
  lat: z.number().optional().nullable(),
  lon: z.number().optional().nullable(),
  catastale_comune: z.string().optional(),
  foglio: z.string().optional(),
  particella: z.string().optional(),
  subalterno: z.string().optional(),
  categoria: z.string().optional(),
  rendita: z.number().optional().nullable(),
  note: z.string().optional(),
  foto_url: z.string().optional(),
});

export default function ImmobileFormPage() {
  const navigate = useNavigate();
  const { request, loading } = useApi();
  const [geocoding, setGeocoding] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      codice: '',
      titolo: '',
      indirizzo: '',
      lat: null,
      lon: null,
    },
  });

  const handleGeocode = async () => {
    const indirizzo = watch('indirizzo');
    if (!indirizzo) {
      toast.error('Inserisci prima un indirizzo');
      return;
    }

    setGeocoding(true);
    try {
      const response = await request('POST', '/geocode', { address: indirizzo });
      setValue('lat', response.lat);
      setValue('lon', response.lon);
      toast.success(`Coordinate trovate: ${response.lat}, ${response.lon}`);
    } catch (error) {
      toast.error('Impossibile geocodificare l\'indirizzo');
    } finally {
      setGeocoding(false);
    }
  };

  const onSubmit = async (data) => {
    try {
      // Convert empty strings to null for numeric fields
      const payload = {
        ...data,
        lat: data.lat || null,
        lon: data.lon || null,
        rendita: data.rendita ? parseFloat(data.rendita) : null,
      };

      await request('POST', '/immobili', payload);
      toast.success('Immobile creato con successo');
      navigate('/immobili');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore durante la creazione');
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold font-heading">Nuovo Immobile</h1>
          <p className="text-slate-500">Inserisci i dati del nuovo immobile</p>
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
                <Label htmlFor="codice">Codice *</Label>
                <Input
                  id="codice"
                  {...register('codice')}
                  placeholder="es. IMM-001"
                  data-testid="input-codice"
                />
                {errors.codice && (
                  <p className="text-sm text-red-500">{errors.codice.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="titolo">Titolo *</Label>
                <Input
                  id="titolo"
                  {...register('titolo')}
                  placeholder="es. Palazzo Centro Storico"
                  data-testid="input-titolo"
                />
                {errors.titolo && (
                  <p className="text-sm text-red-500">{errors.titolo.message}</p>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="indirizzo">Indirizzo *</Label>
              <div className="flex gap-2">
                <Input
                  id="indirizzo"
                  {...register('indirizzo')}
                  placeholder="Via Roma 1, 00100 Roma RM"
                  className="flex-1"
                  data-testid="input-indirizzo"
                />
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={handleGeocode}
                  disabled={geocoding}
                >
                  {geocoding ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <MapPin className="w-4 h-4" />
                  )}
                  Geocodifica
                </Button>
              </div>
              {errors.indirizzo && (
                <p className="text-sm text-red-500">{errors.indirizzo.message}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="lat">Latitudine</Label>
                <Input
                  id="lat"
                  type="number"
                  step="any"
                  {...register('lat', { valueAsNumber: true })}
                  placeholder="41.9028"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lon">Longitudine</Label>
                <Input
                  id="lon"
                  type="number"
                  step="any"
                  {...register('lon', { valueAsNumber: true })}
                  placeholder="12.4964"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="foto_url">URL Foto</Label>
              <Input
                id="foto_url"
                {...register('foto_url')}
                placeholder="https://..."
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Dati Catastali</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label htmlFor="catastale_comune">Comune</Label>
                <Input
                  id="catastale_comune"
                  {...register('catastale_comune')}
                  placeholder="Roma"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="foglio">Foglio</Label>
                <Input
                  id="foglio"
                  {...register('foglio')}
                  placeholder="123"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="particella">Particella</Label>
                <Input
                  id="particella"
                  {...register('particella')}
                  placeholder="456"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="subalterno">Subalterno</Label>
                <Input
                  id="subalterno"
                  {...register('subalterno')}
                  placeholder="1"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="categoria">Categoria</Label>
                <Input
                  id="categoria"
                  {...register('categoria')}
                  placeholder="A/2"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="rendita">Rendita Catastale (€)</Label>
                <Input
                  id="rendita"
                  type="number"
                  step="0.01"
                  {...register('rendita', { valueAsNumber: true })}
                  placeholder="1500.00"
                />
              </div>
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
              placeholder="Note aggiuntive sull'immobile..."
              rows={4}
            />
          </CardContent>
        </Card>

        <div className="flex justify-end gap-4">
          <Button type="button" variant="outline" onClick={() => navigate(-1)}>
            Annulla
          </Button>
          <Button type="submit" disabled={loading} data-testid="submit-immobile">
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creazione...
              </>
            ) : (
              'Crea Immobile'
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
