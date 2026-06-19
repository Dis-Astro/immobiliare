import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores';
import { useTheme, useNotifications } from '../hooks';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { ScrollArea } from './ui/scroll-area';
import { Badge } from './ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import {
  Building2,
  LayoutDashboard,
  Map,
  Home,
  FileText,
  Users,
  CreditCard,
  Bell,
  Settings,
  LogOut,
  Search,
  Sun,
  Moon,
  Menu,
  ChevronRight,
  AlertTriangle,
  FileWarning,
  Wrench,
  ClipboardList,
  BarChart3,
  Shield,
  Sparkles,
  Zap
} from 'lucide-react';
import { cn } from '../lib/utils';

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/', roles: ['supervisore', 'gestore', 'lettura'] },
  { icon: Map, label: 'Mappa', path: '/mappa', roles: ['supervisore', 'gestore', 'lettura'] },
  { icon: Home, label: 'Immobili', path: '/immobili', roles: ['supervisore', 'gestore', 'lettura'] },
  { icon: FileText, label: 'Contratti', path: '/contratti', roles: ['supervisore', 'gestore', 'lettura'] },
  { icon: FileText, label: 'Modelli Contratto', path: '/modelli-contratto', roles: ['supervisore', 'gestore'] },
  { icon: Users, label: 'Soggetti', path: '/soggetti', roles: ['supervisore', 'gestore', 'lettura'] },
  { icon: CreditCard, label: 'Pagamenti', path: '/pagamenti', roles: ['supervisore', 'gestore', 'lettura'] },
  { icon: AlertTriangle, label: 'Eventi Critici', path: '/eventi-critici', roles: ['supervisore', 'gestore', 'lettura'] },
  { icon: ClipboardList, label: 'Verbali', path: '/verbali', roles: ['supervisore', 'gestore', 'lettura'] },
  { icon: FileWarning, label: 'Documenti', path: '/documenti', roles: ['supervisore', 'gestore', 'lettura'] },
  { icon: Zap, label: 'APE', path: '/ape', roles: ['supervisore', 'gestore', 'lettura'] },
  { icon: Wrench, label: 'Manutenzione', path: '/manutenzione', roles: ['supervisore', 'gestore', 'lettura'] },
  { icon: Sparkles, label: 'Assistente AI', path: '/ai', roles: ['supervisore', 'gestore', 'lettura'] },
  { icon: BarChart3, label: 'Report', path: '/report', roles: ['supervisore', 'gestore'] },
  { icon: Shield, label: 'Audit Log', path: '/audit', roles: ['supervisore'] },
  { icon: Settings, label: 'Impostazioni', path: '/impostazioni', roles: ['supervisore'] },
];

export function Sidebar({ open, onClose }) {
  const location = useLocation();
  const { user } = useAuthStore();
  
  const filteredNav = navItems.filter(item => 
    item.roles.includes(user?.ruolo)
  );

  return (
    <aside 
      className={cn(
        "fixed left-0 top-0 z-40 h-screen bg-slate-900 text-white transition-transform duration-300",
        "w-64 flex flex-col",
        open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}
    >
      <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-800">
        <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
          <Building2 className="w-6 h-6 text-slate-900" />
        </div>
        <div>
          <h1 className="font-bold text-lg font-heading">EstateWise</h1>
          <p className="text-xs text-slate-400">Gestione Immobili</p>
        </div>
      </div>

      <ScrollArea className="flex-1 px-3 py-4">
        <nav className="space-y-1">
          {filteredNav.map((item) => {
            const isActive = location.pathname === item.path || 
              (item.path !== '/' && location.pathname.startsWith(item.path));
            
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors",
                  isActive 
                    ? "bg-white text-slate-900 font-medium" 
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                )}
                data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
              >
                <item.icon className="w-5 h-5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </ScrollArea>

      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-slate-700 rounded-full flex items-center justify-center text-sm font-medium">
            {user?.nome?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.nome}</p>
            <p className="text-xs text-slate-400 capitalize">{user?.ruolo}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

export function Header({ onMenuClick }) {
  const { user, logout } = useAuthStore();
  const { theme, toggleTheme } = useTheme();
  const { unreadCount } = useNotifications();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Generate breadcrumb
  const pathSegments = location.pathname.split('/').filter(Boolean);
  const breadcrumbs = pathSegments.map((segment, index) => ({
    label: segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' '),
    path: '/' + pathSegments.slice(0, index + 1).join('/')
  }));

  return (
    <header className="sticky top-0 z-30 h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
      <div className="flex items-center justify-between h-full px-4 lg:px-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={onMenuClick}
          >
            <Menu className="w-5 h-5" />
          </Button>

          {/* Breadcrumb */}
          <nav className="hidden sm:flex items-center gap-1 text-sm">
            <Link to="/" className="text-slate-500 hover:text-slate-900 dark:hover:text-white">
              Home
            </Link>
            {breadcrumbs.map((crumb, index) => (
              <React.Fragment key={crumb.path}>
                <ChevronRight className="w-4 h-4 text-slate-400" />
                {index === breadcrumbs.length - 1 ? (
                  <span className="font-medium text-slate-900 dark:text-white">
                    {crumb.label}
                  </span>
                ) : (
                  <Link 
                    to={crumb.path}
                    className="text-slate-500 hover:text-slate-900 dark:hover:text-white"
                  >
                    {crumb.label}
                  </Link>
                )}
              </React.Fragment>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          {/* Global Search */}
          <div className="hidden md:block relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Cerca..."
              className="pl-9 bg-slate-50 dark:bg-slate-800 border-0"
              data-testid="global-search-input"
            />
          </div>

          {/* Theme Toggle */}
          <Button variant="ghost" size="icon" onClick={toggleTheme}>
            {theme === 'light' ? (
              <Moon className="w-5 h-5" />
            ) : (
              <Sun className="w-5 h-5" />
            )}
          </Button>

          {/* Notifications */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="relative" data-testid="notifications-btn">
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <Badge className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center bg-red-500">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <DropdownMenuLabel>Notifiche</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {unreadCount === 0 ? (
                <div className="p-4 text-center text-sm text-slate-500">
                  Nessuna nuova notifica
                </div>
              ) : (
                <div className="max-h-64 overflow-auto">
                  <DropdownMenuItem>
                    <Link to="/notifiche" className="w-full">
                      Vedi tutte le notifiche ({unreadCount})
                    </Link>
                  </DropdownMenuItem>
                </div>
              )}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="gap-2" data-testid="user-menu-btn">
                <div className="w-8 h-8 bg-slate-200 dark:bg-slate-700 rounded-full flex items-center justify-center text-sm font-medium">
                  {user?.nome?.charAt(0).toUpperCase() || 'U'}
                </div>
                <span className="hidden sm:inline">{user?.nome}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>
                <div>
                  <p>{user?.nome}</p>
                  <p className="text-xs text-slate-500 font-normal">{user?.email}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate('/profilo')}>
                Profilo
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate('/cambio-password')}>
                Cambia Password
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-red-600">
                <LogOut className="w-4 h-4 mr-2" />
                Esci
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="lg:pl-64">
        <Header onMenuClick={() => setSidebarOpen(true)} />
        <main className="p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
