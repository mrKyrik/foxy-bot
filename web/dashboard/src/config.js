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

// Response interceptor: 401 veya 403 alınırsa token'ı sil ve ana sayfaya yönlendir
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && (error.response.status === 401 || error.response.status === 403)) {
      localStorage.removeItem('kumiho_token');
      localStorage.removeItem('kumiho_active_guild');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);
