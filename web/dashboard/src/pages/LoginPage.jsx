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
          <img src="/foxy-bot-pp.webp" alt="Foxy Bot Logo" style={{ width: '120px', height: '120px', borderRadius: '50%', marginBottom: '24px', boxShadow: '0 8px 32px rgba(0,255,136,0.3)' }} />
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
            margin: '0 auto',
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
            <path d="M19.27 5.33C17.94 4.71 16.5 4.26 15 4a.09.09 0 0 0-.07.03c-.18.33-.39.76-.53 1.09a16.09 16.09 0 0 0-4.8 0c-.14-.33-.35-.76-.53-1.09a.09.09 0 0 0-.07-.03c-1.5.26-2.93.71-4.27 1.33a.08.08 0 0 0-.05.05C1.86 10.74.83 16.08 1.13 21.36a.07.07 0 0 0 .03.05c1.8 1.32 3.53 2.12 5.24 2.65a.09.09 0 0 0 .1-.03c.41-.56.8-1.13 1.14-1.74a.09.09 0 0 0-.04-.12c-.58-.22-1.14-.49-1.66-.8a.09.09 0 0 1-.01-.15c.11-.08.23-.17.34-.26a.09.09 0 0 1 .09-.01c3.55 1.61 7.41 1.61 10.92 0a.09.09 0 0 1 .09.01c.11.09.23.18.34.26a.09.09 0 0 1-.01.15c-.52.31-1.08.58-1.66.8a.09.09 0 0 0-.04.12c.35.61.73 1.18 1.14 1.74a.09.09 0 0 0 .1.03c1.71-.53 3.44-1.33 5.24-2.65a.07.07 0 0 0 .03-.05c.36-6.01-.98-11.23-3.6-15.98a.08.08 0 0 0-.05-.05ZM8.5 16.5c-1.12 0-2.03-.99-2.03-2.2s.9-2.2 2.03-2.2c1.13 0 2.04.99 2.03 2.2 0 1.21-.9 2.2-2.03 2.2Zm7 0c-1.12 0-2.03-.99-2.03-2.2s.9-2.2 2.03-2.2c1.13 0 2.04.99 2.03 2.2 0 1.21-.9 2.2-2.03 2.2Z"/>
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
