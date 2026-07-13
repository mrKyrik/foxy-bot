import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import { motion } from 'framer-motion';
import { Loader } from 'lucide-react';

const CallbackPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState(null);

  useEffect(() => {
    const code = searchParams.get('code');
    if (!code) {
      setError("Yetkilendirme kodu bulunamadı.");
      return;
    }

    const exchangeCode = async () => {
      try {
        const redirectUri = `${window.location.protocol}//${window.location.host}/auth/callback`;
        const res = await axios.post(`${API_BASE_URL}/auth/discord/callback`, { 
          code,
          redirect_uri: redirectUri
        });
        if (res.data.token) {
          localStorage.setItem('kumiho_token', res.data.token);
          // Reload to initialize contexts with new token
          window.location.href = '/'; 
        }
      } catch (err) {
        console.error(err);
        setError("Giriş yapılamadı: " + (err.response?.data?.detail || err.message));
      }
    };

    exchangeCode();
  }, [searchParams, navigate]);

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0a0a0a', color: '#ff4444' }}>
        <h2>Giriş Başarısız</h2>
        <p>{error}</p>
        <button onClick={() => navigate('/login')} style={{ marginTop: '20px', padding: '10px 20px', background: '#333', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>Giriş Sayfasına Dön</button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0a0a0a', color: 'white' }}>
      <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
        <Loader size={48} color="#00ff88" />
      </motion.div>
      <h2 style={{ marginTop: '20px' }}>Discord ile Bağlanılıyor...</h2>
    </div>
  );
};

export default CallbackPage;
