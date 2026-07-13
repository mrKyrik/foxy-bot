import React, { useState, useEffect } from 'react';
import { Settings, Users, Activity, Loader, Trash2, UserMinus } from 'lucide-react';

const RoomAdminPanel = ({ channelId, guildId }) => {
  const [liveData, setLiveData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const token = localStorage.getItem('kumiho_token');

  const fetchLiveData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/api/voice_rooms/${channelId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setLiveData(data);
      }
    } catch (err) {
      setError("Bağlantı hatası: Veri çekilemedi.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLiveData();
  }, [channelId]);

  const handleDeleteRoom = async () => {
    if (!window.confirm("Bu odayı zorla silmek istediğinize emin misiniz?")) return;
    try {
      const res = await fetch(`http://localhost:8000/api/voice_rooms/${channelId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        setError("Oda başarıyla silindi.");
        setLiveData(null);
      } else {
        alert("Hata: " + data.error);
      }
    } catch (err) {
      alert("Silme işlemi başarısız.");
    }
  };

  const handleKickUser = async (userId, userName) => {
    if (!window.confirm(`${userName} adlı kullanıcıyı odadan atmak istiyor musunuz?`)) return;
    try {
      const res = await fetch(`http://localhost:8000/api/voice_rooms/${channelId}/kick/${userId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        alert("Kullanıcı atıldı.");
        fetchLiveData(); // Yenile
      } else {
        alert("Hata: " + data.error);
      }
    } catch (err) {
      alert("Atma işlemi başarısız.");
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '16px', color: 'var(--text-secondary)' }}>
        <Loader className="animate-spin" size={16} /> Canlı Veri Bekleniyor...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '16px', color: 'var(--accent-red)', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)', marginTop: '16px' }}>
        ⚠️ {error}
      </div>
    );
  }

  if (!liveData) return null;

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '16px', border: '1px solid rgba(255,255,255,0.05)', marginTop: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', paddingBottom: '12px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <h4 style={{ margin: 0, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={18} color="var(--accent-green)" /> Canlı Oda Durumu
        </h4>
        <div style={{ display: 'flex', gap: '12px' }}>
            <button 
                onClick={fetchLiveData}
                style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: 'var(--text-secondary)', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.85rem' }}>
                🔄 Yenile
            </button>
            <button 
                onClick={handleDeleteRoom}
                style={{ background: 'var(--accent-red)', border: 'none', color: '#fff', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                <Trash2 size={14} /> Zorla Sil
            </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '16px' }}>
        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Kapasite</span>
          <div style={{ fontSize: '1.2rem', fontWeight: 600, color: '#fff', marginTop: '4px' }}>
            {liveData.user_limit === 0 ? 'Sınırsız' : `${liveData.members.length} / ${liveData.user_limit}`}
          </div>
        </div>
        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Ses Kalitesi</span>
          <div style={{ fontSize: '1.2rem', fontWeight: 600, color: '#fff', marginTop: '4px' }}>
            {Math.round(liveData.bitrate / 1000)} kbps
          </div>
        </div>
      </div>

      <div>
        <h5 style={{ color: 'var(--text-secondary)', marginBottom: '12px', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Users size={16} /> İçerideki Kullanıcılar ({liveData.members.length})
        </h5>
        
        {liveData.members.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>Oda şu an boş...</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {liveData.members.map(m => (
              <div key={m.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '8px 12px', borderRadius: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {m.avatar ? 
                    <img src={m.avatar} alt={m.name} style={{ width: '28px', height: '28px', borderRadius: '50%' }} /> :
                    <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px' }}>?</div>
                  }
                  <span style={{ color: '#fff', fontWeight: 500 }}>{m.name}</span>
                </div>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ display: 'flex', gap: '8px', fontSize: '1.1rem' }}>
                    {m.video ? '📹' : ''}
                    {m.stream ? '📺' : ''}
                    {m.mute ? '🔇' : ''}
                    {m.deaf ? '🎧' : ''}
                  </div>
                  <button 
                    onClick={() => handleKickUser(m.id, m.name)}
                    style={{ background: 'transparent', border: '1px solid rgba(239, 68, 68, 0.5)', color: 'var(--accent-red)', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }}
                    title="Odadan At"
                  >
                    <UserMinus size={14} /> At
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RoomAdminPanel;
