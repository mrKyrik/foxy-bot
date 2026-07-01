import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { X, Settings, Shield, Server, Video, Ticket } from 'lucide-react';
import { API_BASE_URL } from '../config';

const SETTINGS_MAP = [
  {
    category: "Mesaj Logları",
    icon: <Settings size={18} color="#3b82f6" />,
    items: [
      { id: "msg_delete_on", label: "Mesaj Silinme", desc: "Üyelerin kendi mesajlarını silmesi." },
      { id: "msg_edit_on", label: "Mesaj Düzenlenme", desc: "Üyelerin mesajlarını düzenlemesi." }
    ]
  },
  {
    category: "Ses Logları",
    icon: <Video size={18} color="#10b981" />,
    items: [
      { id: "ses_join_on", label: "Kanala Giriş", desc: "Kullanıcıların ses kanalına katılması." },
      { id: "ses_leave_on", label: "Kanaldan Çıkış", desc: "Kullanıcıların ses kanalından ayrılması." },
      { id: "ses_change_on", label: "Kanal Değiştirme", desc: "Kullanıcıların bir ses kanalından diğerine geçmesi." },
      { id: "ses_stream_on", label: "Kamera/Yayın", desc: "Ses kanalında kamera açma veya yayın başlatma." }
    ]
  },
  {
    category: "Moderatör Logları",
    icon: <Shield size={18} color="#f43f5e" />,
    items: [
      { id: "mod_role_on", label: "Yetkili Rol Verme/Alma", desc: "Yetkililerin diğer üyelere rol vermesi/alması." },
      { id: "mod_channel_on", label: "Yetkili Kanal İşlemleri", desc: "Kanal oluşturma, silme veya düzenleme olayları." },
      { id: "mod_msg_on", label: "Başkasının Mesajını Silme", desc: "Yetkili birinin başka birinin mesajını silmesi." }
    ]
  },
  {
    category: "Sunucu Logları",
    icon: <Server size={18} color="#06b6d4" />,
    items: [
      { id: "srv_update_on", label: "Sunucu Güncelleme", desc: "İsim veya ikon değişiklikleri." },
      { id: "srv_emoji_on", label: "Emoji İşlemleri", desc: "Sunucuya yeni emoji eklenmesi veya silinmesi." },
      { id: "srv_role_on", label: "Rol Oluşturma/Silme", desc: "Sunucuda köklü rol değişiklikleri." },
      { id: "srv_perm_on", label: "Kanal İzinleri", desc: "Kanal izinlerinin değiştirilmesi." }
    ]
  },
  {
    category: "Davet ve Başvuru",
    icon: <Ticket size={18} color="#eab308" />,
    items: [
      { id: "invite_use_on", label: "Davet Kullanımı", desc: "Kullanıcıların sunucuya kimin davetiyle girdiği." },
      { id: "app_accept_on", label: "Başvuru Kabul", desc: "Forumda onaylanan yetkili başvuruları." },
      { id: "app_reject_on", label: "Başvuru Ret", desc: "Forumda reddedilen yetkili başvuruları." }
    ]
  },
  {
    category: "Diğer Ayarlar",
    icon: <Settings size={18} color="#8b5cf6" />,
    items: [
      { id: "ticket_on", label: "Ticket Logları", desc: "Ticket oluşturma ve kapatma olayları." },
      { id: "role_add_on", label: "Genel Rol Ekleme", desc: "Kullanıcılara otomatik eklenen genel roller." },
      { id: "role_remove_on", label: "Genel Rol Alınma", desc: "Kullanıcılardan otomatik alınan genel roller." }
    ]
  }
];

const SettingsModal = ({ isOpen, onClose, guildId }) => {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      axios.get(`${API_BASE_URL}/settings/${guildId}`)
        .then(res => {
          setSettings(res.data.settings || {});
        })
        .catch(err => console.error("Ayarlar çekilemedi:", err))
        .finally(() => setLoading(false));
    }
  }, [isOpen, guildId]);

  const toggleSetting = async (settingName) => {
    const currentState = settings[settingName] || "off";
    const newState = currentState === "on" ? "off" : "on";
    
    // Optimistic UI update
    setSettings(prev => ({ ...prev, [settingName]: newState }));

    try {
      await axios.post(`${API_BASE_URL}/settings/${guildId}`, {
        setting_name: settingName,
        state: newState
      });
    } catch (err) {
      console.error("Ayar güncellenemedi:", err);
      // Revert on failure
      setSettings(prev => ({ ...prev, [settingName]: currentState }));
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.6)',
      backdropFilter: 'blur(10px)',
      display: 'flex', justifyContent: 'center', alignItems: 'center',
      zIndex: 9999,
      animation: 'fadeIn 0.3s ease'
    }}>
      <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        
        .toggle-switch {
          position: relative;
          width: 48px;
          height: 24px;
          border-radius: 12px;
          background-color: #374151;
          cursor: pointer;
          transition: background-color 0.3s;
        }
        .toggle-switch.on { background-color: #10b981; }
        
        .toggle-knob {
          position: absolute;
          top: 2px;
          left: 2px;
          width: 20px;
          height: 20px;
          background-color: white;
          border-radius: 50%;
          transition: transform 0.3s;
        }
        .toggle-switch.on .toggle-knob {
          transform: translateX(24px);
        }
      `}</style>
      
      <div className="glass-panel" style={{
        width: '75%', maxHeight: '80vh',
        display: 'flex', flexDirection: 'column',
        animation: 'slideUp 0.4s ease',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '16px',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '24px 32px', borderBottom: '1px solid rgba(255,255,255,0.1)',
          background: 'rgba(0,0,0,0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ background: 'rgba(255,255,255,0.1)', padding: '10px', borderRadius: '12px' }}>
              <Settings size={28} color="#fff" />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: '#fff' }}>Sistem Ayarları</h2>
              <span style={{ color: '#aaa', fontSize: '0.9rem' }}>Veritabanı loglama seçeneklerini yapılandırın</span>
            </div>
          </div>
          <button onClick={onClose} style={{
            background: 'transparent', border: 'none', color: '#ccc',
            cursor: 'pointer', padding: '8px', borderRadius: '50%',
            transition: 'background 0.2s'
          }} onMouseOver={e => e.currentTarget.style.background='rgba(255,255,255,0.1)'} 
             onMouseOut={e => e.currentTarget.style.background='transparent'}>
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '32px', overflowY: 'auto', flex: 1 }}>
          {loading ? (
            <div style={{ textAlign: 'center', color: '#aaa', padding: '40px' }}>Ayarlar Yükleniyor...</div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '32px' }}>
              {SETTINGS_MAP.map((group, idx) => (
                <div key={idx} style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '12px', padding: '24px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px', color: '#fff', fontSize: '1.1rem' }}>
                    {group.icon} {group.category}
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {group.items.map(item => {
                      const isOn = settings[item.id] === "on";
                      return (
                        <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ flex: 1, paddingRight: '16px' }}>
                            <div style={{ color: '#eee', fontWeight: '500', marginBottom: '4px' }}>{item.label}</div>
                            <div style={{ color: '#888', fontSize: '0.85rem' }}>{item.desc}</div>
                          </div>
                          <div 
                            className={`toggle-switch ${isOn ? 'on' : ''}`} 
                            onClick={() => toggleSetting(item.id)}
                          >
                            <div className="toggle-knob"></div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
