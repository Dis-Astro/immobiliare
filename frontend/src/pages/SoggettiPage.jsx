import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useFetch, useApi } from '../hooks';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { 
  Plus, 
  Search, 
  MoreHorizontal, 
  Users,
  Eye,
  Edit,
  Star,
  Building,
  User
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

export default function SoggettiPage() {
  const [search, setSearch] = useState('');
  const [tipo, setTipo] = useState('');
  const navigate = useNavigate();
  
  const queryParams = new URLSearchParams();
  if (search) queryParams.set('search', search);
  if (tipo) queryParams.set('tipo', tipo);
  
  const { data: soggetti, loading, refetch } = useFetch(`/soggetti?${queryParams.toString()}`);
  const { request } = useApi();

  const handleDelete = async (id) => {
    if (!window.confirm('Sei sicuro di voler eliminare questo soggetto?')) return;
    
    try {
      await request('DELETE', `/soggetti/${id}`);
      toast.success('Soggetto eliminato');
      refetch();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore durante l\'eliminazione');
    }
  };

  const renderRating = (rating) => {
    if (!rating) return <span className="text-slate-400">N/A</span>;
    
    return (
      <div className="flex items-center gap-1">
        {[...Array(5)].map((_, i) => (
          <Star 
            key={i} 
            className={cn(
              "w-3 h-3",
              i < Math.round(rating) ? "fill-amber-400 text-amber-400" : "text-slate-300"
            )} 
          />
        ))}
        <span className="text-sm text-slate-500 ml-1">({rating.toFixed(1)})</span>
      </div>
    );
  };

  return (
    <div className="space-y-6" data-testid="soggetti-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-heading">Soggetti</h1>
          <p className="text-slate-500">Gestisci locatori e affittuari</p>
        </div>
        
        <Link to="/soggetti/nuovo">
          <Button className="gap-2" data-testid="new-soggetto-btn">
            <Plus className="w-4 h-4" />
            Nuovo Soggetto
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Cerca per nome, CF, P.IVA o email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={tipo || 'all'} onValueChange={(v) => setTipo(v === 'all' ? '' : v)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Tutti i tipi" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tutti i tipi</SelectItem>
                <SelectItem value="persona">Persona Fisica</SelectItem>
                <SelectItem value="azienda">Azienda</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : soggetti?.length === 0 ? (
            <div className="p-12 text-center">
              <Users className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">Nessun soggetto trovato</p>
              <Link to="/soggetti/nuovo">
                <Button className="mt-4">Aggiungi il primo soggetto</Button>
              </Link>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome/Ragione Sociale</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>CF/P.IVA</TableHead>
                  <TableHead>Contatto</TableHead>
                  <TableHead className="text-center">Contratti</TableHead>
                  <TableHead>Rating</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {soggetti?.map((soggetto) => (
                  <TableRow key={soggetto.id} className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800">
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "w-9 h-9 rounded-full flex items-center justify-center",
                          soggetto.tipo === 'azienda' ? "bg-blue-100" : "bg-slate-100"
                        )}>
                          {soggetto.tipo === 'azienda' ? (
                            <Building className="w-4 h-4 text-blue-600" />
                          ) : (
                            <User className="w-4 h-4 text-slate-600" />
                          )}
                        </div>
                        <Link to={`/soggetti/${soggetto.id}`} className="hover:underline font-medium">
                          {soggetto.nome}
                        </Link>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {soggetto.tipo}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {soggetto.cf || soggetto.piva || '-'}
                    </TableCell>
                    <TableCell className="text-slate-500">
                      {soggetto.email || soggetto.telefono || '-'}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant="secondary">{soggetto.contratti_count}</Badge>
                    </TableCell>
                    <TableCell>
                      {renderRating(soggetto.rating_medio)}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => navigate(`/soggetti/${soggetto.id}`)}>
                            <Eye className="w-4 h-4 mr-2" />
                            Visualizza
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => navigate(`/soggetti/${soggetto.id}/modifica`)}>
                            <Edit className="w-4 h-4 mr-2" />
                            Modifica
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
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
