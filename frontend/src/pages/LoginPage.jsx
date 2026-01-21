import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Building2, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const login = useAuthStore((state) => state.login);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const user = await login(email, password);
      toast.success(`Benvenuto, ${user.nome}!`);
      
      if (user.must_change_password) {
        navigate('/cambio-password');
      } else {
        navigate('/');
      }
    } catch (err) {
      const message = err.response?.data?.detail || 'Errore di autenticazione';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-slate-900 dark:bg-white rounded-xl mb-4">
            <Building2 className="w-8 h-8 text-white dark:text-slate-900" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white font-heading">
            EstateWise
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mt-2">
            Gestione Affitti Immobiliari
          </p>
        </div>

        <Card className="border-slate-200 dark:border-slate-800">
          <CardHeader>
            <CardTitle>Accedi</CardTitle>
            <CardDescription>
              Inserisci le tue credenziali per accedere
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="nome@azienda.it"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  data-testid="login-email-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    data-testid="login-password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <Button 
                type="submit" 
                className="w-full bg-slate-900 hover:bg-slate-800 text-white"
                disabled={loading}
                data-testid="login-submit-btn"
              >
                {loading ? 'Accesso in corso...' : 'Accedi'}
              </Button>
            </form>

            <div className="mt-6 p-4 bg-slate-100 dark:bg-slate-800 rounded-lg">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium mb-2">
                CREDENZIALI DEMO
              </p>
              <p className="text-sm text-slate-700 dark:text-slate-300 font-mono">
                admin@estatewise.it / admin123
              </p>
            </div>
          </CardContent>
        </Card>

        <p className="text-center text-sm text-slate-500 mt-6">
          EstateWise v1.0 - Gestione Patrimonio Immobiliare
        </p>
      </div>
    </div>
  );
}
