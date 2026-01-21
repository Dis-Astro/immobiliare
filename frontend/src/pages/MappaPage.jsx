import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { useFetch } from '../../hooks';
import { api } from '../../stores';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Skeleton } from '../ui/skeleton';
import { 
  Filter,
  Maximize2,
  RefreshCw,
  Building2,
  Users,
  AlertTriangle,
  ExternalLink
} from 'lucide-react';
import { cn } from '../../lib/utils';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet default marker icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom colored markers
const createColoredIcon = (color) => {
  const colors = {
    rosso: '#EF4444',
    giallo: '#F59E0B',
    verde: '#10B981',
    grigio: '#6B7280'
  };
  
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        width: 24px;
        height: 24px;
        background: ${colors[color] || colors.grigio};
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      "></div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24]
  });
};

// Component to fit bounds
function FitBounds({ markers }) {
  const map = useMap();
  
  useEffect(() => {
    if (markers && markers.length > 0) {
      const bounds = L.latLngBounds(markers.map(m => [m.lat, m.lon]));
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
    } else if (markers && markers.length === 1) {
      map.setView([markers[0].lat, markers[0].lon], 15);
    }
  }, [markers, map]);
  
  return null;
}

function MarkerPopup({ marker }) {
  const { immobile, problems, status } = marker;
  
  return (
    <div className="min-w-[250px]">
      <div className="flex items-start gap-3 mb-3">
        {immobile.foto_url ? (
          <img 
            src={immobile.foto_url} 
            alt={immobile.titolo}
            className="w-16 h-16 rounded-lg object-cover"
          />
        ) : (
          <div className="w-16 h-16 bg-slate-200 rounded-lg flex items-center justify-center">
            <Building2 className="w-6 h-6 text-slate-400" />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-slate-900 truncate">{immobile.titolo}</h3>
          <p className="text-sm text-slate-500 truncate">{immobile.indirizzo}</p>
          <Badge 
            className={cn(
              "mt-1",
              status === 'rosso' && "bg-red-500",
              status === 'giallo' && "bg-amber-500",
              status === 'verde' && "bg-emerald-500",
              status === 'grigio' && "bg-slate-500"
            )}
          >
            {status === 'rosso' ? 'Critico' :
             status === 'giallo' ? 'Attenzione' :
             status === 'verde' ? 'OK' : 'Non locato'}
          </Badge>
        </div>
      </div>
      
      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2 text-slate-600">
          <Building2 className="w-4 h-4" />
          <span>{immobile.unita_count} unità • {immobile.contratti_attivi} contratti attivi</span>
        </div>
        
        {immobile.affittuari?.length > 0 && (
          <div className="flex items-center gap-2 text-slate-600">
            <Users className="w-4 h-4" />
            <span>{immobile.affittuari.join(', ')}</span>
          </div>
        )}
        
        {problems?.length > 0 && (
          <div className="mt-2 p-2 bg-red-50 rounded-lg">
            <div className="flex items-center gap-1 text-red-700 font-medium mb-1">
              <AlertTriangle className="w-4 h-4" />
              Problemi
            </div>
            <ul className="text-red-600 text-xs space-y-1">
              {problems.map((p, i) => (
                <li key={i}>• {p}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
      
      <Link to={marker.link}>
        <Button size="sm" className="w-full mt-3 gap-2">
          Dettagli <ExternalLink className="w-3 h-3" />
        </Button>
      </Link>
    </div>
  );
}

function StatusLegend({ stats }) {
  const items = [
    { color: 'bg-red-500', label: 'Critico', count: stats?.rosso || 0 },
    { color: 'bg-amber-500', label: 'Attenzione', count: stats?.giallo || 0 },
    { color: 'bg-emerald-500', label: 'OK', count: stats?.verde || 0 },
    { color: 'bg-slate-500', label: 'Non locato', count: stats?.grigio || 0 },
  ];
  
  return (
    <div className="flex items-center gap-4 flex-wrap">
      {items.map(item => (
        <div key={item.label} className="flex items-center gap-2">
          <div className={cn("w-3 h-3 rounded-full", item.color)} />
          <span className="text-sm text-slate-600 dark:text-slate-400">
            {item.label} ({item.count})
          </span>
        </div>
      ))}
    </div>
  );
}

export default function MappaPage() {
  const [selectedStatus, setSelectedStatus] = useState(null);
  const [markersData, setMarkersData] = useState(null);
  const [loading, setLoading] = useState(true);
  const mapRef = useRef(null);

  const fetchMarkers = async () => {
    setLoading(true);
    try {
      const params = selectedStatus ? { stato: selectedStatus } : {};
      const response = await api.get('/mappa/markers', { params });
      setMarkersData(response.data);
    } catch (error) {
      console.error('Failed to fetch markers:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMarkers();
  }, [selectedStatus]);

  const markers = markersData?.markers || [];
  const stats = markersData?.by_status || {};

  // Default center (Italy)
  const defaultCenter = [41.9, 12.5];
  const defaultZoom = 6;

  return (
    <div className="space-y-4" data-testid="mappa-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-heading">Mappa Immobili</h1>
          <p className="text-slate-500">
            {markers.length} immobili visualizzati
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchMarkers}
            disabled={loading}
          >
            <RefreshCw className={cn("w-4 h-4 mr-2", loading && "animate-spin")} />
            Aggiorna
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card className="border-slate-200 dark:border-slate-800">
        <CardContent className="py-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-500" />
              <span className="text-sm text-slate-500">Filtra per stato:</span>
              <div className="flex gap-1">
                {[
                  { value: null, label: 'Tutti' },
                  { value: 'rosso', label: 'Critico', color: 'bg-red-500' },
                  { value: 'giallo', label: 'Attenzione', color: 'bg-amber-500' },
                  { value: 'verde', label: 'OK', color: 'bg-emerald-500' },
                  { value: 'grigio', label: 'Non locato', color: 'bg-slate-500' },
                ].map(filter => (
                  <Button
                    key={filter.label}
                    variant={selectedStatus === filter.value ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedStatus(filter.value)}
                    className="gap-1"
                  >
                    {filter.color && <div className={cn("w-2 h-2 rounded-full", filter.color)} />}
                    {filter.label}
                  </Button>
                ))}
              </div>
            </div>
            
            <StatusLegend stats={stats} />
          </div>
        </CardContent>
      </Card>

      {/* Map */}
      <Card className="border-slate-200 dark:border-slate-800 overflow-hidden">
        <div className="h-[600px] relative">
          {loading && markers.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-100 dark:bg-slate-800">
              <div className="text-center">
                <Skeleton className="w-12 h-12 rounded-full mx-auto mb-4" />
                <p className="text-slate-500">Caricamento mappa...</p>
              </div>
            </div>
          ) : markers.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-100 dark:bg-slate-800">
              <div className="text-center">
                <Building2 className="w-12 h-12 text-slate-400 mx-auto mb-4" />
                <p className="text-slate-600 font-medium">Nessun immobile con coordinate</p>
                <p className="text-slate-500 text-sm mt-1">
                  Aggiungi coordinate agli immobili per visualizzarli sulla mappa
                </p>
                <Link to="/immobili/nuovo">
                  <Button className="mt-4">Aggiungi Immobile</Button>
                </Link>
              </div>
            </div>
          ) : (
            <MapContainer
              center={defaultCenter}
              zoom={defaultZoom}
              className="h-full w-full"
              ref={mapRef}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              
              <FitBounds markers={markers} />
              
              {markers.map(marker => (
                <Marker
                  key={marker.id}
                  position={[marker.lat, marker.lon]}
                  icon={createColoredIcon(marker.status)}
                >
                  <Popup>
                    <MarkerPopup marker={marker} />
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          )}
        </div>
      </Card>
    </div>
  );
}
