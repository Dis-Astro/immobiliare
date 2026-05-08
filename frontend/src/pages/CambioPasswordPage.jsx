import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../stores';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { KeyRound, Eye, EyeOff, Loader2, ArrowLeft, ShieldCheck } from 'lucide-react';

export default function CambioPasswordPage() {
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [saving, setSaving] = useState(false);

  const validate = () => {
    if (!currentPassword) return 'Inserisci la password attuale';
    if (newPassword.length < 8) return 'La nuova password deve avere almeno 8 caratteri';
    if (newPassword === currentPassword) return 'La nuova password deve essere diversa da quella attuale';
    if (newPassword !== confirmPassword) return 'La conferma password non corrisponde';
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const err = validate();
    if (err) {
      toast.error(err);
      return;
    }

    setSaving(true);
    try {
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success('Password aggiornata con successo');
      navigate('/profilo');
    } catch (err) {
      toast.error('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const PasswordStrength = ({ value }) => {
    const checks = [
      { label: '8+ caratteri', ok: value.length >= 8 },
      { label: 'Maiuscola', ok: /[A-Z]/.test(value) },
      { label: 'Numero', ok: /[0-9]/.test(value) },
      { label: 'Carattere speciale', ok: /[^A-Za-z0-9]/.test(value) },
    ];
    return (
      <div className="flex flex-wrap gap-2 text-xs mt-2">
        {checks.map(c => (
          <span
            key={c.label}
            className={`px-2 py-0.5 rounded-full border ${
              c.ok
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800'
                : 'bg-slate-50 text-slate-500 border-slate-200 dark:bg-slate-900 dark:border-slate-700'
            }`}
          >
            {c.ok ? '✓' : '○'} {c.label}
          </span>
        ))}
      </div>
    );
  };

  return (
    <div className="max-w-xl space-y-6" data-testid="cambio-password-page">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold font-heading flex items-center gap-2">
            <KeyRound className="w-8 h-8 text-slate-700" /> Cambio Password
          </h1>
          <p className="text-slate-500">Scegli una nuova password sicura</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-600" /> Aggiorna credenziali
          </CardTitle>
          <CardDescription>
            Per modificare la password, conferma quella attuale e scegline una nuova.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="current">Password attuale</Label>
              <div className="relative">
                <Input
                  id="current"
                  type={showCurrent ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={e => setCurrentPassword(e.target.value)}
                  autoComplete="current-password"
                  data-testid="input-current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrent(!showCurrent)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  tabIndex={-1}
                >
                  {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="new">Nuova password</Label>
              <div className="relative">
                <Input
                  id="new"
                  type={showNew ? 'text' : 'password'}
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                  data-testid="input-new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowNew(!showNew)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  tabIndex={-1}
                >
                  {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {newPassword && <PasswordStrength value={newPassword} />}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm">Conferma nuova password</Label>
              <Input
                id="confirm"
                type={showNew ? 'text' : 'password'}
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                data-testid="input-confirm-password"
              />
              {confirmPassword && newPassword !== confirmPassword && (
                <p className="text-xs text-red-500">Le password non corrispondono</p>
              )}
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="outline" onClick={() => navigate('/profilo')}>
                Annulla
              </Button>
              <Button type="submit" disabled={saving} data-testid="btn-submit-password">
                {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <KeyRound className="w-4 h-4 mr-2" />}
                Aggiorna password
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
