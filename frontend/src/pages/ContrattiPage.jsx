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
  FileText,
  Eye,
  Edit,
  Calendar,
  Euro,
  User,
  Building2
} from 'lucide-react';
import { cn } from '../lib/utils';

const statoColors = {
  attivo: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  scaduto: 'bg-amber-100 text-amber-700 border-amber-200',
  chiuso: 'bg-slate-100 text-slate-700 border-slate-200',
  contestato: 'bg-red-100 text-red-700 border-red-200',
};

export default function ContrattiPage() {
  const [search, setSearch] = useState('');
  const [stato, setStato] = useState('');
  const navigate = useNavigate();
  
  const queryParams = new URLSearchParams();
  if (search) queryParams.set('search', search);
  if (stato) queryParams.set('stato', stato);
  
  const { data: contratti, loading } = useFetch(`/contratti?${queryParams.toString()}`);

  return (
    <div className="space-y-6" data-testid="contratti-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-heading">Contratti</h1>
          <p className="text-slate-500">Gestisci i contratti di locazione</p>
        </div>
        
        <Link to="/contratti/nuovo">
          <Button className="gap-2" data-testid="new-contratto-btn">
            <Plus className="w-4 h-4" />
            Nuovo Contratto
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
                placeholder="Cerca per codice contratto..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={stato || 'all'} onValueChange={(v) => setStato(v === 'all' ? '' : v)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Tutti gli stati" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tutti gli stati</SelectItem>
                <SelectItem value="attivo">Attivo</SelectItem>
                <SelectItem value="scaduto">Scaduto</SelectItem>
                <SelectItem value="chiuso">Chiuso</SelectItem>
                <SelectItem value="contestato">Contestato</SelectItem>
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
          ) : contratti?.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">Nessun contratto trovato</p>
              <Link to="/contratti/nuovo">
                <Button className="mt-4">Crea il primo contratto</Button>
              </Link>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Codice</TableHead>
                  <TableHead>Affittuario</TableHead>
                  <TableHead>Immobile/Unità</TableHead>
                  <TableHead className="text-right">Canone</TableHead>
                  <TableHead>Scadenza</TableHead>
                  <TableHead>Stato</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {contratti?.map((contratto) => (
                  <TableRow key={contratto.id} className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800">
                    <TableCell className="font-mono font-medium text-sm">
                      {contratto.codice_contratto}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-slate-400" />
                        <span>{contratto.affittuario_nome || 'N/A'}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-slate-400" />
                        <div>
                          <p className="font-medium">{contratto.immobile_titolo}</p>
                          <p className="text-sm text-slate-500">{contratto.unita_codice}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      € {contratto.canone_importo?.toLocaleString('it-IT')}
                      <span className="text-slate-400 text-xs">/{contratto.periodicita?.charAt(0)}</span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-slate-400" />
                        <span>{contratto.data_scadenza}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={cn("capitalize", statoColors[contratto.stato])}>
                        {contratto.stato}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => navigate(`/contratti/${contratto.id}`)}>
                            <Eye className="w-4 h-4 mr-2" />
                            Visualizza
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => navigate(`/contratti/${contratto.id}/modifica`)}>
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
