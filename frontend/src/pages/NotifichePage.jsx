import React, { useEffect, useState } from 'react';
import { api } from '../stores';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { 
  Bell, 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertTriangle,
  FileText,
  Euro,
  Calendar,
  RefreshCw,
  Trash2,
  CheckCheck,
  Play,
  Loader2,
  Mail,
  MailX
} from 'lucide-react';
import { cn } from '../lib/utils';

const TIPO_ICONS = {
  scadenza_contratto: Calendar,
  rata_ritardo: Euro,
  doc_scadenza: FileText,
  evento_critico: AlertTriangle,
  sistema: Bell
};

const STATO_COLORS = {
  pending: 'bg-yellow-100 text-yellow-800',
  sent: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  read: 'bg-slate-100 text-slate-600'
};

const STATO_ICONS = {
  pending: Clock,
  sent: CheckCircle,
  failed: XCircle,
  read: CheckCheck
};

function NotificaCard({ notifica, onRead, onDelete }) {
  const Icon = TIPO_ICONS[notifica.tipo] || Bell;
  const StatoIcon = STATO_ICONS[notifica.stato] || Clock;
  const isUnread = notifica.stato !== 'read';
  
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('it-IT', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <Card 
      className={cn(
        "transition-all hover:shadow-md",
        isUnread && "border-l-4 border-l-primary bg-primary/5"
      )}
      data-testid={`notifica-card-${notifica.id}`}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          <div className={cn(
            "p-2 rounded-full",
            notifica.tipo === 'evento_critico' ? "bg-red-100" :
            notifica.tipo === 'rata_ritardo' ? "bg-amber-100" :
            notifica.tipo === 'scadenza_contratto' ? "bg-blue-100" :
            "bg-slate-100"
          )}>
            <Icon className={cn(
              "w-5 h-5",
              notifica.tipo === 'evento_critico' ? "text-red-600" :
              notifica.tipo === 'rata_ritardo' ? "text-amber-600" :
              notifica.tipo === 'scadenza_contratto' ? "text-blue-600" :
              "text-slate-600"
            )} />
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <h3 className={cn(
                "font-medium text-slate-900",
                isUnread && "font-semibold"
              )}>
                {notifica.titolo}
              </h3>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Badge className={STATO_COLORS[notifica.stato]}>
                  <StatoIcon className="w-3 h-3 mr-1" />
                  {notifica.stato}
                </Badge>
              </div>
            </div>
            
            <p className="text-sm text-slate-600 mt-1 line-clamp-2">
              {notifica.messaggio}
            </p>
            
            <div className="flex items-center justify-between mt-3">
              <div className="flex items-center gap-4 text-xs text-slate-500">
                <span>{formatDate(notifica.created_at)}</span>
                {notifica.destinatario_email && (
                  <span className="flex items-center gap-1">
                    {notifica.stato === 'sent' ? (
                      <Mail className="w-3 h-3 text-green-500" />
                    ) : notifica.stato === 'failed' ? (
                      <MailX className="w-3 h-3 text-red-500" />
                    ) : (
                      <Mail className="w-3 h-3" />
                    )}
                    Email
                  </span>
                )}
                {notifica.tentativi > 0 && (
                  <span>Tentativi: {notifica.tentativi}/3</span>
                )}
              </div>
              
              <div className="flex items-center gap-1">
                {isUnread && (
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => onRead(notifica.id)}
                  >
                    <CheckCheck className="w-4 h-4 mr-1" />
                    Letta
                  </Button>
                )}
                <Button 
                  variant="ghost" 
                  size="sm"
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  onClick={() => onDelete(notifica.id)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            {notifica.last_error && (
              <div className="mt-2 p-2 bg-red-50 rounded text-xs text-red-600">
                <strong>Errore:</strong> {notifica.last_error}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function NotifichePage() {
  const [notifiche, setNotifiche] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [activeTab, setActiveTab] = useState('tutte');
  const [userRole, setUserRole] = useState('');

  const fetchNotifiche = async (stato = null) => {
    setLoading(true);
    try {
      const params = { limit: 100 };
      if (stato && stato !== 'tutte') {
        params.stato = stato;
      }
      const [notificheRes, statsRes] = await Promise.all([
        api.get('/notifiche', { params }),
        api.get('/notifiche/stats')
      ]);
      setNotifiche(notificheRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Errore nel caricamento notifiche');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifiche(activeTab);
    // Get user role from stored auth
    try {
      const auth = JSON.parse(localStorage.getItem('estatewise-auth') || '{}');
      setUserRole(auth.state?.user?.ruolo || '');
    } catch (e) {}
  }, [activeTab]);

  const handleMarkAsRead = async (id) => {
    try {
      await api.post(`/notifiche/${id}/read`);
      toast.success('Notifica segnata come letta');
      fetchNotifiche(activeTab);
    } catch (error) {
      toast.error('Errore');
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await api.post('/notifiche/read-all');
      toast.success('Tutte le notifiche segnate come lette');
      fetchNotifiche(activeTab);
    } catch (error) {
      toast.error('Errore');
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/notifiche/${id}`);
      toast.success('Notifica eliminata');
      fetchNotifiche(activeTab);
    } catch (error) {
      toast.error('Errore');
    }
  };

  const handleTriggerCheck = async (checkType = 'all') => {
    setTriggering(true);
    try {
      const response = await api.post('/notifiche/trigger-check', null, {
        params: { check_type: checkType }
      });
      toast.success(response.data.message);
      // Refresh after a delay to see new notifications
      setTimeout(() => fetchNotifiche(activeTab), 2000);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore nel trigger');
    } finally {
      setTriggering(false);
    }
  };

  const handleRetryFailed = async () => {
    try {
      const response = await api.post('/notifiche/retry-failed');
      toast.success(response.data.message);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore');
    }
  };

  const unreadCount = stats?.by_stato?.pending + stats?.by_stato?.sent - (stats?.by_stato?.read || 0);

  return (
    <div className="space-y-6" data-testid="notifiche-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-heading flex items-center gap-2">
            <Bell className="w-6 h-6" />
            Notifiche
          </h1>
          <p className="text-slate-500">
            {stats?.total || 0} notifiche totali • {unreadCount || 0} non lette
          </p>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => fetchNotifiche(activeTab)}
            disabled={loading}
          >
            <RefreshCw className={cn("w-4 h-4 mr-2", loading && "animate-spin")} />
            Aggiorna
          </Button>
          
          {unreadCount > 0 && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleMarkAllAsRead}
            >
              <CheckCheck className="w-4 h-4 mr-2" />
              Segna tutte lette
            </Button>
          )}
          
          {userRole === 'supervisore' && (
            <>
              <Button 
                size="sm" 
                onClick={() => handleTriggerCheck('all')}
                disabled={triggering}
                data-testid="trigger-check-btn"
              >
                {triggering ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                Esegui Controlli
              </Button>
              
              {stats?.by_stato?.failed > 0 && (
                <Button 
                  variant="destructive" 
                  size="sm" 
                  onClick={handleRetryFailed}
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Riprova Fallite ({stats.by_stato.failed})
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-full">
                <Clock className="w-5 h-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.by_stato?.pending || 0}</p>
                <p className="text-sm text-slate-500">In Attesa</p>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-full">
                <CheckCircle className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.by_stato?.sent || 0}</p>
                <p className="text-sm text-slate-500">Inviate</p>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-full">
                <XCircle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.by_stato?.failed || 0}</p>
                <p className="text-sm text-slate-500">Fallite</p>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 bg-slate-100 rounded-full">
                <CheckCheck className="w-5 h-5 text-slate-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.by_stato?.read || 0}</p>
                <p className="text-sm text-slate-500">Lette</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs & List */}
      <Card>
        <CardHeader className="pb-2">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v)}>
            <TabsList>
              <TabsTrigger value="tutte">
                Tutte
                {stats?.total > 0 && (
                  <Badge variant="secondary" className="ml-2">{stats.total}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="pending">
                In Attesa
                {stats?.by_stato?.pending > 0 && (
                  <Badge className="ml-2 bg-yellow-500">{stats.by_stato.pending}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="failed">
                Fallite
                {stats?.by_stato?.failed > 0 && (
                  <Badge className="ml-2 bg-red-500">{stats.by_stato.failed}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="read">Lette</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
            </div>
          ) : notifiche.length === 0 ? (
            <div className="text-center py-12">
              <Bell className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">Nessuna notifica</p>
            </div>
          ) : (
            <div className="space-y-3 mt-4">
              {notifiche.map(notifica => (
                <NotificaCard
                  key={notifica.id}
                  notifica={notifica}
                  onRead={handleMarkAsRead}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tipo Stats */}
      {stats?.by_tipo && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Notifiche per Tipo</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {Object.entries(stats.by_tipo).map(([tipo, count]) => {
                const Icon = TIPO_ICONS[tipo] || Bell;
                return (
                  <div key={tipo} className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg">
                    <Icon className="w-4 h-4 text-slate-500" />
                    <div>
                      <p className="font-medium">{count}</p>
                      <p className="text-xs text-slate-500 capitalize">{tipo.replace('_', ' ')}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
