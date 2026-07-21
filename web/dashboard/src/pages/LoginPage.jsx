import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import { motion } from 'framer-motion';
import { Loader } from 'lucide-react';

const LoginPage = ({ setAuthToken }) => {
  const [stats, setStats] = useState({ total_guilds: 0, total_users: 0 });

  // PKCE için code verifier ve challenge üret
  const generateCodeVerifier = () => {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return btoa(String.fromCharCode(...array))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  };

  const generateCodeChallenge = async (verifier) => {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const digest = await crypto.subtle.digest('SHA-256', data);
    return btoa(String.fromCharCode(...new Uint8Array(digest)))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  };

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/global_stats`);
        setStats(res.data);
      } catch (err) {
        console.error("Global stats fetch error:", err);
      }
    };
    fetchStats();
  }, []);

  const handleLogin = async () => {
    try {
      // PKCE parametreleri üret
      const codeVerifier = generateCodeVerifier();
      const codeChallenge = await generateCodeChallenge(codeVerifier);
      
      // State parametresi (CSRF koruması)
      const state = crypto.randomUUID();
      
      // Code verifier ve state'i sessionStorage'a kaydet
      sessionStorage.setItem('pkce_verifier', codeVerifier);
      sessionStorage.setItem('oauth_state', state);
      
      const clientId = import.meta.env.VITE_DISCORD_CLIENT_ID || '1514724443824328744';
      const redirectUri = import.meta.env.VITE_DISCORD_REDIRECT_URI || `${window.location.protocol}//${window.location.host}/auth/callback`;
      
      const DISCORD_OAUTH_URL = `https://discord.com/api/oauth2/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=identify%20guilds&state=${state}&code_challenge=${codeChallenge}&code_challenge_method=S256`;
      
      window.location.href = DISCORD_OAUTH_URL;
    } catch (err) {
      console.error("Login error:", err);
      alert("Giriş başlatılamadı: " + err.message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0a0a0a', color: 'white', padding: '24px' }}>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} style={{ textAlign: 'center', maxWidth: '400px' }}>
        <div style={{ marginBottom: '32px' }}>
          <h1 style={{ fontSize: '3rem', fontWeight: 800, background: 'linear-gradient(135deg, #00ff88, #00d4ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: '16px' }}>
            Kumiho Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>Sunucu yönetim paneline hoş geldiniz</p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '32px' }}>
          <div className="glass-panel" style={{ padding: '24px', borderRadius: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Toplam Sunucu</span>
              <span style={{ fontWeight: 700, fontSize: '1.5rem' }}>{stats.total_guilds || 0}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Toplam Kullanıcı</span>
              <span style={{ fontWeight: 700, fontSize: '1.5rem' }}>{stats.total_users || 0}</span>
            </div>
          </div>
        </div>

        <button 
          onClick={handleLogin}
          style={{
            padding: '16px 32px',
            background: 'linear-gradient(135deg, #5865F2, #4752C4)',
            color: 'white',
            border: 'none',
            borderRadius: '12px',
            fontSize: '1.1rem',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            boxShadow: '0 8px 32px rgba(88, 101, 242, 0.3)',
            transition: 'transform 0.2s, box-shadow 0.2s',
            minWidth: '280px'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 12px 40px rgba(88, 101, 242, 0.4)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 8px 32px rgba(88, 101, 242, 0.3)'; }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.675 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.083.083 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 4.738.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.007-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 0 7.393-.77 10.517-2.14a.076.076 0 0 1 .106.041c.36.645.773 1.255 1.217 1.827a.077.077 0 0 0 .085.028h.005a19.886 19.886 0 0 0 6.002-4.732.077.077 0 0 0 .032-.054c.385-4.124-.723-8.85-3.548-13.66a.061.061 0 0 0-.031-.03zM12.017 19.93a7.6 7.6 0 1 1 0-15.2 7.6 7.6 0 0 1 0 15.2zm0-1.8a5.8 5.8 0 1 1 0-11.6 5.8 5.8 0 0 1 0 11.6zm5.8-7.8a.83.83 0 0 1-.83.83h-4.17a.83.83 0 0 1 0-1.66h4.17a.83.83 0 0 1 .83.83z"/>
          </svg>
          Discord ile Giriş Yap
        </button>

        <p style={{ marginTop: '24px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Giriş yaparak <a href="https://discord.com/terms" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-blue)' }}>Discord Hizmet Şartları</a> ve 
          <a href="https://discord.com/privacy" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-blue)' }}>Gizlilik Politikası</a>'nı kabul etmiş olursunuz.
        </p>
      </motion.div>
    </div>
  );
};

export default LoginPage;
