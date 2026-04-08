import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from './api';

interface User {
  user_id: string;
  email: string;
  username: string;
  bio?: string;
  avatar_url?: string;
  status?: string;
  role?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, username: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
  refreshUser: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const token = await api.getToken();
      if (!token) {
        setLoading(false);
        return;
      }
      const data = await api.get('/api/auth/me');
      setUser(data.user);
    } catch {
      api.setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email: string, password: string) => {
    const data = await api.post('/api/auth/login', { email, password });
    api.setToken(data.access_token);
    await api.setRefreshToken(data.refresh_token);
    setUser(data.user);
  };

  const register = async (email: string, password: string, username: string) => {
    const data = await api.post('/api/auth/register', { email, password, username });
    api.setToken(data.access_token);
    await api.setRefreshToken(data.refresh_token);
    setUser(data.user);
  };

  const logout = async () => {
    api.setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const data = await api.get('/api/auth/me');
      setUser(data.user);
    } catch {}
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
