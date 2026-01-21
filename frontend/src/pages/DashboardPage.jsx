import React from 'react';
import { Link } from 'react-router-dom';
import { useDashboard } from '../../hooks';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Skeleton } from '../ui/skeleton';
import { 
  Building2, 
  Home, 
  FileText, 
  AlertTriangle,
  TrendingUp,
  Clock,
  Euro,
  MapPin,
  ChevronRight,
  ExternalLink
} from 'lucide-react';
import { cn } from '../../lib/utils';

function KPICard({ title, value, icon: Icon, trend, color = 'slate', link }) {
  const colorClasses = {
    slate: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    red: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    amber: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
    emerald: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300',
  };

  const Content = (
    <Card className="border-slate-200 dark:border-slate-800 hover:shadow-lg transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-slate-500 dark:text-slate-400 uppercase tracking-wide font-medium">
              {title}
            </p>
            <p className="text-3xl font-bold mt-2 font-heading">{value}</p>
            {trend && (
              <p className={cn("text-sm mt-1", trend > 0 ? "text-emerald-600" : "text-red-600")}>
                <TrendingUp className={cn("w-4 h-4 inline mr-1", trend < 0 && "rotate-180")} />
                {trend > 0 ? '+' : ''}{trend}%
              </p>
            )}
          </div>
          <div className={cn("p-3 rounded-lg", colorClasses[color])}>
            <Icon className="w-6 h-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  );

  if (link) {
    return <Link to={link} data-testid={`kpi-${title.toLowerCase().replace(/\s/g, '-')}`}>{Content}</Link>;
  }
  return <div data-testid={`kpi-${title.toLowerCase().replace(/\s/g, '-')}`}>{Content}</div>;
}

function ProblemList({ title, items, emptyMessage, renderItem, link }) {
  return (
    <Card className="border-slate-200 dark:border-slate-800">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-heading">{title}</CardTitle>
        {link && (
          <Link to={link}>
            <Button variant="ghost" size="sm" className="gap-1">
              Vedi tutti <ChevronRight className="w-4 h-4" />
            </Button>
          </Link>
        )}
      </CardHeader>
      <CardContent>
        {items?.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">{emptyMessage}</p>
        ) : (
          <div className="space-y-3">
            {items?.map((item, index) => renderItem(item, index))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { data, loading, refetch } = useDashboard();

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="border-slate-200">
              <CardContent className="p-6">
                <Skeleton className="h-4 w-24 mb-4" />
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const kpi = data?.kpi || {};

  return (
    <div className="space-y-6" data-testid="dashboard">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Dashboard</h1>
          <p className="text-slate-500">Panoramica problemi e situazione patrimonio</p>
        </div>
        <Button onClick={refetch} variant="outline" size="sm">
          Aggiorna
        </Button>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard 
          title="Immobili" 
          value={kpi.immobili || 0} 
          icon={Building2}
          link="/immobili"
        />
        <KPICard 
          title="Unità Locate" 
          value={`${kpi.unita_locate || 0}/${kpi.unita_totali || 0}`} 
          icon={Home}
          color="emerald"
        />
        <KPICard 
          title="Rate in Ritardo" 
          value={kpi.rate_in_ritardo || 0} 
          icon={Clock}
          color={kpi.rate_in_ritardo > 0 ? 'red' : 'slate'}
          link="/pagamenti"
        />
        <KPICard 
          title="Incassi Mese" 
          value={`€ ${(kpi.incassi_mese || 0).toLocaleString('it-IT')}`} 
          icon={Euro}
          color="emerald"
        />
      </div>

      {/* Alert Cards */}
      {(kpi.rate_in_ritardo > 0 || kpi.contratti_in_scadenza > 0 || kpi.eventi_critici_settimana > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {kpi.rate_in_ritardo > 0 && (
            <Card className="border-red-200 bg-red-50 dark:bg-red-950 dark:border-red-800">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="p-2 bg-red-100 dark:bg-red-900 rounded-lg">
                  <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <p className="font-medium text-red-700 dark:text-red-300">
                    {kpi.rate_in_ritardo} Rate in Ritardo
                  </p>
                  <p className="text-sm text-red-600 dark:text-red-400">
                    Totale: € {(kpi.insoluti_importo || 0).toLocaleString('it-IT')}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
          {kpi.contratti_in_scadenza > 0 && (
            <Card className="border-amber-200 bg-amber-50 dark:bg-amber-950 dark:border-amber-800">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="p-2 bg-amber-100 dark:bg-amber-900 rounded-lg">
                  <FileText className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <p className="font-medium text-amber-700 dark:text-amber-300">
                    {kpi.contratti_in_scadenza} Contratti in Scadenza
                  </p>
                  <p className="text-sm text-amber-600 dark:text-amber-400">
                    Nei prossimi 30 giorni
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
          {kpi.eventi_critici_settimana > 0 && (
            <Card className="border-red-200 bg-red-50 dark:bg-red-950 dark:border-red-800">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="p-2 bg-red-100 dark:bg-red-900 rounded-lg">
                  <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <p className="font-medium text-red-700 dark:text-red-300">
                    {kpi.eventi_critici_settimana} Eventi Critici
                  </p>
                  <p className="text-sm text-red-600 dark:text-red-400">
                    Negli ultimi 7 giorni
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Problems Lists */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Rate in Ritardo */}
        <ProblemList
          title="Rate in Ritardo"
          items={data?.rateRitardo}
          emptyMessage="Nessuna rata in ritardo"
          link="/pagamenti"
          renderItem={(rata, index) => (
            <div 
              key={index} 
              className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
            >
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{rata.affittuario_nome || 'N/A'}</p>
                <p className="text-sm text-slate-500">{rata.immobile_titolo}</p>
              </div>
              <div className="text-right ml-4">
                <p className="font-mono font-medium">€ {rata.importo?.toLocaleString('it-IT')}</p>
                <Badge variant="destructive" className="mt-1">
                  {rata.giorni_ritardo}gg ritardo
                </Badge>
              </div>
            </div>
          )}
        />

        {/* Contratti in Scadenza */}
        <ProblemList
          title="Contratti in Scadenza"
          items={data?.contrattiScadenza}
          emptyMessage="Nessun contratto in scadenza"
          link="/contratti"
          renderItem={(contratto, index) => (
            <div 
              key={index} 
              className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
            >
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{contratto.affittuario_nome || 'N/A'}</p>
                <p className="text-sm text-slate-500">{contratto.immobile_titolo}</p>
              </div>
              <div className="text-right ml-4">
                <p className="text-sm text-slate-500">Scade il</p>
                <Badge variant="outline" className="mt-1">
                  {contratto.giorni_alla_scadenza}gg
                </Badge>
              </div>
            </div>
          )}
        />

        {/* Eventi Critici */}
        <ProblemList
          title="Eventi Critici Recenti"
          items={data?.eventiCritici}
          emptyMessage="Nessun evento critico recente"
          link="/eventi-critici"
          renderItem={(evento, index) => (
            <div 
              key={index} 
              className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
            >
              <div className={cn(
                "w-2 h-2 rounded-full",
                evento.gravita === 'alta' ? 'bg-red-500' :
                evento.gravita === 'media' ? 'bg-amber-500' : 'bg-blue-500'
              )} />
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">
                  {evento.tipo?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </p>
                <p className="text-sm text-slate-500 truncate">
                  {evento.affittuario_nome} - {evento.immobile_titolo}
                </p>
              </div>
              <Badge variant={
                evento.gravita === 'alta' ? 'destructive' :
                evento.gravita === 'media' ? 'warning' : 'secondary'
              }>
                {evento.gravita}
              </Badge>
            </div>
          )}
        />

        {/* Quick Actions */}
        <Card className="border-slate-200 dark:border-slate-800">
          <CardHeader>
            <CardTitle className="text-lg font-heading">Azioni Rapide</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <Link to="/contratti/nuovo">
              <Button variant="outline" className="w-full justify-start gap-2">
                <FileText className="w-4 h-4" />
                Nuovo Contratto
              </Button>
            </Link>
            <Link to="/immobili/nuovo">
              <Button variant="outline" className="w-full justify-start gap-2">
                <Building2 className="w-4 h-4" />
                Nuovo Immobile
              </Button>
            </Link>
            <Link to="/soggetti/nuovo">
              <Button variant="outline" className="w-full justify-start gap-2">
                <ExternalLink className="w-4 h-4" />
                Nuovo Soggetto
              </Button>
            </Link>
            <Link to="/mappa">
              <Button variant="outline" className="w-full justify-start gap-2">
                <MapPin className="w-4 h-4" />
                Apri Mappa
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
