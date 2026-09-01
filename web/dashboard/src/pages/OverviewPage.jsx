import React, { useEffect, useState, useContext } from 'react';
import axios from 'axios';
import { Activity, AlertTriangle, Shield, Clock, LayoutDashboard } from 'lucide-react';
import { motion } from 'framer-motion';
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
    <div style={{ padding: '32px', height: '100%', overflowY: 'auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <LayoutDashboard size={32} color="var(--color-cyan)" /> Genel Bakış
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>
            {activeGuild ? `${activeGuild.name} sunucusunun temel istatistikleri ve son aktiviteleri.` : 'Yükleniyor...'}
          </p>
        </div>
      </header>

      {stats ? (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-panel" style={{ padding: '24px', borderRadius: '16px', display: 'flex', alignItems: 'center', gap: '20px' }}>
              <div style={{ background: 'rgba(0, 210, 255, 0.1)', padding: '16px', borderRadius: '12px', color: 'var(--color-cyan)' }}>
                <Activity size={32} />
              </div>
              <div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '4px' }}>Toplam Log İşlemi</div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fff' }}>{stats.total_logs}</div>
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-panel" style={{ padding: '24px', borderRadius: '16px', display: 'flex', alignItems: 'center', gap: '20px' }}>
              <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '16px', borderRadius: '12px', color: 'var(--accent-orange)' }}>
                <AlertTriangle size={32} />
              </div>
              <div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '4px' }}>Uyarılar (Warns)</div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fff' }}>{stats.total_warns}</div>
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass-panel" style={{ padding: '24px', borderRadius: '16px', display: 'flex', alignItems: 'center', gap: '20px' }}>
              <div style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '16px', borderRadius: '12px', color: 'var(--accent-blue)' }}>
                <Shield size={32} />
              </div>
              <div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '4px' }}>Admin İşlemleri</div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fff' }}>{stats.total_admin_actions}</div>
              </div>
            </motion.div>
          </div>

          {stats.recent_logs && stats.recent_logs.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="glass-panel" style={{ marginTop: '32px', padding: '24px', borderRadius: '16px' }}>
              <h2 style={{ fontSize: '1.25rem', color: '#fff', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={20} color="var(--color-cyan)" /> Son Aktiviteler
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {stats.recent_logs.map((log, idx) => (
                  <div key={idx} style={{ background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '16px', border: '1px solid var(--panel-border)' }}>
                    <div style={{ background: 'var(--panel-bg)', padding: '8px', borderRadius: '8px', color: 'var(--text-secondary)' }}>
                      <Activity size={18} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, color: 'var(--accent-blue)', marginBottom: '4px' }}>{log.event_type}</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{log.username ? `${log.username} (${log.user_id})` : `Kullanıcı / Hedef: ${log.user_id || 'Bilinmiyor'}`}</div>
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={14} /> {log.timestamp ? new Date(log.timestamp).toLocaleString('tr-TR') : 'Bilinmiyor'}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </>
      ) : (
        <div className="glass-panel" style={{ padding: '48px', textAlign: 'center', borderRadius: '16px' }}>
          <Activity size={48} color="var(--text-muted)" style={{ marginBottom: '16px', opacity: 0.5 }} />
          <h3 style={{ color: '#fff', fontSize: '1.25rem', marginBottom: '8px' }}>Veriler Yükleniyor veya Yok</h3>
          <p style={{ color: 'var(--text-secondary)' }}>Sunucu istatistikleri toparlanıyor veya henüz log verisi bulunmuyor...</p>
        </div>
      )}
    </div>
  );
};

export default OverviewPage;
