import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useFetch, useApi } from '../../hooks';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Skeleton } from '../ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { 
  Plus, 
  Search, 
  MoreHorizontal, 
  Building2, 
  MapPin,
  Eye,
  Edit,
  Trash2,
  Home,
  FileText
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';

export default function ImmobiliPage() {
  const [search, setSearch] = useState('');
  const { data: immobili, loading, refetch } = useFetch(`/immobili?search=${search}`);
  const { request } = useApi();
  const navigate = useNavigate();

  const handleDelete = async (id) => {
    if (!window.confirm('Sei sicuro di voler eliminare questo immobile?')) return;
    
    try {
      await request('DELETE', `/immobili/${id}`);
      toast.success('Immobile eliminato');
      refetch();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore durante l\'eliminazione');
    }
  };

  return (
    <div className="space-y-6" data-testid="immobili-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-heading">Immobili</h1>
          <p className="text-slate-500">Gestisci il patrimonio immobiliare</p>
        </div>
        
        <Link to="/immobili/nuovo">
          <Button className="gap-2" data-testid="new-immobile-btn">
            <Plus className="w-4 h-4" />
            Nuovo Immobile
          </Button>
        </Link>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="py-4">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Cerca per codice, titolo o indirizzo..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
              data-testid="search-immobili"
            />
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
          ) : immobili?.length === 0 ? (
            <div className="p-12 text-center">
              <Building2 className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">Nessun immobile trovato</p>
              <Link to="/immobili/nuovo">
                <Button className="mt-4">Aggiungi il primo immobile</Button>
              </Link>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Codice</TableHead>
                  <TableHead>Titolo</TableHead>
                  <TableHead>Indirizzo</TableHead>
                  <TableHead className="text-center">Unità</TableHead>
                  <TableHead className="text-center">Contratti</TableHead>
                  <TableHead className="text-center">Mappa</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {immobili?.map((imm) => (
                  <TableRow key={imm.id} className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800">
                    <TableCell className="font-mono font-medium">{imm.codice}</TableCell>
                    <TableCell>
                      <Link to={`/immobili/${imm.id}`} className="hover:underline font-medium">
                        {imm.titolo}
                      </Link>
                    </TableCell>
                    <TableCell className="text-slate-500 max-w-xs truncate">
                      {imm.indirizzo}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant="outline" className="gap-1">
                        <Home className="w-3 h-3" />
                        {imm.unita_count}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant={imm.contratti_attivi > 0 ? "default" : "secondary"} className="gap-1">
                        <FileText className="w-3 h-3" />
                        {imm.contratti_attivi}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      {imm.lat && imm.lon ? (
                        <Badge variant="outline" className="gap-1 text-emerald-600">
                          <MapPin className="w-3 h-3" />
                          OK
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="gap-1 text-slate-400">
                          <MapPin className="w-3 h-3" />
                          N/A
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => navigate(`/immobili/${imm.id}`)}>
                            <Eye className="w-4 h-4 mr-2" />
                            Visualizza
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => navigate(`/immobili/${imm.id}/modifica`)}>
                            <Edit className="w-4 h-4 mr-2" />
                            Modifica
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => handleDelete(imm.id)}
                            className="text-red-600"
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Elimina
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
