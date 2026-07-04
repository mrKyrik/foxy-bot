import React, { useEffect, useState, useContext } from 'react';
import axios from 'axios';
import { Activity, AlertTriangle, Shield, Clock } from 'lucide-react';
import { GuildContext } from '../GuildContext';
import { API_BASE_URL } from '../config';

const OverviewPage = () => {
  const { activeGuildId, guilds } = useContext(GuildContext);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (!activeGuildId) return;
    const fetchStats = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/stats/${activeGuildId}`);
        setStats(res.data);
      } catch (e) {
        console.error(e);
      }
    };
    fetchStats();
  }, [activeGuildId]);

  const activeGuild = guilds.find(g => g.id === activeGuildId);

  return (
    <div style={{ padding: '24px', color: '#fff' }}>
      <h1>Genel Bakış: {activeGuild ? activeGuild.name : '...'}</h1>
      
      {stats ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginTop: '24px' }}>
          <div style={{ background: 'rgba(255,255,255,0.05)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--accent-green)', marginBottom: '10px' }}>
              <Activity size={24} /> <h3>Toplam Log</h3>
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{stats.total_logs}</div>
          </div>
          
          <div style={{ background: 'rgba(255,255,255,0.05)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--accent-orange)', marginBottom: '10px' }}>
              <AlertTriangle size={24} /> <h3>Uyarılar (Warns)</h3>
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{stats.total_warns}</div>
          </div>

          <div style={{ background: 'rgba(255,255,255,0.05)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--accent-blue)', marginBottom: '10px' }}>
              <Shield size={24} /> <h3>Admin İşlemleri</h3>
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{stats.total_admin_actions}</div>
          </div>
        </div>
      ) : (
        <p style={{ marginTop: '24px', color: 'var(--text-secondary)' }}>Veriler yükleniyor veya bu sunucuya ait veri yok...</p>
      )}

      {stats && stats.recent_logs && stats.recent_logs.length > 0 && (
        <div style={{ marginTop: '40px' }}>
          <h2>Son Aktiviteler</h2>
          <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {stats.recent_logs.map((log, idx) => (
              <div key={idx} style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Clock size={16} color="var(--text-secondary)" />
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{new Date(log.timestamp).toLocaleString()}</span>
                <span style={{ fontWeight: '500', color: 'var(--accent-blue)' }}>{log.event_type}</span>
                <span style={{ color: '#ccc' }}>Kullanıcı/Kanal: {log.user_id}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default OverviewPage;
