import AsyncStorage from '@react-native-async-storage/async-storage';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

class ApiClient {
  private token: string | null = null;

  async getToken(): Promise<string | null> {
    if (this.token) return this.token;
    this.token = await AsyncStorage.getItem('access_token');
    return this.token;
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      AsyncStorage.setItem('access_token', token);
    } else {
      AsyncStorage.removeItem('access_token');
      AsyncStorage.removeItem('refresh_token');
    }
  }

  async setRefreshToken(token: string) {
    await AsyncStorage.setItem('refresh_token', token);
  }

  async request(path: string, options: RequestInit = {}): Promise<any> {
    const token = await this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const url = `${BACKEND_URL}${path}`;
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      // Try refresh
      const refreshToken = await AsyncStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const refreshRes = await fetch(`${BACKEND_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Refresh-Token': refreshToken },
          });
          if (refreshRes.ok) {
            const data = await refreshRes.json();
            this.setToken(data.access_token);
            headers['Authorization'] = `Bearer ${data.access_token}`;
            const retryRes = await fetch(url, { ...options, headers });
            if (!retryRes.ok) {
              const errData = await retryRes.json().catch(() => ({}));
              throw new Error(errData.detail || `HTTP ${retryRes.status}`);
            }
            return retryRes.json();
          }
        } catch (e) {
          // refresh failed
        }
      }
      this.setToken(null);
      throw new Error('Session expired');
    }
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      const detail = errData.detail;
      if (typeof detail === 'string') throw new Error(detail);
      if (Array.isArray(detail)) throw new Error(detail.map((e: any) => e.msg || JSON.stringify(e)).join(' '));
      throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
  }

  get(path: string) {
    return this.request(path, { method: 'GET' });
  }

  post(path: string, body?: any) {
    return this.request(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });
  }

  put(path: string, body?: any) {
    return this.request(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined });
  }

  delete(path: string) {
    return this.request(path, { method: 'DELETE' });
  }
}

export const api = new ApiClient();
