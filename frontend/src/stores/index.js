import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api/v1';

// Auth Store
export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      
      login: async (email, password) => {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);
        
        const response = await axios.post(`${API_URL}/auth/login`, formData);
        const { access_token, refresh_token, user } = response.data;
        
        set({
          user,
          token: access_token,
          refreshToken: refresh_token,
          isAuthenticated: true
        });
        
        return user;
      },
      
      logout: () => {
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false
        });
      },
      
      refreshAuth: async () => {
        const { refreshToken } = get();
        if (!refreshToken) throw new Error('No refresh token');
        
        const response = await axios.post(`${API_URL}/auth/refresh`, {
          refresh_token: refreshToken
        });
        
        const { access_token, refresh_token, user } = response.data;
        
        set({
          user,
          token: access_token,
          refreshToken: refresh_token
        });
      },
      
      updateUser: (userData) => {
        set({ user: { ...get().user, ...userData } });
      }
    }),
    {
      name: 'estatewise-auth',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
);

// UI Store
export const useUIStore = create(
  persist(
    (set) => ({
      theme: 'light',
      sidebarOpen: true,
      
      toggleTheme: () => set((state) => ({ 
        theme: state.theme === 'light' ? 'dark' : 'light' 
      })),
      
      setTheme: (theme) => set({ theme }),
      
      toggleSidebar: () => set((state) => ({ 
        sidebarOpen: !state.sidebarOpen 
      })),
      
      setSidebarOpen: (open) => set({ sidebarOpen: open })
    }),
    {
      name: 'estatewise-ui'
    }
  )
);

// Notifications Store
export const useNotificationsStore = create((set, get) => ({
  notifications: [],
  unreadCount: 0,
  
  setNotifications: (notifications) => set({ notifications }),
  setUnreadCount: (count) => set({ unreadCount: count }),
  
  fetchNotifications: async () => {
    const { token } = useAuthStore.getState();
    if (!token) return;
    
    try {
      const response = await axios.get(`${API_URL}/notifiche`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { limit: 20 }
      });
      set({ notifications: response.data });
      
      const countResponse = await axios.get(`${API_URL}/notifiche/count-non-lette`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      set({ unreadCount: countResponse.data.count });
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    }
  },
  
  markAsRead: async (notificaId) => {
    const { token } = useAuthStore.getState();
    if (!token) return;
    
    try {
      await axios.post(`${API_URL}/notifiche/${notificaId}/read`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      get().fetchNotifications();
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  },
  
  markAllAsRead: async () => {
    const { token } = useAuthStore.getState();
    if (!token) return;
    
    try {
      await axios.post(`${API_URL}/notifiche/read-all`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      get().fetchNotifications();
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  }
}));

// Create axios instance with interceptors
export const api = axios.create({
  baseURL: API_URL
});

api.interceptors.request.use((config) => {
  const { token } = useAuthStore.getState();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        await useAuthStore.getState().refreshAuth();
        const { token } = useAuthStore.getState();
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      } catch (refreshError) {
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
