import React, { useState } from 'react';
import { useFetch, useApi } from '../hooks';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Skeleton } from '../components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Users,
  Plus,
  Shield,
  UserCog,
  User,
  ToggleLeft,
  ToggleRight,
  Key,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

const roleLabels = {
  supervisore: { label: 'Supervisore', color: 'bg-purple-100 text-purple-700' },
  gestore: { label: 'Gestore', color: 'bg-blue-100 text-blue-700' },
  lettura: { label: 'Lettura', color: 'bg-slate-100 text-slate-700' },
};

export default function UtentiPage() {
  const { request, loading: saving } = useApi();
  const { data: users, loading, refetch } = useFetch('/users');
  const [open, setOpen] = useState(false);
  const [editUser, setEditUser] = useState(null);
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    password: '',
    ruolo: 'gestore',
  });

  const resetForm = () => {
    setFormData({ nome: '', email: '', password: '', ruolo: 'gestore' });
    setEditUser(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.nome || !formData.email) {
      toast.error('Nome ed email obbligatori');
      return;
    }
    if (!editUser && !formData.password) {
      toast.error('Password obbligatoria per nuovi utenti');
      return;
    }
    try {
      if (editUser) {
        const payload = { nome: formData.nome, email: formData.email, ruolo: formData.ruolo };
        if (formData.password) payload.password = formData.password;
        await request('PUT', `/users/${editUser.id}`, payload);
        toast.success('Utente aggiornato');
      } else {
        await request('POST', '/users', formData);
        toast.success('Utente creato');
      }
      setOpen(false);
      resetForm();
      refetch();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore');
    }
  };

  const handleToggleActive = async (user) => {
    if (user.attivo) {
      await request('DELETE', `/users/${user.id}`);
      toast.success('Utente disattivato');
    } else {
      await request('PUT', `/users/${user.id}`, { attivo: true });
      toast.success('Utente riattivato');
    }
    refetch();
  };

  const openEdit = (user) => {
    setEditUser(user);
    setFormData({ nome: user.nome, email: user.email, password: '', ruolo: user.ruolo });
    setOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Utenti</h1>
          <p className="text-slate-500">Gestisci gli utenti della piattaforma</p>
        </div>
        <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) resetForm(); }}>
          <DialogTrigger asChild>
            <Button onClick={resetForm}>
              <Plus className="w-4 h-4 mr-2" />
              Nuovo Utente
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>{editUser ? 'Modifica Utente' : 'Nuovo Utente'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label>Nome *</Label>
                <Input
                  value={formData.nome}
                  onChange={(e) => setFormData(p => ({ ...p, nome: e.target.value }))}
                  placeholder="Nome e cognome"
                />
              </div>
              <div className="space-y-2">
                <Label>Email *</Label>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(p => ({ ...p, email: e.target.value }))}
                  placeholder="email@esempio.it"
                />
              </div>
              <div className="space-y-2">
                <Label>{editUser ? 'Nuova Password (lascia vuoto per invariata)' : 'Password *'}</Label>
                <Input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData(p => ({ ...p, password: e.target.value }))}
                  placeholder="min. 8 caratteri"
                />
              </div>
              <div className="space-y-2">
                <Label>Ruolo</Label>
                <Select
                  value={formData.ruolo}
                  onValueChange={(v) => setFormData(p => ({ ...p, ruolo: v }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="supervisore">Supervisore</SelectItem>
                    <SelectItem value="gestore">Gestore</SelectItem>
                    <SelectItem value="lettura">Lettura</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <Button type="button" variant="outline" onClick={() => { setOpen(false); resetForm(); }}>
                  Annulla
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving ? 'Salvataggio...' : editUser ? 'Salva Modifiche' : 'Crea Utente'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : users?.length === 0 ? (
            <div className="p-12 text-center">
              <Users className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">Nessun utente trovato</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Ruolo</TableHead>
                  <TableHead>Stato</TableHead>
                  <TableHead>Ultimo Accesso</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users?.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        {u.ruolo === 'supervisore' ? (
                          <Shield className="w-4 h-4 text-purple-500" />
                        ) : u.ruolo === 'gestore' ? (
                          <UserCog className="w-4 h-4 text-blue-500" />
                        ) : (
                          <User className="w-4 h-4 text-slate-500" />
                        )}
                        {u.nome}
                      </div>
                    </TableCell>
                    <TableCell className="text-slate-500">{u.email}</TableCell>
                    <TableCell>
                      <Badge className={cn("capitalize", roleLabels[u.ruolo]?.color)}>
                        {roleLabels[u.ruolo]?.label || u.ruolo}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={u.attivo ? 'default' : 'secondary'}>
                        {u.attivo ? 'Attivo' : 'Disattivato'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-slate-500">
                      {u.last_login ? new Date(u.last_login).toLocaleDateString('it-IT') : 'Mai'}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button size="sm" variant="ghost" onClick={() => openEdit(u)}>
                          <UserCog className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleToggleActive(u)}
                        >
                          {u.attivo ? (
                            <ToggleRight className="w-4 h-4 text-green-500" />
                          ) : (
                            <ToggleLeft className="w-4 h-4 text-slate-400" />
                          )}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
