import React, { useState, useEffect, useMemo, useContext } from 'react';
import axios from 'axios';
import { X, Mic, MessageSquare, ShieldAlert, Tag, Hash, Calendar, Edit3, Send, AlertTriangle, ShieldX, Hammer, Trash2 } from 'lucide-react';
import { formatTime } from '../utils/time';
import { API_BASE_URL } from '../config';
import { GuildContext } from '../GuildContext';

const UserLookPanel = ({ user, allLogs, onClose }) => {
  const { activeGuildId } = useContext(GuildContext);
  const [notes, setNotes] = useState([]);
  const [currentAdminId, setCurrentAdminId] = useState(null);
  const [isOwner, setIsOwner] = useState(false);
  const [currentRoles, setCurrentRoles] = useState([]);
  const [newNote, setNewNote] = useState('');
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [loadingRoles, setLoadingRoles] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Sadece bu kullanıcıya ait (user_id veya admin_id) logları filtrele
  const userLogs = useMemo(() => {
    if (!user || !user.id) return [];
    const id = user.id;
    return allLogs
      .filter(l => l.user_id === id || l.admin_id === id)
      .sort((a, b) => b.timestamp - a.timestamp); // En yeni en üstte
  }, [user, allLogs]);

  // Mini istatistikleri hesapla
  const stats = useMemo(() => {
    let msgCount = 0;
    let voiceCount = 0;
    let modCount = 0;
    
    userLogs.forEach(l => {
      const type = l.event_type || '';
      if (type.includes('msg')) msgCount++;
      else if (type.includes('voice')) voiceCount++;
      else if (type.includes('mod') || type.includes('warn') || type.includes('ban') || type.includes('kick')) modCount++;
    });

    return { msgCount, voiceCount, modCount };
  }, [userLogs]);

  useEffect(() => {
    if (user && user.id) {
      fetchNotes();
      fetchCurrentRoles();
    }
  }, [user, activeGuildId]);

  const fetchCurrentRoles = async () => {
    if (!activeGuildId || !user) return;
    setLoadingRoles(true);
    try {
      const token = localStorage.getItem('kumiho_token');
      const res = await axios.get(`${API_BASE_URL}/users/${activeGuildId}/${user.id}/roles`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCurrentRoles(res.data.roles || []);
    } catch (err) {
      console.error("Roller çekilemedi:", err);
    } finally {
      setLoadingRoles(false);
    }
  };

  const fetchNotes = async () => {
    setLoadingNotes(true);
    try {
      if (!activeGuildId) return;
      const res = await axios.get(`${API_BASE_URL}/notes/${activeGuildId}/${user.id}`);
      setNotes(res.data.notes || []);
      if (res.data.current_admin_id) setCurrentAdminId(res.data.current_admin_id);
      if (res.data.is_owner !== undefined) setIsOwner(res.data.is_owner);
    } catch (err) {
      console.error("Notlar çekilemedi:", err);
    } finally {
      setLoadingNotes(false);
    }
  };

  const handleAddNote = async (e) => {
    e.preventDefault();
    if (!newNote.trim()) return;

    try {
      if (!activeGuildId) return;
      await axios.post(`${API_BASE_URL}/notes/${activeGuildId}`, {
        user_id: user.id,
        note: newNote
      });
      setNewNote('');
      fetchNotes(); // Notları yenile
    } catch (err) {
      console.error("Not eklenemedi:", err);
    }
  };

  const handleDeleteNote = async (noteId) => {
    if (!window.confirm("Bu notu silmek istediğinize emin misiniz?")) return;
    try {
      await axios.delete(`${API_BASE_URL}/notes/${activeGuildId}/${noteId}`);
      fetchNotes();
    } catch (err) {
      console.error("Not silinemedi:", err);
      alert(err.response?.data?.error || "Not silinirken bir hata oluştu.");
    }
  };

  const handleAction = async (actionType) => {
    if (!window.confirm(`Kullanıcıya '${actionType}' işlemi uygulamak istediğinize emin misiniz?`)) return;
    
    setActionLoading(true);
    try {
      if (!activeGuildId) return;
      await axios.post(`${API_BASE_URL}/actions/${activeGuildId}`, {
        target_user_id: user.id,
        action_type: actionType,
        reason: "Dashboard üzerinden işlem yapıldı."
      });
      alert('İşlem başarıyla sıraya alındı!');
    } catch (err) {
      console.error("İşlem başarısız:", err);
      alert('İşlem başarısız oldu.');
    } finally {
      setActionLoading(false);
    }
  };

  if (!user) return null;

  // Event tipine göre ikon ve renk belirle
  const getEventMeta = (type) => {
    if (type.includes('voice')) return { icon: <Mic size={14} />, color: 'var(--accent-blue)', bg: 'var(--accent-blue-glow)' };
    if (type.includes('msg')) return { icon: <MessageSquare size={14} />, color: 'var(--accent-yellow)', bg: 'rgba(234, 179, 8, 0.2)' };
    if (type.includes('mod') || type.includes('warn')) return { icon: <ShieldAlert size={14} />, color: 'var(--accent-red)', bg: 'var(--accent-red-glow)' };
    if (type.includes('role')) return { icon: <Tag size={14} />, color: 'var(--accent-purple)', bg: 'var(--accent-purple-glow)' };
    if (type.includes('channel')) return { icon: <Hash size={14} />, color: '#10b981', bg: 'var(--accent-green-glow)' };
    return { icon: <Calendar size={14} />, color: '#fff', bg: 'rgba(255,255,255,0.1)' };
  };

  const parseDetails = (log) => {
      if (log.details_obj) {
          if (log.details_obj.content) return log.details_obj.content;
          if (log.details_obj.new_content) return "Mesajı Düzenledi: " + log.details_obj.new_content;
          if (log.details_obj.channel_name) return log.details_obj.channel_name;
          if (log.details_obj.role_name) return log.details_obj.role_name;
      }
      return log.details || "Detay yok";
  };

  return (
    <div style={{
      position: 'fixed', top: 0, right: 0, bottom: 0, width: '450px',
      background: 'rgba(10, 10, 12, 0.85)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)',
      borderLeft: '1px solid var(--panel-border)', zIndex: 1000,
      display: 'flex', flexDirection: 'column', boxShadow: '-10px 0 30px rgba(0,0,0,0.5)',
      animation: 'slideInRight 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
    }}>
      {/* Kapanış Butonu */}
      <button onClick={onClose} style={{
        position: 'absolute', top: '16px', right: '16px', background: 'rgba(255,255,255,0.1)',
        border: 'none', borderRadius: '50%', width: '32px', height: '32px', display: 'flex',
        alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer', transition: 'all 0.2s'
      }} onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.2)'}
         onMouseOut={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}>
        <X size={18} />
      </button>

      {/* Profil Header */}
      <div style={{ padding: '40px 24px 24px 24px', borderBottom: '1px solid var(--panel-border)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <img 
            src={user.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'} 
            style={{ width: '80px', height: '80px', borderRadius: '50%', border: '2px solid var(--panel-border-glow)', boxShadow: '0 0 20px rgba(0,0,0,0.3)', marginBottom: '16px', objectFit: 'cover' }} 
            alt="avatar" 
        />
        <h2 style={{ margin: '0 0 4px 0', fontSize: '1.4rem', fontFamily: 'Outfit, sans-serif' }}>{user.name}</h2>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontFamily: 'monospace', marginBottom: '16px' }}>{user.id}</span>
        
        {/* Current Roles */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', justifyContent: 'center' }}>
          {loadingRoles ? (
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Roller yükleniyor...</span>
          ) : currentRoles.length === 0 ? (
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Rol bulunamadı</span>
          ) : (
            currentRoles.map((role) => (
              <div key={role.role_id} style={{
                background: 'var(--accent-purple-glow)',
                border: '1px solid var(--accent-purple)',
                color: '#fff',
                padding: '4px 10px',
                borderRadius: '12px',
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                <Tag size={12} /> {role.role_name}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Aksiyon Butonları (Moderasyon) */}
      <div style={{ padding: '16px 24px', display: 'flex', gap: '8px', borderBottom: '1px solid var(--panel-border)', background: 'rgba(255,255,255,0.02)' }}>
        <button disabled={actionLoading} onClick={() => handleAction('mute')} style={{ flex: 1, background: 'rgba(234, 179, 8, 0.1)', border: '1px solid var(--accent-yellow)', color: 'var(--accent-yellow)', padding: '8px', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
          <ShieldAlert size={14} /> Sustur
        </button>
        <button disabled={actionLoading} onClick={() => handleAction('kick')} style={{ flex: 1, background: 'rgba(249, 115, 22, 0.1)', border: '1px solid #f97316', color: '#f97316', padding: '8px', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
          <ShieldX size={14} /> At
        </button>
        <button disabled={actionLoading} onClick={() => handleAction('ban')} style={{ flex: 1, background: 'rgba(244, 63, 94, 0.1)', border: '1px solid var(--accent-red)', color: 'var(--accent-red)', padding: '8px', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
          <Hammer size={14} /> Banla
        </button>
      </div>

      {/* Mini İstatistikler */}
      <div style={{ padding: '20px 24px', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', borderBottom: '1px solid var(--panel-border)' }}>
        <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '12px', padding: '12px', textAlign: 'center', border: '1px solid var(--panel-border)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '4px', textTransform: 'uppercase' }}>Ses İşlemi</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'var(--accent-blue)' }}>{stats.voiceCount}</div>
        </div>
        <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '12px', padding: '12px', textAlign: 'center', border: '1px solid var(--panel-border)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '4px', textTransform: 'uppercase' }}>Mesaj S/D</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'var(--accent-yellow)' }}>{stats.msgCount}</div>
        </div>
        <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '12px', padding: '12px', textAlign: 'center', border: '1px solid var(--panel-border)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '4px', textTransform: 'uppercase' }}>Kural İhlali</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'var(--accent-red)' }}>{stats.modCount}</div>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        
        {/* Admin Notları (Watchlist) */}
        <div style={{ padding: '24px', borderBottom: '1px solid var(--panel-border)' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Edit3 size={16} /> Admin Notları (Gözlem)
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '16px', maxHeight: '150px', overflowY: 'auto' }}>
            {loadingNotes ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Notlar yükleniyor...</div>
            ) : notes.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontStyle: 'italic' }}>Bu kullanıcı için henüz not eklenmemiş.</div>
            ) : (
              notes.map((n, i) => (
                <div key={i} style={{ background: 'rgba(59, 130, 246, 0.1)', borderLeft: '3px solid var(--accent-blue)', padding: '8px 12px', borderRadius: '4px', position: 'relative' }}>
                  <div style={{ fontSize: '0.9rem', color: '#fff', marginBottom: '4px', paddingRight: '24px' }}>{n.note}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{n.added_by} • {n.created_at}</div>
                  {(n.admin_id === currentAdminId || isOwner) && currentAdminId && (
                    <button 
                      onClick={() => handleDeleteNote(n.id)}
                      style={{ position: 'absolute', top: '8px', right: '8px', background: 'transparent', border: 'none', color: 'var(--accent-red)', cursor: 'pointer', padding: '4px' }}
                      title="Notu Sil"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              ))
            )}
          </div>

          <form onSubmit={handleAddNote} style={{ display: 'flex', gap: '8px' }}>
            <input 
              type="text" 
              value={newNote} 
              onChange={(e) => setNewNote(e.target.value)} 
              placeholder="Yeni not ekle..." 
              style={{ flex: 1, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', color: '#fff', padding: '10px 12px', borderRadius: '8px', fontSize: '0.9rem', outline: 'none' }} 
            />
            <button type="submit" style={{ background: 'var(--accent-blue)', border: 'none', color: '#fff', padding: '0 16px', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Send size={16} />
            </button>
          </form>
        </div>

        {/* Timeline Gövdesi */}
        <div style={{ padding: '24px' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
            <Calendar size={16} /> Son Hareketler
          </h3>
          
          {userLogs.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '20px' }}>Bu kullanıcıya ait log bulunamadı.</div>
          ) : (
            <div style={{ position: 'relative', paddingLeft: '20px' }}>
              {/* Timeline çizgisi */}
              <div style={{ position: 'absolute', left: '7px', top: '0', bottom: '0', width: '2px', background: 'var(--panel-border)' }}></div>
              
              {userLogs.slice(0, 100).map((log, idx) => {
                const meta = getEventMeta(log.event_type || '');
                return (
                  <div key={idx} style={{ position: 'relative', marginBottom: '24px' }}>
                    {/* Nokta */}
                    <div style={{ position: 'absolute', left: '-20px', top: '0', width: '16px', height: '16px', borderRadius: '50%', background: meta.bg, border: `2px solid ${meta.color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2 }}>
                      <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: meta.color }}></div>
                    </div>
                    
                    {/* İçerik */}
                    <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', borderRadius: '12px', padding: '12px', marginLeft: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '0.8rem', color: meta.color, display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '600', textTransform: 'uppercase' }}>
                          {meta.icon} {log.event_type?.replace(/_/g, ' ') || 'bilinmeyen'}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{formatTime(log.timestamp)}</span>
                      </div>
                      <div style={{ fontSize: '0.9rem', color: '#e2e8f0', wordBreak: 'break-word', lineHeight: '1.4' }}>
                        {parseDetails(log)}
                      </div>
                    </div>
                  </div>
                )
              })}
              {userLogs.length > 100 && (
                  <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '10px' }}>
                      ...ve {userLogs.length - 100} işlem daha.
                  </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserLookPanel;
