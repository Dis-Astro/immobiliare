import React, { useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useFetch, useApi } from '../hooks';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Skeleton } from '../components/ui/skeleton';
import { toast } from 'sonner';
import { 
  ArrowLeft, 
  Plus, 
  Trash2, 
  Upload, 
  Camera,
  Save,
  FileText,
  Check,
  X,
  Image as ImageIcon,
  Loader2
} from 'lucide-react';
import { cn } from '../lib/utils';

const STATI_AMBIENTE = ['ottimo', 'buono', 'usurato', 'danneggiato'];

const AMBIENTI_DEFAULT = [
  'Ingresso',
  'Soggiorno',
  'Cucina',
  'Camera da letto 1',
  'Camera da letto 2',
  'Bagno 1',
  'Bagno 2',
  'Balcone/Terrazzo',
  'Cantina',
  'Box auto',
];

const checklistItemSchema = z.object({
  ambiente: z.string().min(1, 'Nome ambiente obbligatorio'),
  stato: z.enum(['ottimo', 'buono', 'usurato', 'danneggiato']),
  note: z.string().optional(),
  foto_refs: z.array(z.string()).default([]),
});

const verbaleSchema = z.object({
  contratto_id: z.string().min(1, 'Seleziona un contratto'),
  tipo: z.enum(['consegna', 'riconsegna']),
  data: z.string().min(1, 'Data obbligatoria'),
  checklist: z.array(checklistItemSchema),
  note: z.string().optional(),
});

export default function VerbaleFormPage() {
  const navigate = useNavigate();
  const { contrattoId } = useParams();
  const { request, loading: submitting } = useApi();
  
  const [checklist, setChecklist] = useState(
    AMBIENTI_DEFAULT.map(ambiente => ({
      ambiente,
      stato: 'buono',
      note: '',
      foto_refs: [],
    }))
  );
  const [uploadingPhoto, setUploadingPhoto] = useState(null);
  const [tipo, setTipo] = useState('consegna');
  const [data, setData] = useState(new Date().toISOString().split('T')[0]);
  const [note, setNote] = useState('');

  // Fetch contratto data
  const { data: contratto, loading: loadingContratto } = useFetch(
    contrattoId ? `/contratti/${contrattoId}` : null
  );

  const addAmbiente = () => {
    setChecklist(prev => [...prev, {
      ambiente: `Ambiente ${prev.length + 1}`,
      stato: 'buono',
      note: '',
      foto_refs: [],
    }]);
  };

  const removeAmbiente = (index) => {
    setChecklist(prev => prev.filter((_, i) => i !== index));
  };

  const updateAmbiente = (index, field, value) => {
    setChecklist(prev => prev.map((item, i) => 
      i === index ? { ...item, [field]: value } : item
    ));
  };

  const handlePhotoUpload = async (index, file) => {
    if (!file) return;
    
    // Validate file
    if (!file.type.startsWith('image/')) {
      toast.error('Il file deve essere un\'immagine');
      return;
    }
    
    if (file.size > 10 * 1024 * 1024) {
      toast.error('L\'immagine non può superare 10MB');
      return;
    }
    
    // Check max photos per verbale (10)
    const totalPhotos = checklist.reduce((sum, item) => sum + item.foto_refs.length, 0);
    if (totalPhotos >= 10) {
      toast.error('Massimo 10 foto per verbale');
      return;
    }
    
    setUploadingPhoto(index);
    
    try {
      // In a real app, upload to server
      // For now, create a local URL
      const photoUrl = URL.createObjectURL(file);
      
      setChecklist(prev => prev.map((item, i) => 
        i === index ? { 
          ...item, 
          foto_refs: [...item.foto_refs, photoUrl] 
        } : item
      ));
      
      toast.success('Foto aggiunta');
    } catch (error) {
      toast.error('Errore nel caricamento della foto');
    } finally {
      setUploadingPhoto(null);
    }
  };

  const removePhoto = (ambienteIndex, photoIndex) => {
    setChecklist(prev => prev.map((item, i) => 
      i === ambienteIndex ? {
        ...item,
        foto_refs: item.foto_refs.filter((_, pi) => pi !== photoIndex)
      } : item
    ));
  };

  const handleSubmit = async () => {
    try {
      const payload = {
        contratto_id: contrattoId,
        tipo,
        data,
        checklist: checklist.map(item => ({
          ambiente: item.ambiente,
          stato: item.stato,
          note: item.note || null,
          foto_refs: item.foto_refs,
        })),
        note: note || null,
      };
      
      await request('POST', '/verbali', payload);
      toast.success(`Verbale di ${tipo} creato con successo!`);
      navigate(`/contratti/${contrattoId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore nella creazione del verbale');
    }
  };

  if (loadingContratto) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="verbale-form">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold font-heading">Nuovo Verbale</h1>
          <p className="text-slate-500">
            {contratto ? `Contratto ${contratto.codice_contratto}` : 'Verbale di consegna/riconsegna'}
          </p>
        </div>
      </div>

      {/* Tipo e Data */}
      <Card>
        <CardHeader>
          <CardTitle>Informazioni Generali</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Tipo Verbale *</Label>
              <Select value={tipo} onValueChange={setTipo}>
                <SelectTrigger data-testid="select-tipo-verbale">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="consegna">Consegna</SelectItem>
                  <SelectItem value="riconsegna">Riconsegna</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Data *</Label>
              <Input
                type="date"
                value={data}
                onChange={(e) => setData(e.target.value)}
                data-testid="input-data-verbale"
              />
            </div>
          </div>
          
          {contratto && (
            <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-slate-500">Immobile</p>
                  <p className="font-medium">{contratto.immobile_titolo}</p>
                </div>
                <div>
                  <p className="text-slate-500">Unità</p>
                  <p className="font-medium">{contratto.unita_codice}</p>
                </div>
                <div>
                  <p className="text-slate-500">Affittuario</p>
                  <p className="font-medium">{contratto.affittuario_nome}</p>
                </div>
                <div>
                  <p className="text-slate-500">Locatore</p>
                  <p className="font-medium">{contratto.locatore_nome}</p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Checklist Ambienti */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Checklist Ambienti</CardTitle>
            <CardDescription>
              Valuta lo stato di ogni ambiente. Puoi aggiungere fino a 10 foto totali.
            </CardDescription>
          </div>
          <Button variant="outline" onClick={addAmbiente}>
            <Plus className="w-4 h-4 mr-2" />
            Aggiungi Ambiente
          </Button>
        </CardHeader>
        <CardContent className="space-y-6">
          {checklist.map((item, index) => (
            <div 
              key={index} 
              className="p-4 border rounded-lg space-y-4"
              data-testid={`checklist-item-${index}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Ambiente</Label>
                    <Input
                      value={item.ambiente}
                      onChange={(e) => updateAmbiente(index, 'ambiente', e.target.value)}
                      placeholder="Nome ambiente"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Stato</Label>
                    <Select 
                      value={item.stato} 
                      onValueChange={(v) => updateAmbiente(index, 'stato', v)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {STATI_AMBIENTE.map(stato => (
                          <SelectItem key={stato} value={stato}>
                            <div className="flex items-center gap-2">
                              <div className={cn(
                                "w-2 h-2 rounded-full",
                                stato === 'ottimo' && "bg-emerald-500",
                                stato === 'buono' && "bg-blue-500",
                                stato === 'usurato' && "bg-amber-500",
                                stato === 'danneggiato' && "bg-red-500"
                              )} />
                              <span className="capitalize">{stato}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Note</Label>
                    <Input
                      value={item.note}
                      onChange={(e) => updateAmbiente(index, 'note', e.target.value)}
                      placeholder="Note opzionali"
                    />
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-red-500 hover:text-red-700 ml-2"
                  onClick={() => removeAmbiente(index)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
              
              {/* Foto */}
              <div className="space-y-2">
                <Label>Foto ({item.foto_refs.length}/10 totali per verbale)</Label>
                <div className="flex flex-wrap gap-2">
                  {item.foto_refs.map((foto, fotoIndex) => (
                    <div key={fotoIndex} className="relative group">
                      <img 
                        src={foto} 
                        alt={`${item.ambiente} - Foto ${fotoIndex + 1}`}
                        className="w-20 h-20 object-cover rounded-lg border"
                      />
                      <button
                        onClick={() => removePhoto(index, fotoIndex)}
                        className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <X className="w-3 h-3 mx-auto" />
                      </button>
                    </div>
                  ))}
                  
                  <label className="w-20 h-20 flex items-center justify-center border-2 border-dashed rounded-lg cursor-pointer hover:border-primary transition-colors">
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => handlePhotoUpload(index, e.target.files[0])}
                      disabled={uploadingPhoto !== null}
                    />
                    {uploadingPhoto === index ? (
                      <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                    ) : (
                      <Camera className="w-6 h-6 text-slate-400" />
                    )}
                  </label>
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Note Generali */}
      <Card>
        <CardHeader>
          <CardTitle>Note Generali</CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Note generali sul verbale..."
            rows={4}
          />
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-end gap-4">
        <Button variant="outline" onClick={() => navigate(-1)}>
          Annulla
        </Button>
        <Button onClick={handleSubmit} disabled={submitting} data-testid="submit-verbale">
          {submitting ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Salvataggio...
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-2" />
              Salva Verbale
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
