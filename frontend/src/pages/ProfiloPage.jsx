import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../stores';
import { useAuthStore } from '../stores';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { User, Mail, Shield, KeyRound, Save, Loader2, CheckCircle2 } from 'lucide-react';

const ruoloLabels = {
  supervisore: { label: 'Supervisore', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' },
  gestore: { label: 'Gestore', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
  lettura: { label: 'Sola lettura', color: 'bg-slate-100 text-slate-700 dark:bg-slate-900/30 dark:text-slate-400' },
};

export default function ProfiloPage() {
  const { user, updateUser } = useAuthStore();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');

  const fetchProfile = async () => {
    try {
      const res = await api.get('/auth/me');
      setProfile(res.data);
      setNome(res.data.nome);
      setEmail(res.data.email);
    } catch (err) {
      toast.error('Errore caricamento profilo');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProfile(); }, []);

  const handleSave = async () => {
    if (!nome.trim() || !email.trim()) {
      toast.error('Nome ed email sono obbligatori');
      return;
    }
    setSaving(true);
    try {
      const res = await api.put('/auth/me', { nome: nome.trim(), email: email.trim() });
      setProfile(res.data);
      updateUser({ nome: res.data.nome, email: res.data.email });
      toast.success('Profilo aggiornato');
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>;
  }
  if (!profile) {
    return <p className="text-red-500 p-8">Errore caricamento profilo</p>;
  }

  const ruoloInfo = ruoloLabels[profile.ruolo] || ruoloLabels.gestore;
  const dirty = nome !== profile.nome || email !== profile.email;

  return (
    <div className="max-w-3xl space-y-6" data-testid="profilo-page">
      <div>
        <h1 className="text-3xl font-bold font-heading flex items-center gap-2">
          <User className="w-8 h-8 text-slate-700" /> Profilo Utente
        </h1>
        <p className="text-slate-500">Gestisci i tuoi dati personali e le credenziali</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Dati anagrafici</CardTitle>
          <CardDescription>Aggiorna nome ed email associati al tuo account</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="nome">Nome completo</Label>
            <Input
              id="nome"
              value={nome}
              onChange={e => setNome(e.target.value)}
              data-testid="input-nome"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              data-testid="input-email"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            <Button
              onClick={handleSave}
              disabled={!dirty || saving}
              data-testid="btn-save-profile"
            >
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              Salva modifiche
            </Button>
            {!dirty && (
              <span className="text-sm text-slate-500 flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Tutto sincronizzato
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Informazioni account</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b">
            <div className="flex items-center gap-2 text-slate-500">
              <Shield className="w-4 h-4" /> Ruolo
            </div>
            <Badge variant="outline" className={ruoloInfo.color}>{ruoloInfo.label}</Badge>
          </div>
          <div className="flex items-center justify-between py-2 border-b">
            <div className="flex items-center gap-2 text-slate-500">
              <Mail className="w-4 h-4" /> Stato
            </div>
            <Badge variant={profile.attivo ? 'default' : 'destructive'}>
              {profile.attivo ? 'Attivo' : 'Disattivato'}
            </Badge>
          </div>
          {profile.last_login && (
            <div className="flex items-center justify-between py-2 border-b">
              <span className="text-slate-500">Ultimo accesso</span>
              <span className="text-sm">{new Date(profile.last_login).toLocaleString('it-IT')}</span>
            </div>
          )}
          <div className="flex items-center justify-between py-2">
            <span className="text-slate-500">User ID</span>
            <code className="text-xs text-slate-500">{profile.id}</code>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="w-5 h-5" /> Sicurezza
          </CardTitle>
          <CardDescription>Modifica la tua password di accesso</CardDescription>
        </CardHeader>
        <CardContent>
          <Link to="/cambio-password">
            <Button variant="outline" data-testid="btn-go-change-password">
              <KeyRound className="w-4 h-4 mr-2" /> Cambia password
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
