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
export const API_BASE_URL = "http://localhost:3001/api";

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
