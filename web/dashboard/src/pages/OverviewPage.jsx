import React, { useEffect, useState, useContext } from 'react';
import axios from 'axios';
import { Activity, AlertTriangle, Shield, Clock, LayoutDashboard, RefreshCw, User, Volume2, MessageSquare, Wrench } from 'lucide-react';
import { motion } from 'framer-motion';
import { GuildContext } from '../GuildContext';
import { API_BASE_URL } from '../config';

const EVENT_TYPE_MAP = {
  ses_join: { label: 'Kanala Katıldı', color: 'var(--accent-green, #10b981)', icon: Volume2 },
  ses_leave: { label: 'Kanaldan Ayrıldı', color: 'var(--accent-red, #ef4444)', icon: Volume2 },
  ses_switch_join: { label: 'Kanal Değiştirdi', color: 'var(--accent-blue, #3b82f6)', icon: Volume2 },
  ses_switch_leave: { label: 'Kanal Değiştirdi', color: 'var(--accent-blue, #3b82f6)', icon: Volume2 },
  ses_camera_on: { label: 'Kamera Açtı', color: 'var(--accent-green, #10b981)', icon: Volume2 },
  ses_camera_off: { label: 'Kamera Kapattı', color: 'var(--text-muted, #64748b)', icon: Volume2 },
  ses_stream_on: { label: 'Yayın Başlattı', color: 'var(--color-cyan, #06b6d4)', icon: Volume2 },
  ses_stream_off: { label: 'Yayın Kapattı', color: 'var(--text-muted, #64748b)', icon: Volume2 },
  msg_delete: { label: 'Mesaj Silindi', color: 'var(--accent-red, #ef4444)', icon: MessageSquare },
  msg_edit: { label: 'Mesaj Düzenlendi', color: 'var(--accent-orange, #f59e0b)', icon: MessageSquare },
  mod_msg_delete: { label: 'Yetkili Mesaj Sildi', color: 'var(--accent-red, #ef4444)', icon: MessageSquare },
  mod_channel: { label: 'Kanal Değişikliği', color: 'var(--accent-orange, #f59e0b)', icon: Wrench },
  mod_role: { label: 'Rol Değişikliği', color: 'var(--color-purple, #8b5cf6)', icon: Shield },
  srv_role: { label: 'Sunucu Rolü Güncellendi', color: 'var(--color-purple, #8b5cf6)', icon: Shield },
  srv_perm: { label: 'İzin Güncellendi', color: 'var(--color-purple, #8b5cf6)', icon: Shield },
  role_add: { label: 'Rol Verildi', color: 'var(--accent-green, #10b981)', icon: Shield },
  role_remove: { label: 'Rol Alındı', color: 'var(--accent-red, #ef4444)', icon: Shield },
  role_sync_add: { label: 'Rol Eşitlendi', color: 'var(--accent-blue, #3b82f6)', icon: Shield },
  ticket_create: { label: 'Talep Açıldı', color: 'var(--color-cyan, #06b6d4)', icon: Activity },
  ticket_close: { label: 'Talep Kapatıldı', color: 'var(--text-muted, #64748b)', icon: Activity },
  app_create: { label: 'Başvuru Yapıldı', color: 'var(--accent-blue, #3b82f6)', icon: Activity },
  invite_use: { label: 'Davet Kullanıldı', color: 'var(--accent-green, #10b981)', icon: Activity },
  oda_create: { label: 'Özel Oda Oluşturuldu', color: 'var(--accent-green, #10b981)', icon: Volume2 },
  oda_delete: { label: 'Özel Oda Silindi', color: 'var(--accent-red, #ef4444)', icon: Volume2 },
  oda_update: { label: 'Özel Oda Güncellendi', color: 'var(--accent-orange, #f59e0b)', icon: Volume2 },
  BAN: { label: 'Kullanıcı Yasaklandı', color: 'var(--accent-red, #ef4444)', icon: Shield },
  mod_ban: { label: 'Yetkili Ban Attı', color: 'var(--accent-red, #ef4444)', icon: Shield },
  PURGE: { label: 'Toplu Mesaj Silme', color: 'var(--accent-red, #ef4444)', icon: MessageSquare },
  NUKE: { label: 'Kanal Yenilendi (Nuke)', color: 'var(--accent-red, #ef4444)', icon: Wrench },
  ROLE_ADD: { label: 'Admin Rol Verdi', color: 'var(--accent-green, #10b981)', icon: Shield },
  ROLE_REMOVE: { label: 'Admin Rol Aldı', color: 'var(--accent-red, #ef4444)', icon: Shield }
};

const OverviewPage = () => {
  const { activeGuildId, guilds } = useContext(GuildContext);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    if (!activeGuildId) return;
    try {
      const res = await axios.get(`${API_BASE_URL}/stats/${activeGuildId}`);
      setStats(res.data);
    } catch (e) {
      console.error("Stats fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchStats();

    // 10 saniyede bir otomatik yenile
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, [activeGuildId]);

  const activeGuild = guilds.find(g => g.id === activeGuildId);

  const formatEventInfo = (eventType) => {
    return EVENT_TYPE_MAP[eventType] || { label: eventType || 'Bilinmeyen İşlem', color: 'var(--accent-blue, #3b82f6)', icon: Activity };
  };

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
        <button 
          onClick={() => { setLoading(true); fetchStats(); }}
          style={{
            background: 'var(--panel-bg, rgba(255,255,255,0.05))',
            border: '1px solid var(--panel-border, rgba(255,255,255,0.1))',
            color: 'var(--text-secondary, #94a3b8)',
            padding: '8px 16px',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
            fontSize: '0.85rem'
          }}>
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Yenile
        </button>
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
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fff' }}>{Number(stats.total_logs || 0).toLocaleString('tr-TR')}</div>
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-panel" style={{ padding: '24px', borderRadius: '16px', display: 'flex', alignItems: 'center', gap: '20px' }}>
              <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '16px', borderRadius: '12px', color: 'var(--accent-orange)' }}>
                <AlertTriangle size={32} />
              </div>
              <div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '4px' }}>Uyarılar (Warns)</div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fff' }}>{Number(stats.total_warns || 0).toLocaleString('tr-TR')}</div>
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass-panel" style={{ padding: '24px', borderRadius: '16px', display: 'flex', alignItems: 'center', gap: '20px' }}>
              <div style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '16px', borderRadius: '12px', color: 'var(--accent-blue)' }}>
                <Shield size={32} />
              </div>
              <div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '4px' }}>Admin İşlemleri</div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fff' }}>{Number(stats.total_admin_actions || 0).toLocaleString('tr-TR')}</div>
              </div>
            </motion.div>
          </div>

          {stats.recent_logs && stats.recent_logs.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="glass-panel" style={{ marginTop: '32px', padding: '24px', borderRadius: '16px' }}>
              <h2 style={{ fontSize: '1.25rem', color: '#fff', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={20} color="var(--color-cyan)" /> Son Aktiviteler
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {stats.recent_logs.map((log, idx) => {
                  const evInfo = formatEventInfo(log.event_type);
                  const IconComp = evInfo.icon;
                  return (
                    <div key={idx} style={{ background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '16px', border: '1px solid var(--panel-border)' }}>
                      {log.avatar_url ? (
                        <img 
                          src={log.avatar_url} 
                          alt="avatar" 
                          style={{ width: '40px', height: '40px', borderRadius: '10px', objectFit: 'cover', border: '1px solid var(--panel-border)' }}
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                      ) : (
                        <div style={{ background: 'var(--panel-bg)', padding: '10px', borderRadius: '10px', color: evInfo.color, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <IconComp size={20} />
                        </div>
                      )}
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <span style={{ fontWeight: 700, color: evInfo.color, fontSize: '0.95rem' }}>{evInfo.label}</span>
                          {log.source === 'admin' && (
                            <span style={{ fontSize: '0.7rem', padding: '2px 6px', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', fontWeight: 600 }}>ADMIN</span>
                          )}
                        </div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {log.username ? `${log.username} (${log.user_id})` : (log.user_id ? `Kullanıcı: ${log.user_id}` : (log.details_text || 'İşlem'))}
                        </div>
                      </div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={14} /> {log.timestamp ? new Date(log.timestamp).toLocaleString('tr-TR') : 'Bilinmiyor'}
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </>
      ) : (
        <div className="glass-panel" style={{ padding: '48px', textAlign: 'center', borderRadius: '16px' }}>
          <Activity size={48} color="var(--text-muted)" style={{ marginBottom: '16px', opacity: 0.5 }} />
          <h3 style={{ color: '#fff', fontSize: '1.25rem', marginBottom: '8px' }}>Veriler Yükleniyor</h3>
          <p style={{ color: 'var(--text-secondary)' }}>Sunucu istatistikleri alınıyor, lütfen bekleyin...</p>
        </div>
      )}
    </div>
  );
};

export default OverviewPage;

