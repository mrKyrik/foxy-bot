import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Shield, Key, Loader } from 'lucide-react';
import { API_BASE_URL } from '../config';

const LoginPage = ({ setAuthToken }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await axios.post(`${API_BASE_URL}/auth/login`, { password });
      if (res.data.status === 'success') {
        const token = res.data.token;
        localStorage.setItem('kumiho_token', token);
        setAuthToken(token);
        navigate('/'); // Login başarılı, ana sayfaya git
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Giriş başarısız. Lütfen şifrenizi kontrol edin.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: 'var(--bg-color)',
      fontFamily: 'var(--font-primary)'
    }}>
      <div className="glass-panel" style={{
        padding: '40px',
        width: '100%',
        maxWidth: '400px',
        borderRadius: '24px',
        border: '1px solid var(--panel-border-glow)',
        boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center'
      }}>
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          background: 'rgba(255, 255, 255, 0.05)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          marginBottom: '24px',
          border: '1px solid var(--panel-border)'
        }}>
          <Shield size={32} color="var(--accent-blue)" />
        </div>
        
        <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>Kumiho Yönetim</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '32px', textAlign: 'center' }}>
          Sisteme erişmek için süper admin şifrenizi girin.
        </p>

        <form onSubmit={handleLogin} style={{ width: '100%' }}>
          <div style={{ position: 'relative', marginBottom: '24px' }}>
            <Key size={18} color="var(--text-muted)" style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="password"
              placeholder="Admin Şifresi"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(0,0,0,0.2)',
                border: '1px solid var(--panel-border)',
                borderRadius: '12px',
                padding: '16px 16px 16px 48px',
                color: '#fff',
                fontSize: '1rem',
                outline: 'none',
                transition: 'border-color 0.3s'
              }}
              onFocus={(e) => e.target.style.borderColor = 'var(--accent-blue)'}
              onBlur={(e) => e.target.style.borderColor = 'var(--panel-border)'}
            />
          </div>

          {error && (
            <div style={{
              color: 'var(--accent-red)',
              fontSize: '0.9rem',
              marginBottom: '16px',
              padding: '12px',
              background: 'rgba(244, 63, 94, 0.1)',
              borderRadius: '8px',
              border: '1px solid rgba(244, 63, 94, 0.2)'
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '16px',
              background: 'var(--accent-blue)',
              color: '#fff',
              border: 'none',
              borderRadius: '12px',
              fontSize: '1rem',
              fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '8px',
              opacity: loading ? 0.7 : 1,
              transition: 'background 0.3s'
            }}
          >
            {loading ? <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} /> : 'Giriş Yap'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
