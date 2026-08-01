/**
 * src/config.js
 * -------------
 * Uygulama genelinde kullanılan merkezi yapılandırma.
 * Production deploy'da sadece bu dosyayı güncellemek yeterlidir.
 */

// İzlenecek Discord sunucusunun ID'si
// export const GUILD_ID = "1494456063729078294"; // Artık Context üzerinden dinamik yönetiliyor

import axios from 'axios';

// FastAPI backend'in base URL'si
// Dev: http://localhost:3001/api
// Prod: https://api.kumiho.bot/api
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? `http://${window.location.hostname}:3001/api` 
    : `${window.location.protocol}//${window.location.host}/api`);

// Axios interceptor: Her isteğe JWT token ekle
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('kumiho_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: 401 alınırsa refresh yapmayı dene, olmazsa veya 403 ise token'ı sil ve çık
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // 401 hatası aldıysak ve daha önce retry yapmadıysak
    if (error.response && error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('kumiho_refresh_token');
      
      if (refreshToken) {
        try {
          const res = await axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken });
          if (res.data.token) {
            localStorage.setItem('kumiho_token', res.data.token);
            if (res.data.refresh_token) {
              localStorage.setItem('kumiho_refresh_token', res.data.refresh_token);
            }
            // Başarılı olursa orjinal isteği yeni token ile tekrar dene
            originalRequest.headers['Authorization'] = `Bearer ${res.data.token}`;
            return axios(originalRequest);
          }
        } catch (refreshError) {
          // Refresh de patlarsa her şeyi temizle
          localStorage.removeItem('kumiho_token');
          localStorage.removeItem('kumiho_refresh_token');
          localStorage.removeItem('kumiho_active_guild');
          window.location.href = '/';
          return Promise.reject(refreshError);
        }
      }
    }
    
    // Refresh yoksa veya 403 yetkisizlik hatasıysa
    if (error.response && (error.response.status === 401 || error.response.status === 403)) {
      localStorage.removeItem('kumiho_token');
      localStorage.removeItem('kumiho_refresh_token');
      localStorage.removeItem('kumiho_active_guild');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);
