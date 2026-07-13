import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Shield, Key, Server, Users } from 'lucide-react';
import { API_BASE_URL } from '../config';
import './Login.css';

const LoginPage = ({ setAuthToken }) => {
  const [stats, setStats] = useState({ total_guilds: 0, total_users: 0 });

  const clientId = import.meta.env.VITE_DISCORD_CLIENT_ID || '1514724443824328744';
  const redirectUri = import.meta.env.VITE_DISCORD_REDIRECT_URI || 'http://localhost:5173/auth/callback';
  const DISCORD_OAUTH_URL = `https://discord.com/api/oauth2/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=identify%20guilds`;

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



  return (
    <div className="login-container">
      {/* Sol Taraf - Kumiho Marka Alanı */}
      <div className="login-left">
        <div className="brand-wrapper">
          <div className="brand-logo-container">
            <Shield size={56} color="var(--accent-blue)" />
          </div>
          <h1 className="brand-title">Kumiho</h1>
          <p className="brand-subtitle">
            Gelişmiş Discord Moderasyon ve Sunucu Yönetim Sistemi. Kontrolü elinize alın.
          </p>
          
          <div style={{ display: 'flex', gap: '24px', marginTop: '32px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(255,255,255,0.05)', padding: '12px 24px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
              <Server size={24} color="var(--accent-blue)" />
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#fff' }}>{stats.total_guilds}</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Aktif Sunucu</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(255,255,255,0.05)', padding: '12px 24px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
              <Users size={24} color="var(--accent-green)" />
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#fff' }}>{stats.total_users}</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Toplam Kullanıcı</div>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Sağ Taraf - Giriş Formu */}
      <div className="login-right">
        <div className="login-panel">
          <div className="login-header">
            <h2>Hoş Geldiniz</h2>
            <p>Sisteme erişmek ve sunucunuzu yönetmek için Discord ile giriş yapın.</p>
          </div>

          <a href={DISCORD_OAUTH_URL} className="login-btn" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
            Discord ile Giriş Yap
          </a>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
