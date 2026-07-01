/**
 * src/config.js
 * -------------
 * Uygulama genelinde kullanılan merkezi yapılandırma.
 * Production deploy'da sadece bu dosyayı güncellemek yeterlidir.
 */

// İzlenecek Discord sunucusunun ID'si
export const GUILD_ID = "1494456063729078294";

// FastAPI backend'in base URL'si
// Dev: http://localhost:8000/api
// Prod: https://your-api.example.com/api
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
