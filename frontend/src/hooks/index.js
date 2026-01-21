import { useEffect, useCallback, useState } from 'react';
import { useAuthStore, useNotificationsStore, api } from '../stores';

// Hook for API calls with loading state
export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const request = useCallback(async (method, url, data = null, config = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api({
        method,
        url,
        data,
        ...config
      });
      return response.data;
    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Errore sconosciuto';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { request, loading, error, setError };
}

// Hook for fetching data
export function useFetch(url, dependencies = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAuthenticated } = useAuthStore();

  const fetchData = useCallback(async () => {
    if (!isAuthenticated || !url) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get(url);
      setData(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }, [url, isAuthenticated]);

  useEffect(() => {
    fetchData();
  }, [fetchData, ...dependencies]);

  return { data, loading, error, refetch: fetchData };
}

// Hook for dashboard data
export function useDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { isAuthenticated } = useAuthStore();

  const fetchDashboard = useCallback(async () => {
    if (!isAuthenticated) return;
    
    setLoading(true);
    try {
      const [overview, rateRitardo, eventiCritici, contrattiScadenza] = await Promise.all([
        api.get('/dashboard/overview'),
        api.get('/dashboard/rate-ritardo?limit=5'),
        api.get('/dashboard/eventi-critici?limit=5'),
        api.get('/dashboard/contratti-scadenza?limit=5')
      ]);

      setData({
        kpi: overview.data.kpi,
        rateRitardo: rateRitardo.data,
        eventiCritici: eventiCritici.data,
        contrattiScadenza: contrattiScadenza.data
      });
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  return { data, loading, refetch: fetchDashboard };
}

// Hook for notifications
export function useNotifications() {
  const { notifications, unreadCount, fetchNotifications, markAsRead, markAllAsRead } = useNotificationsStore();
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      fetchNotifications();
      const interval = setInterval(fetchNotifications, 60000); // Refresh every minute
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, fetchNotifications]);

  return { notifications, unreadCount, markAsRead, markAllAsRead, refetch: fetchNotifications };
}

// Hook for theme
export function useTheme() {
  const [theme, setTheme] = useState(() => {
    const stored = localStorage.getItem('estatewise-ui');
    if (stored) {
      try {
        return JSON.parse(stored).state?.theme || 'light';
      } catch {
        return 'light';
      }
    }
    return 'light';
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  const toggleTheme = useCallback(() => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    const stored = JSON.parse(localStorage.getItem('estatewise-ui') || '{"state":{}}');
    stored.state.theme = newTheme;
    localStorage.setItem('estatewise-ui', JSON.stringify(stored));
  }, [theme]);

  return { theme, toggleTheme };
}

// Hook for debouncing
export function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
