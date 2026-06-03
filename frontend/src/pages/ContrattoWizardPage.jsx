import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { api } from '../stores';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  ArrowLeft, 
  ArrowRight, 
  Check, 
  Building2, 
  Users, 
  FileText, 
  Euro, 
  Bell, 
  Download,
  Star,
  Loader2
} from 'lucide-react';
import { cn } from '../lib/utils';

const STEPS = [
  { id: 'unita', title: 'Unità', icon: Building2, description: 'Seleziona l\'unità da locare' },
  { id: 'locatore', title: 'Locatore', icon: Users, description: 'Seleziona o crea il locatore' },
  { id: 'affittuario', title: 'Affittuario', icon: Users, description: 'Seleziona o crea l\'affittuario' },
  { id: 'termini', title: 'Termini', icon: Euro, description: 'Definisci canone, durata e deposito' },
  { id: 'reminder', title: 'Reminder', icon: Bell, description: 'Configura le notifiche' },
  { id: 'conferma', title: 'Conferma', icon: Check, description: 'Rivedi e conferma' },
];

// Validation schemas for each step
const unitaSchema = z.object({
  unita_id: z.string().min(1, 'Seleziona un\'unità'),
});

const locatoreSchema = z.object({
  locatore_id: z.string().min(1, 'Seleziona un locatore'),
});

const affittuarioSchema = z.object({
  affittuario_id: z.string().min(1, 'Seleziona un affittuario'),
});

const terminiSchema = z.object({
  data_firma: z.string().min(1, 'Data firma obbligatoria'),
  data_inizio: z.string().min(1, 'Data inizio obbligatoria'),
  durata_mesi: z.number().min(1, 'Durata minima 1 mese').max(240, 'Durata massima 240 mesi'),
  canone_importo: z.number().min(1, 'Canone obbligatorio'),
  periodicita: z.enum(['mensile', 'trimestrale', 'annuale']),
  giorno_scadenza: z.number().min(1).max(28),
  deposito_importo: z.number().optional(),
});

const reminderSchema = z.object({
  scadenza_contratto: z.array(z.number()).default([365, 30, 1]),
  rata_scaduta: z.array(z.number()).default([1, 7, 15]),
  documento_scadenza: z.array(z.number()).default([30, 7]),
});

export default function ContrattoWizardPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // Data for selections
  const [unita, setUnita] = useState([]);
  const [soggetti, setSoggetti] = useState([]);
  const [selectedUnita, setSelectedUnita] = useState(null);
  const [selectedLocatore, setSelectedLocatore] = useState(null);
  const [selectedAffittuario, setSelectedAffittuario] = useState(null);
  const [affittuarioRating, setAffittuarioRating] = useState(null);
  
  // Form data
  const [formData, setFormData] = useState({
    unita_id: '',
    locatore_id: '',
    affittuario_id: '',
    data_firma: new Date().toISOString().split('T')[0],
    data_inizio: new Date().toISOString().split('T')[0],
    durata_mesi: 12,
    canone_importo: 0,
    periodicita: 'mensile',
    giorno_scadenza: 5,
    deposito_importo: 0,
    reminder_config: {
      scadenza_contratto: [365, 30, 1],
      rata_scaduta: [1, 7, 15],
      documento_scadenza: [30, 7],
    },
    note: '',
  });

  // Load data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [unitaRes, soggettiRes] = await Promise.all([
          api.get(`/unita?limit=100&disponibile_al=${formData.data_inizio}`),
          api.get('/soggetti?limit=100'),
        ]);
        setUnita(unitaRes.data);
        setSoggetti(soggettiRes.data);
      } catch (error) {
        toast.error('Errore nel caricamento dei dati');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [formData.data_inizio]);

  // Fetch affittuario rating when selected
  useEffect(() => {
    const fetchRating = async () => {
      if (formData.affittuario_id) {
        try {
          const res = await api.get(`/valutazioni/affittuario/${formData.affittuario_id}/score`);
          setAffittuarioRating(res.data);
        } catch (error) {
          setAffittuarioRating(null);
        }
      }
    };
    fetchRating();
  }, [formData.affittuario_id]);

  const updateFormData = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Update selected entities for preview
    if (field === 'unita_id') {
      setSelectedUnita(unita.find(u => u.id === value));
    }
    if (field === 'locatore_id') {
      setSelectedLocatore(soggetti.find(s => s.id === value));
    }
    if (field === 'affittuario_id') {
      setSelectedAffittuario(soggetti.find(s => s.id === value));
    }
  };

  const validateCurrentStep = () => {
    try {
      switch (currentStep) {
        case 0: unitaSchema.parse({ unita_id: formData.unita_id }); break;
        case 1: locatoreSchema.parse({ locatore_id: formData.locatore_id }); break;
        case 2: affittuarioSchema.parse({ affittuario_id: formData.affittuario_id }); break;
        case 3: terminiSchema.parse({
          data_firma: formData.data_firma,
          data_inizio: formData.data_inizio,
          durata_mesi: formData.durata_mesi,
          canone_importo: formData.canone_importo,
          periodicita: formData.periodicita,
          giorno_scadenza: formData.giorno_scadenza,
          deposito_importo: formData.deposito_importo,
        }); break;
        case 4: return true; // Reminder step always valid
        case 5: return true; // Confirm step
        default: return true;
      }
      return true;
    } catch (error) {
      if (error.errors) {
        toast.error(error.errors[0].message);
      }
      return false;
    }
  };

  const nextStep = () => {
    if (validateCurrentStep()) {
      setCurrentStep(prev => Math.min(prev + 1, STEPS.length - 1));
    }
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 0));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const payload = {
        unita_id: formData.unita_id,
        locatore_id: formData.locatore_id,
        affittuario_id: formData.affittuario_id,
        data_firma: formData.data_firma,
        data_inizio: formData.data_inizio,
        durata_mesi: formData.durata_mesi,
        canone_importo: formData.canone_importo,
        periodicita: formData.periodicita,
        giorno_scadenza: formData.giorno_scadenza,
        deposito_importo: formData.deposito_importo || null,
        deposito_stato: formData.deposito_importo ? 'da_versare' : null,
        note: formData.note,
        reminder_config: formData.reminder_config,
      };
      
      const response = await api.post('/contratti', payload);
      toast.success('Contratto creato con successo!');
      navigate(`/contratti/${response.data.id}`);
    } catch (error) {
      // Handle different error formats
      let errorMsg = 'Errore nella creazione del contratto';
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === 'string') {
          errorMsg = detail;
        } else if (Array.isArray(detail)) {
          errorMsg = detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
        } else if (typeof detail === 'object') {
          errorMsg = detail.msg || detail.message || JSON.stringify(detail);
        }
      }
      toast.error(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // Unità
        return (
          <div className="space-y-4">
            <div className="max-w-xs space-y-2">
              <Label>Data inizio contratto *</Label>
              <Input
                type="date"
                value={formData.data_inizio}
                onChange={(e) => {
                  updateFormData('data_inizio', e.target.value);
                  updateFormData('unita_id', '');
                  setSelectedUnita(null);
                }}
                data-testid="input-data-inizio-step-unita"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {unita.map(u => (
                <Card 
                  key={u.id}
                  className={cn(
                    "cursor-pointer transition-all hover:shadow-md",
                    formData.unita_id === u.id && "ring-2 ring-primary"
                  )}
                  onClick={() => updateFormData('unita_id', u.id)}
                  data-testid={`unita-card-${u.id}`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-semibold">{u.codice_unita}</p>
                        <p className="text-sm text-slate-500">{u.tipo_immobile?.replace('_', ' ')}</p>
                        <p className="text-sm text-slate-500">{u.mq} mq</p>
                        {u.stato === 'prenotata' && (
                          <Badge variant="outline" className="mt-2">Contratto futuro</Badge>
                        )}
                      </div>
                      {formData.unita_id === u.id && (
                        <Check className="w-5 h-5 text-primary" />
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            {unita.length === 0 && (
              <p className="text-center text-slate-500 py-8">
                Nessuna unità disponibile. Tutte le unità sono già locate.
              </p>
            )}
          </div>
        );
      
      case 1: // Locatore
      case 2: // Affittuario
        const fieldName = currentStep === 1 ? 'locatore_id' : 'affittuario_id';
        const selectedId = currentStep === 1 ? formData.locatore_id : formData.affittuario_id;
        const isAffittuario = currentStep === 2;
        
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {soggetti.map(s => (
                <Card 
                  key={s.id}
                  className={cn(
                    "cursor-pointer transition-all hover:shadow-md",
                    selectedId === s.id && "ring-2 ring-primary"
                  )}
                  onClick={() => updateFormData(fieldName, s.id)}
                  data-testid={`soggetto-card-${s.id}`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-semibold">{s.nome}</p>
                        <Badge variant="outline" className="mt-1 capitalize">{s.tipo}</Badge>
                        <p className="text-sm text-slate-500 mt-1">{s.email || s.telefono}</p>
                        {isAffittuario && s.rating_medio && (
                          <div className="flex items-center gap-1 mt-2">
                            {[...Array(5)].map((_, i) => (
                              <Star 
                                key={i}
                                className={cn(
                                  "w-3 h-3",
                                  i < Math.round(s.rating_medio) ? "fill-amber-400 text-amber-400" : "text-slate-300"
                                )}
                              />
                            ))}
                            <span className="text-xs text-slate-500">({s.rating_medio?.toFixed(1)})</span>
                          </div>
                        )}
                      </div>
                      {selectedId === s.id && (
                        <Check className="w-5 h-5 text-primary" />
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            
            {isAffittuario && affittuarioRating && (
              <Card className="bg-slate-50 dark:bg-slate-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Valutazione Affittuario</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-slate-500">Score Pagamenti</p>
                      <p className={cn(
                        "font-semibold",
                        affittuarioRating.score_pagamenti >= 80 ? "text-emerald-600" :
                        affittuarioRating.score_pagamenti >= 50 ? "text-amber-600" : "text-red-600"
                      )}>
                        {affittuarioRating.score_pagamenti}/100
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-500">Puntualità</p>
                      <p className="font-semibold">{affittuarioRating.percent_puntualita}%</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Ritardo Medio</p>
                      <p className="font-semibold">{affittuarioRating.ritardo_medio_giorni} gg</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Tag</p>
                      <Badge className={cn(
                        affittuarioRating.tag_color === 'green' && "bg-emerald-100 text-emerald-700",
                        affittuarioRating.tag_color === 'yellow' && "bg-amber-100 text-amber-700",
                        affittuarioRating.tag_color === 'red' && "bg-red-100 text-red-700",
                        affittuarioRating.tag_color === 'orange' && "bg-orange-100 text-orange-700"
                      )}>
                        {affittuarioRating.tag}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
            
            <Button variant="outline" onClick={() => navigate('/soggetti/nuovo')}>
              Crea Nuovo Soggetto
            </Button>
          </div>
        );
      
      case 3: // Termini
        return (
          <div className="space-y-6 max-w-2xl">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Data Firma *</Label>
                <Input
                  type="date"
                  value={formData.data_firma}
                  onChange={(e) => updateFormData('data_firma', e.target.value)}
                  data-testid="input-data-firma"
                />
              </div>
              <div className="space-y-2">
                <Label>Data Inizio *</Label>
                <Input
                  type="date"
                  value={formData.data_inizio}
                  onChange={(e) => updateFormData('data_inizio', e.target.value)}
                  data-testid="input-data-inizio"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Durata (mesi) *</Label>
                <Input
                  type="number"
                  min="1"
                  max="240"
                  value={formData.durata_mesi}
                  onChange={(e) => updateFormData('durata_mesi', parseInt(e.target.value) || 0)}
                  data-testid="input-durata"
                />
              </div>
              <div className="space-y-2">
                <Label>Periodicità *</Label>
                <Select 
                  value={formData.periodicita} 
                  onValueChange={(v) => updateFormData('periodicita', v)}
                >
                  <SelectTrigger data-testid="select-periodicita">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="mensile">Mensile</SelectItem>
                    <SelectItem value="trimestrale">Trimestrale</SelectItem>
                    <SelectItem value="annuale">Annuale</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Canone (€) *</Label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.canone_importo}
                  onChange={(e) => updateFormData('canone_importo', parseFloat(e.target.value) || 0)}
                  data-testid="input-canone"
                />
              </div>
              <div className="space-y-2">
                <Label>Giorno Scadenza Rata (1-28) *</Label>
                <Input
                  type="number"
                  min="1"
                  max="28"
                  value={formData.giorno_scadenza}
                  onChange={(e) => updateFormData('giorno_scadenza', parseInt(e.target.value) || 5)}
                  data-testid="input-giorno-scadenza"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Deposito Cauzionale (€)</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={formData.deposito_importo}
                onChange={(e) => updateFormData('deposito_importo', parseFloat(e.target.value) || 0)}
                data-testid="input-deposito"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Note</Label>
              <Textarea
                value={formData.note}
                onChange={(e) => updateFormData('note', e.target.value)}
                placeholder="Note aggiuntive sul contratto..."
                rows={3}
              />
            </div>
          </div>
        );
      
      case 4: // Reminder
        return (
          <div className="space-y-6 max-w-2xl">
            <p className="text-slate-500">
              Configura quando ricevere le notifiche per questo contratto. 
              I valori rappresentano i giorni di anticipo/ritardo.
            </p>
            
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Scadenza Contratto (giorni prima)</Label>
                <div className="flex gap-2">
                  {formData.reminder_config.scadenza_contratto.map((v, i) => (
                    <Input
                      key={i}
                      type="number"
                      min="0"
                      value={v}
                      onChange={(e) => {
                        const newArr = [...formData.reminder_config.scadenza_contratto];
                        newArr[i] = parseInt(e.target.value) || 0;
                        updateFormData('reminder_config', {
                          ...formData.reminder_config,
                          scadenza_contratto: newArr
                        });
                      }}
                      className="w-24"
                    />
                  ))}
                </div>
                <p className="text-xs text-slate-500">Default: 365, 30, 1 giorni prima</p>
              </div>
              
              <div className="space-y-2">
                <Label>Rata Scaduta (giorni dopo)</Label>
                <div className="flex gap-2">
                  {formData.reminder_config.rata_scaduta.map((v, i) => (
                    <Input
                      key={i}
                      type="number"
                      min="0"
                      value={v}
                      onChange={(e) => {
                        const newArr = [...formData.reminder_config.rata_scaduta];
                        newArr[i] = parseInt(e.target.value) || 0;
                        updateFormData('reminder_config', {
                          ...formData.reminder_config,
                          rata_scaduta: newArr
                        });
                      }}
                      className="w-24"
                    />
                  ))}
                </div>
                <p className="text-xs text-slate-500">Default: 1, 7, 15 giorni dopo scadenza</p>
              </div>
              
              <div className="space-y-2">
                <Label>Documento in Scadenza (giorni prima)</Label>
                <div className="flex gap-2">
                  {formData.reminder_config.documento_scadenza.map((v, i) => (
                    <Input
                      key={i}
                      type="number"
                      min="0"
                      value={v}
                      onChange={(e) => {
                        const newArr = [...formData.reminder_config.documento_scadenza];
                        newArr[i] = parseInt(e.target.value) || 0;
                        updateFormData('reminder_config', {
                          ...formData.reminder_config,
                          documento_scadenza: newArr
                        });
                      }}
                      className="w-24"
                    />
                  ))}
                </div>
                <p className="text-xs text-slate-500">Default: 30, 7 giorni prima</p>
              </div>
            </div>
          </div>
        );
      
      case 5: // Conferma
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Riepilogo Contratto</CardTitle>
                <CardDescription>Verifica i dati prima della conferma</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-slate-500">Unità</p>
                    <p className="font-medium">{selectedUnita?.codice_unita || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Tipo</p>
                    <p className="font-medium">{selectedUnita?.tipo_immobile?.replace('_', ' ')}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Locatore</p>
                    <p className="font-medium">{selectedLocatore?.nome || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Affittuario</p>
                    <p className="font-medium">{selectedAffittuario?.nome || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Data Inizio</p>
                    <p className="font-medium">{formData.data_inizio}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Durata</p>
                    <p className="font-medium">{formData.durata_mesi} mesi</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Canone</p>
                    <p className="font-medium text-lg">€ {formData.canone_importo.toLocaleString('it-IT')} / {formData.periodicita}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Deposito</p>
                    <p className="font-medium">€ {(formData.deposito_importo || 0).toLocaleString('it-IT')}</p>
                  </div>
                </div>
                
                <div className="pt-4 border-t">
                  <p className="text-sm text-slate-500 mb-2">Rate generate automaticamente:</p>
                  <p className="font-medium">
                    {formData.periodicita === 'mensile' ? formData.durata_mesi :
                     formData.periodicita === 'trimestrale' ? Math.floor(formData.durata_mesi / 3) :
                     Math.floor(formData.durata_mesi / 12)} rate da € {formData.canone_importo.toLocaleString('it-IT')}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        );
      
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="contratto-wizard">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/contratti')}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold font-heading">Nuovo Contratto</h1>
          <p className="text-slate-500">Wizard creazione contratto di locazione</p>
        </div>
      </div>

      {/* Steps indicator */}
      <div className="flex items-center justify-between">
        {STEPS.map((step, index) => (
          <div key={step.id} className="flex items-center">
            <div 
              className={cn(
                "flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors",
                index < currentStep && "bg-primary border-primary text-primary-foreground",
                index === currentStep && "border-primary text-primary",
                index > currentStep && "border-slate-300 text-slate-400"
              )}
            >
              {index < currentStep ? (
                <Check className="w-5 h-5" />
              ) : (
                <step.icon className="w-5 h-5" />
              )}
            </div>
            <div className="hidden sm:block ml-2">
              <p className={cn(
                "text-sm font-medium",
                index === currentStep ? "text-primary" : "text-slate-500"
              )}>
                {step.title}
              </p>
            </div>
            {index < STEPS.length - 1 && (
              <div className={cn(
                "w-8 md:w-16 h-0.5 mx-2",
                index < currentStep ? "bg-primary" : "bg-slate-200"
              )} />
            )}
          </div>
        ))}
      </div>

      {/* Current step content */}
      <Card>
        <CardHeader>
          <CardTitle>{STEPS[currentStep].title}</CardTitle>
          <CardDescription>{STEPS[currentStep].description}</CardDescription>
        </CardHeader>
        <CardContent>
          {renderStepContent()}
        </CardContent>
      </Card>

      {/* Navigation buttons */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={prevStep}
          disabled={currentStep === 0}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Indietro
        </Button>
        
        {currentStep < STEPS.length - 1 ? (
          <Button onClick={nextStep} data-testid="wizard-next-btn">
            Avanti
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        ) : (
          <Button 
            onClick={handleSubmit} 
            disabled={submitting}
            data-testid="wizard-submit-btn"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creazione...
              </>
            ) : (
              <>
                <Check className="w-4 h-4 mr-2" />
                Crea Contratto
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}
