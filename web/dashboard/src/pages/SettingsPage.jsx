import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Settings, MessageSquare, Mic, Shield, Server, AlertTriangle, Ticket, UserCheck, UserPlus, Users, Hash, Loader, Headphones, Trash2, CheckCircle, FileText } from 'lucide-react';
import { API_BASE_URL } from '../config';
import { GuildContext } from '../GuildContext';

const MultiSelectDropdown = ({ options, selected, onChange, placeholder }) => {
  const [open, setOpen] = React.useState(false);
  const dropdownRef = React.useRef(null);

  React.useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const toggle = (val) => {
    if (selected.includes(val)) {
      onChange(selected.filter(i => i !== val));
    } else {
      onChange([...selected, val]);
    }
  };

  return (
    <div style={{ position: 'relative' }} ref={dropdownRef}>
      <div 
        onClick={() => setOpen(!open)}
        style={{ width: '100%', minHeight: '52px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--panel-border)', color: '#fff', fontSize: '1rem', padding: '10px 16px', borderRadius: '12px', cursor: 'pointer', display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}
      >
        {selected.length === 0 && <span style={{color: 'var(--text-muted)'}}>{placeholder}</span>}
        {selected.map(val => {
           const opt = options.find(o => o.value === val);
           return (
             <span key={val} style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', padding: '4px 10px', borderRadius: '8px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
               {opt ? opt.label : val}
               <span 
                 onClick={(e) => { e.stopPropagation(); toggle(val); }} 
                 style={{ cursor: 'pointer', color: '#ff4444', fontWeight: 'bold' }}
               >×</span>
             </span>
           );
        })}
      </div>
      {open && (
        <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, background: '#1e1e2e', border: '1px solid var(--panel-border)', borderRadius: '12px', marginTop: '8px', zIndex: 50, maxHeight: '250px', overflowY: 'auto', boxShadow: '0 8px 24px rgba(0,0,0,0.5)' }}>
          {options.length === 0 ? (
            <div style={{ padding: '12px 16px', color: 'var(--text-muted)' }}>Bulunamadı veya yükleniyor...</div>
          ) : (
            options.map(opt => (
              <div 
                key={opt.value}
                onClick={() => toggle(opt.value)}
                style={{ padding: '12px 16px', cursor: 'pointer', background: selected.includes(opt.value) ? 'rgba(255,255,255,0.08)' : 'transparent', color: opt.color || '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                onMouseOut={(e) => e.currentTarget.style.background = selected.includes(opt.value) ? 'rgba(255,255,255,0.08)' : 'transparent'}
              >
                <span>{opt.label}</span>
                {selected.includes(opt.value) && <CheckCircle size={16} color="var(--accent-green)" />}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

// ─── Kategori listesi ───────────────────────────────────────────────────────
const CATEGORIES = [
  { id: 'mesaj',   label: 'Mesaj Şalterleri',      icon: <MessageSquare size={18} />, channelKey: 'msg_channel'      },
  { id: 'ses',     label: 'Ses Şalterleri',         icon: <Mic size={18} />,          channelKey: 'ses_channel'      },
  { id: 'mod',     label: 'Moderatör Şalterleri',   icon: <Shield size={18} />,       channelKey: 'mod_channel'      },
  { id: 'sunucu',  label: 'Sunucu Şalterleri',      icon: <Server size={18} />,       channelKey: 'sunucu_channel'   },
  { id: 'uyari',   label: 'Uyarı Şalterleri',       icon: <AlertTriangle size={18} />,channelKey: 'uyari_channel'   },
  { id: 'ticket',  label: 'Ticket Şalterleri',      icon: <Ticket size={18} />,       channelKey: 'ticket_channel'   },
  { id: 'basvuru', label: 'Başvuru Şalterleri',     icon: <UserCheck size={18} />,    channelKey: 'basvuru_channel'  },
  { id: 'davet',   label: 'Davet Şalterleri',       icon: <UserPlus size={18} />,     channelKey: 'davet_channel'    },
  { id: 'rol',     label: 'Rol Geçmişi',            icon: <Users size={18} />,        channelKey: 'rol_channel'      },
  { id: 'oda',     label: 'Özel Oda Sistemi',       icon: <Headphones size={18} />,   channelKey: 'oda_channel'      },
];

// ─── ON/OFF şalterler ───────────────────────────────────────────────────────
const SETTINGS_MAP = {
  'mesaj': [
    { id: 'msg_delete_on', label: 'Silinen Mesajlar',      desc: 'Silinen mesajların loglanmasını açar veya kapatır.' },
    { id: 'msg_edit_on',   label: 'Düzenlenen Mesajlar',   desc: 'Düzenlenen mesajların önceki/sonraki hallerini loglar.' },
  ],
  'ses': [
    { id: 'ses_join_on',   label: 'Sese Katıl/Çık',        desc: 'Kullanıcıların ses kanallarına giriş ve çıkışlarını kaydeder.' },
    { id: 'ses_switch_on', label: 'Kanal Değiş',           desc: 'Kullanıcıların ses kanalları arasındaki geçişlerini kaydeder.' },
    { id: 'ses_stream_on', label: 'Yayın Açma',            desc: 'Ekran paylaşımı etkinliklerini kaydeder.' },
    { id: 'ses_camera_on', label: 'Kamera Açma',           desc: 'Kamera açma etkinliklerini kaydeder.' },
  ],
  'mod': [
    { id: 'mod_role_on',    label: 'Rol İşlemleri',        desc: 'Yetkililerin üyelere rol vermesi/alması.' },
    { id: 'mod_channel_on', label: 'Kanal İşlemleri',      desc: 'Yetkililerin kanalları silmesi, düzenlemesi vb.' },
    { id: 'mod_msg_on',     label: 'Mesaj Silme',          desc: 'Yetkililerin başka üyelerin mesajlarını silmesi.' },
  ],
  'sunucu': [
    { id: 'srv_update_on', label: 'Sunucu Ayarı',          desc: 'Sunucu ismi, ikon vb. değişiklikleri.' },
    { id: 'srv_emoji_on',  label: 'Emoji',                  desc: 'Emoji ekleme/silme olayları.' },
    { id: 'srv_role_on',   label: 'Toplu Rol',             desc: 'Rol silme, oluşturma gibi sunucu bazlı köklü rol olayları.' },
    { id: 'srv_perm_on',   label: 'Kanal İzni',            desc: 'Kanal izinlerinin değiştirilmesi.' },
  ],
  'uyari': [
    { id: 'warn_add_on',    label: 'Uyarı Ekleme',         desc: 'Kullanıcılara uyarı verildiğinde kaydeder.' },
    { id: 'warn_remove_on', label: 'Uyarı Silme',          desc: 'Kullanıcıların uyarıları silindiğinde kaydeder.' },
  ],
  'ticket': [
    { id: 'ticket_create_on', label: 'Ticket Açılışı',     desc: 'Yeni bir destek talebi (ticket) oluşturulduğunda kaydeder.' },
    { id: 'ticket_close_on',  label: 'Ticket Kapanışı',    desc: 'Destek talebi sonlandırıldığında kaydeder.' },
  ],
  'basvuru': [
    { id: 'app_create_on', label: 'Başvuru Yapıldı',        desc: 'Yeni bir başvuru formu gönderildiğinde kaydeder.' },
    { id: 'app_accept_on', label: 'Başvuru Onaylandı',      desc: 'Bir başvuru kabul edildiğinde kaydeder.' },
    { id: 'app_reject_on', label: 'Başvuru Reddedildi',     desc: 'Bir başvuru reddedildiğinde kaydeder.' },
  ],
  'davet': [
    { id: 'invite_create_on', label: 'Davet Oluşturuldu',  desc: 'Sunucuda yeni bir davet bağlantısı oluşturulduğunda kaydeder.' },
    { id: 'invite_use_on',    label: 'Davet Kullanıldı',   desc: 'Bir kullanıcı davet bağlantısıyla sunucuya katıldığında kaydeder.' },
  ],
  'rol': [
    { id: 'role_add_on',    label: 'Rol Verildi',           desc: 'Kullanıcılara yeni rol eklendiğinde kaydeder.' },
    { id: 'role_remove_on', label: 'Rol Alındı',            desc: 'Kullanıcılardan rol çıkarıldığında kaydeder.' },
  ],
  'oda': [
    { id: 'oda_create_on',  label: 'Oda Oluşturma',         desc: 'Özel ses odası oluşturulma olaylarını kaydeder.' },
    { id: 'oda_delete_on',  label: 'Oda Silinme',           desc: 'Özel ses odalarının silinme/kapanma olaylarını kaydeder.' },
    { id: 'oda_update_on',  label: 'Oda Güncelleme',        desc: 'Oda kilitleme, limit/isim değiştirme gibi eylemleri kaydeder.' },
  ],
};

const MotionToggle = ({ isOn, toggle }) => (
  <motion.div
    onClick={toggle}
    style={{
      width: '48px', height: '26px', borderRadius: '13px',
      backgroundColor: isOn ? 'var(--accent-green)' : 'rgba(255, 255, 255, 0.1)',
      display: 'flex', alignItems: 'center', padding: '0 3px', cursor: 'pointer',
      border: '1px solid', borderColor: isOn ? 'var(--accent-green-glow)' : 'rgba(255, 255, 255, 0.2)',
      transition: 'background-color 0.3s ease', boxShadow: isOn ? '0 0 12px var(--accent-green-glow)' : 'none',
      flexShrink: 0
    }}
  >
    <motion.div
      layout
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
      style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#fff', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }}
      animate={{ x: isOn ? 20 : 0 }}
    />
  </motion.div>
);

const SettingsPage = () => {
  const { activeGuildId } = useContext(GuildContext);
  const navigate = useNavigate();
  const [activeCategory, setActiveCategory] = useState('mesaj');
  const [settings, setSettings] = useState({});
  const [channelSettings, setChannelSettings] = useState({});
  const [availableChannels, setAvailableChannels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [channelLoading, setChannelLoading] = useState(false);
  const [privateVoice, setPrivateVoice] = useState(null);
  const [pvLoading, setPvLoading] = useState(false);
  const [ticketSettings, setTicketSettings] = useState({});
  const [ticketSaving, setTicketSaving] = useState(false);
  
  // Discord Channels for Manual Private Voice Setup
  const [discordCats, setDiscordCats] = useState([]);
  const [discordVoices, setDiscordVoices] = useState([]);
  const [discordRoles, setDiscordRoles] = useState([]);
  const [discordMembers, setDiscordMembers] = useState([]);
  const [selectedCat, setSelectedCat] = useState("");
  const [selectedVoice, setSelectedVoice] = useState("");


  useEffect(() => {
    setLoading(true);

    if (!activeGuildId) return;
    const fetchSettings = axios.get(`${API_BASE_URL}/settings/${activeGuildId}`)
      .then(res => {
        setSettings(res.data.settings || {});
        setChannelSettings(res.data.channels || {});
        setPrivateVoice(res.data.private_voice || null);
        setTicketSettings(res.data.ticket_settings || {});
        if (res.data.private_voice) {
          setSelectedCat(res.data.private_voice.category_id || "");
          setSelectedVoice(res.data.private_voice.hub_id || "");
        }
      });

    const fetchChannels = axios.get(`${API_BASE_URL}/channels/${activeGuildId}`)
      .then(res => setAvailableChannels(res.data.channels || []));

    const fetchDiscordChannels = axios.get(`${API_BASE_URL}/discord-channels/${activeGuildId}`)
      .then(res => {
        if(res.data.categories) setDiscordCats(res.data.categories);
        if(res.data.voice_channels) setDiscordVoices(res.data.voice_channels);
      })
      .catch(err => console.error("Discord kanalları çekilemedi:", err));

    const fetchRoles = axios.get(`${API_BASE_URL}/discord-roles/${activeGuildId}`)
      .then(res => setDiscordRoles(res.data || []))
      .catch(err => console.error("Roller çekilemedi:", err));

    const fetchMembers = axios.get(`${API_BASE_URL}/discord-members/${activeGuildId}`)
      .then(res => setDiscordMembers(res.data || []))
      .catch(err => console.error("Üyeler çekilemedi:", err));

    Promise.all([fetchSettings, fetchChannels, fetchDiscordChannels, fetchRoles, fetchMembers])
      .catch(err => console.error('Ayarlar yüklenemedi:', err))
      .finally(() => setLoading(false));
  }, [activeGuildId]);


  const handleSetupPrivateVoice = async () => {
    setPvLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/settings/oda-kurulum/${activeGuildId}`);
      setPrivateVoice({ hub_id: res.data.hub_id, category_id: res.data.category_id });
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Kurulum sırasında bir hata oluştu.");
    } finally {
      setPvLoading(false);
    }
  };

  const handleManualSetupPrivateVoice = async () => {
    if (!selectedCat || !selectedVoice) {
      alert("Lütfen hem kategori hem de oluşturma kanalı seçin.");
      return;
    }
    setPvLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/settings/oda-kurulum/manual/${activeGuildId}`, {
        category_id: selectedCat,
        hub_id: selectedVoice
      });
      setPrivateVoice({ hub_id: selectedVoice, category_id: selectedCat });
      alert("Manuel oda sistemi başarıyla yapılandırıldı.");
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.error || "Kurulum sırasında bir hata oluştu.");
    } finally {
      setPvLoading(false);
    }
  };

  const handleDeletePrivateVoice = async () => {
    setPvLoading(true);
    try {
      await axios.delete(`${API_BASE_URL}/settings/oda-kurulum/${activeGuildId}`);
      setPrivateVoice(null);
    } catch (err) {
      console.error(err);
      alert("Silme sırasında bir hata oluştu.");
    } finally {
      setPvLoading(false);
    }
  };

  const handleTicketSettingChange = (field, value) => {
    setTicketSettings(prev => ({...prev, [field]: value}));
  };

  const getParsedArray = (val) => {
    if (!val) return [];
    try {
      const parsed = JSON.parse(val);
      return Array.isArray(parsed) ? parsed : [val];
    } catch {
      return [val];
    }
  };

  const handleTicketMultiSelect = (key, selectedOptions) => {
    const values = Array.from(selectedOptions, option => option.value);
    setTicketSettings(prev => ({ ...prev, [key]: JSON.stringify(values) }));
  };

  const handleTicketSave = async () => {
    setTicketSaving(true);
    try {
      await axios.post(`${API_BASE_URL}/settings/tickets/${activeGuildId}`, ticketSettings);
      alert("Ticket ayarları başarıyla kaydedildi!");
    } catch (err) {
      console.error(err);
      alert("Ticket ayarları kaydedilemedi.");
    } finally {
      setTicketSaving(false);
    }
  };

  const toggleSetting = async (settingName) => {
    const current  = settings[settingName] || 'off';
    const newState = current === 'on' ? 'off' : 'on';
    setSettings(prev => ({ ...prev, [settingName]: newState }));
    try {
      await axios.post(`${API_BASE_URL}/settings/${activeGuildId}`, {
        setting_name: settingName,
        state: newState,
      });
    } catch (err) {
      console.error('Şalter güncellenemedi:', err);
      setSettings(prev => ({ ...prev, [settingName]: current }));
    }
  };

  const handleChannelChange = async (columnKey, channelId) => {
    const prev = channelSettings[columnKey];
    const newVal = channelId || null;
    setChannelSettings(p => ({ ...p, [columnKey]: newVal }));
    setChannelLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/channel-setting/${activeGuildId}`, {
        column: columnKey,
        channel_id: newVal,
      });
    } catch (err) {
      console.error('Kanal güncellenemedi:', err);
      setChannelSettings(p => ({ ...p, [columnKey]: prev }));
    } finally {
      setChannelLoading(false);
    }
  };

  const activeCat = CATEGORIES.find(c => c.id === activeCategory);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '24px', boxSizing: 'border-box' }}>
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Settings size={32} color="var(--accent-blue)" /> Sistem Ayarları
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>Botun genel ayarlarını ve loglama kurallarını yönetin.</p>
      </header>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', gap: '24px' }}>
        {/* Sol Menü (Kategoriler) */}
        <div className="glass-panel" style={{ width: '280px', borderRadius: '16px', padding: '20px 12px', display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '12px', paddingLeft: '12px', textTransform: 'uppercase', letterSpacing: '1px' }}>
            Log Şalterleri
          </div>
          {CATEGORIES.map(cat => {
            const isActive = activeCategory === cat.id;
            return (
              <motion.div
                key={cat.id}
                whileHover={{ scale: 1.02, x: 4 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setActiveCategory(cat.id)}
                style={{
                  padding: '12px 16px', borderRadius: '12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px',
                  fontWeight: 600, fontSize: '0.95rem', color: isActive ? 'var(--accent-green)' : 'var(--text-secondary)',
                  background: isActive ? 'rgba(16, 185, 129, 0.1)' : 'transparent',
                  border: `1px solid ${isActive ? 'var(--accent-green-glow)' : 'transparent'}`,
                  transition: 'background 0.2s, color 0.2s'
                }}
              >
                {cat.icon} {cat.label}
              </motion.div>
            );
          })}
        </div>

        {/* Ana İçerik */}
        <div className="glass-panel" style={{ flex: 1, borderRadius: '16px', padding: '32px', overflowY: 'auto' }}>
          {loading ? (
            <div style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} /> Ayarlar Yükleniyor...
            </div>
          ) : activeCategory === 'oda' ? (
            <motion.div key="oda" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3 }}>
              <h2 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#fff', marginBottom: '32px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Headphones size={28} color="var(--accent-green)" />
                Özel Oda Sistemi
              </h2>
              
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '24px', borderRadius: '16px', border: '1px solid var(--panel-border)' }}>
                {(!privateVoice || !privateVoice.hub_id) ? (
                  <div>
                    <div style={{ fontSize: '1.1rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                      Özel oda sistemi şu anda bu sunucuda kurulu değil. 
                      Kullanıcıların kendilerine özel geçici ses kanalları açabilmesi için sistemi aktif edebilirsiniz.
                    </div>
                    <button 
                      onClick={handleSetupPrivateVoice}
                      disabled={pvLoading}
                      style={{
                        padding: '12px 24px', background: 'var(--accent-green)', color: '#fff', fontWeight: 600,
                        border: 'none', borderRadius: '8px', cursor: pvLoading ? 'not-allowed' : 'pointer',
                        display: 'flex', alignItems: 'center', gap: '8px', opacity: pvLoading ? 0.7 : 1
                      }}
                    >
                      {pvLoading ? <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <Headphones size={18} />}
                      ✨ Otomatik Kurulum Yap
                    </button>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '12px' }}>
                      Not: Bu butona bastığınızda sunucunuzda otomatik olarak <strong>🎙️ Özel Odalar</strong> kategorisi ve <strong>➕ Oda Oluştur</strong> ses kanalı oluşturulacaktır.
                    </div>
                  </div>
                ) : (
                  <div>
                    <div style={{ fontSize: '1.1rem', color: 'var(--accent-green)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '1.3rem' }}>✅</span> Sistem Aktif ve Çalışıyor
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '12px', marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div style={{ color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>Kategori ID:</span> 
                        <code style={{ background: 'rgba(0,0,0,0.3)', padding: '4px 8px', borderRadius: '6px', color: '#fff' }}>{privateVoice.category_id}</code>
                        </div>
                        <div style={{ color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>Hub (Oluşturma) Kanalı ID:</span> 
                        <code style={{ background: 'rgba(0,0,0,0.3)', padding: '4px 8px', borderRadius: '6px', color: '#fff' }}>{privateVoice.hub_id}</code>
                        </div>
                    </div>
                    
                    <button 
                      onClick={handleDeletePrivateVoice}
                      disabled={pvLoading}
                      style={{
                        padding: '10px 20px', background: 'rgba(244, 63, 94, 0.1)', color: 'var(--accent-red)', fontWeight: 600,
                        border: '1px solid var(--accent-red)', borderRadius: '8px', cursor: pvLoading ? 'not-allowed' : 'pointer',
                        display: 'flex', alignItems: 'center', gap: '8px', opacity: pvLoading ? 0.7 : 1
                      }}
                    >
                      {pvLoading ? <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <Trash2 size={18} />}
                      Sistemi Kapat / Sıfırla
                    </button>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                      Not: Bu işlem sadece sistem kaydını siler. Kanalları Discord üzerinden manuel silebilirsiniz.
                    </div>
                  </div>
                )}
                
                <div style={{ marginTop: '32px', paddingTop: '32px', borderTop: '1px solid var(--panel-border)' }}>
                    <h3 style={{ fontSize: '1.2rem', color: '#fff', marginBottom: '16px' }}>Manuel Kurulum / Değiştirme</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                       <div>
                         <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 600 }}>Özel Odalar Kategorisi</label>
                         <select 
                           value={selectedCat} 
                           onChange={e => setSelectedCat(e.target.value)} 
                           style={{
                             width: '100%', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--panel-border)',
                             color: '#fff', fontSize: '1rem', padding: '12px 16px', borderRadius: '12px', appearance: 'none', outline: 'none'
                           }}
                         >
                            <option value="" style={{ background: 'var(--bg-color)' }}>— Kategori Seçin —</option>
                            {discordCats.map(c => <option key={c.id} value={c.id} style={{ background: 'var(--bg-color)' }}>{c.name}</option>)}
                         </select>
                       </div>
                       <div>
                         <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 600 }}>Oda Oluşturma Kanalı</label>
                         <select 
                           value={selectedVoice} 
                           onChange={e => setSelectedVoice(e.target.value)} 
                           style={{
                             width: '100%', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--panel-border)',
                             color: '#fff', fontSize: '1rem', padding: '12px 16px', borderRadius: '12px', appearance: 'none', outline: 'none'
                           }}
                         >
                            <option value="" style={{ background: 'var(--bg-color)' }}>— Ses Kanalı Seçin —</option>
                            {discordVoices.map(c => <option key={c.id} value={c.id} style={{ background: 'var(--bg-color)' }}>{c.name}</option>)}
                         </select>
                       </div>
                       <button 
                         onClick={handleManualSetupPrivateVoice} 
                         disabled={pvLoading} 
                         style={{
                           padding: '12px 24px', background: 'var(--accent-blue)', color: '#fff', fontWeight: 600,
                           border: 'none', borderRadius: '8px', cursor: pvLoading ? 'not-allowed' : 'pointer',
                           alignSelf: 'flex-start', marginTop: '8px'
                         }}
                       >
                         {pvLoading ? 'Kaydediliyor...' : 'Kaydet / Güncelle'}
                       </button>
                    </div>
                </div>
              </div>

              {/* ── Discord Oda Log Kanalı Seçici ── */}
              <div style={{ marginTop: '40px', background: 'rgba(0,0,0,0.2)', padding: '24px', borderRadius: '16px', border: '1px solid var(--panel-border)' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  <Hash size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} /> Özel Oda Log Kanalı
                </div>

                {availableChannels.length === 0 ? (
                  <div style={{ fontSize: '0.9rem', color: 'var(--accent-yellow)', padding: '12px', background: 'rgba(234, 179, 8, 0.1)', borderRadius: '8px', border: '1px solid rgba(234, 179, 8, 0.2)' }}>
                    ⚠️ Kanal listesi boş — bot çevrimiçi değil veya henüz kanal verisi çekilemedi.
                  </div>
                ) : (
                  <div style={{ position: 'relative' }}>
                    <select
                      value={channelSettings['oda_channel'] || ''}
                      onChange={e => handleChannelChange('oda_channel', e.target.value)}
                      style={{
                        width: '100%', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--panel-border)',
                        color: '#fff', fontSize: '1rem', padding: '12px 16px', borderRadius: '12px', appearance: 'none', outline: 'none', cursor: 'pointer', transition: 'border-color 0.2s', fontFamily: 'inherit'
                      }}
                      onFocus={(e) => e.target.style.borderColor = 'var(--accent-blue)'}
                      onBlur={(e) => e.target.style.borderColor = 'var(--panel-border)'}
                    >
                      <option value="" style={{ background: 'var(--bg-color)' }}>— Kanal Seçilmedi (Log Gönderilmez) —</option>
                      {availableChannels.map(ch => (
                        <option key={ch.channel_id} value={ch.channel_id} style={{ background: 'var(--bg-color)' }}>
                          # {ch.channel_name}
                        </option>
                      ))}
                    </select>
                    <div style={{ position: 'absolute', right: '16px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
                       {channelLoading
                          ? (<Loader size={16} style={{ color: 'var(--text-secondary)' }} />)
                          : (<Hash size={16} color="var(--text-muted)" />)
                       }
                    </div>
                  </div>
                )}

                {channelSettings['oda_channel'] && (
                  <div style={{ fontSize: '0.85rem', color: 'var(--accent-green)', marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    ✓ Seçili kanal ID: {channelSettings['oda_channel']}
                    <span style={{ color: 'var(--accent-red)', cursor: 'pointer', fontWeight: 600, padding: '4px 8px', background: 'rgba(244, 63, 94, 0.1)', borderRadius: '6px' }} onClick={() => handleChannelChange('oda_channel', null)}>
                      Temizle
                    </span>
                  </div>
                )}
              </div>

              {/* ── Log Şalterleri ── */}
              <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {SETTINGS_MAP['oda'].map(setting => {
                  const isOn = settings[setting.id] === 1;
                  return (
                    <div key={setting.id} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', padding: '16px 20px', borderRadius: '12px'
                    }}>
                      <div>
                        <div style={{ color: '#fff', fontWeight: 600, fontSize: '1.05rem', marginBottom: '4px' }}>{setting.label}</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{setting.desc}</div>
                      </div>
                      <MotionToggle isOn={isOn} toggle={() => handleToggle(setting.id, isOn)} />
                    </div>
                  );
                })}
              </div>

            </motion.div>
          ) : (
            <motion.div key={activeCategory} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3 }}>
              <h2 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#fff', marginBottom: '32px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                {React.cloneElement(activeCat.icon, { size: 28, color: 'var(--accent-green)' })}
                {activeCat?.label}
              </h2>

              {/* ── Discord Kanal Seçici ── */}
              <div style={{ marginBottom: '40px', background: 'rgba(0,0,0,0.2)', padding: '24px', borderRadius: '16px', border: '1px solid var(--panel-border)' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  <Hash size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} /> Discord Log Kanalı
                </div>

                {availableChannels.length === 0 ? (
                  <div style={{ fontSize: '0.9rem', color: 'var(--accent-yellow)', padding: '12px', background: 'rgba(234, 179, 8, 0.1)', borderRadius: '8px', border: '1px solid rgba(234, 179, 8, 0.2)' }}>
                    ⚠️ Kanal listesi boş — bot çevrimiçi değil veya henüz kanal verisi çekilemedi.
                  </div>
                ) : (
                  <div style={{ position: 'relative' }}>
                    <select
                      value={channelSettings[activeCat?.channelKey] || ''}
                      onChange={e => handleChannelChange(activeCat.channelKey, e.target.value)}
                      style={{
                        width: '100%', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--panel-border)',
                        color: '#fff', fontSize: '1rem', padding: '12px 16px', borderRadius: '12px', appearance: 'none', outline: 'none', cursor: 'pointer', transition: 'border-color 0.2s', fontFamily: 'inherit'
                      }}
                      onFocus={(e) => e.target.style.borderColor = 'var(--accent-blue)'}
                      onBlur={(e) => e.target.style.borderColor = 'var(--panel-border)'}
                    >
                      <option value="" style={{ background: 'var(--bg-color)' }}>— Kanal Seçilmedi (Log Gönderilmez) —</option>
                      {availableChannels.map(ch => (
                        <option key={ch.channel_id} value={ch.channel_id} style={{ background: 'var(--bg-color)' }}>
                          # {ch.channel_name}
                        </option>
                      ))}
                    </select>
                    <div style={{ position: 'absolute', right: '16px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
                       {channelLoading
                          ? (<Loader size={16} style={{ color: 'var(--text-secondary)' }} />)
                          : (<Hash size={16} color="var(--text-muted)" />)
                       }
                    </div>
                  </div>
                )}

                {channelSettings[activeCat?.channelKey] && (
                  <div style={{ fontSize: '0.85rem', color: 'var(--accent-green)', marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    ✓ Seçili kanal ID: {channelSettings[activeCat?.channelKey]}
                    <span style={{ color: 'var(--accent-red)', cursor: 'pointer', fontWeight: 600, padding: '4px 8px', background: 'rgba(244, 63, 94, 0.1)', borderRadius: '6px' }} onClick={() => handleChannelChange(activeCat.channelKey, null)}>
                      Temizle
                    </span>
                  </div>
                )}
              </div>

              
              {/* ── Şalterler ── */}
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Veritabanı Loglama Şalterleri
                </div>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '24px' }}>
                  Bu şalterler web dashboard üzerinde gösterilmek üzere log kaydı tutulmasını sağlar.
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {(SETTINGS_MAP[activeCategory] || []).map(item => {
                    const isOn = settings[item.id] === 'on';
                    return (
                      <div 
                        key={item.id} 
                        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', borderRadius: '16px', transition: 'background 0.2s' }}
                        onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.04)'}
                        onMouseOut={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                      >
                        <div style={{ paddingRight: '24px' }}>
                          <div style={{ fontSize: '1.05rem', color: '#fff', marginBottom: '6px', fontWeight: 600 }}>{item.label}</div>
                          <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>{item.desc}</div>
                        </div>
                        <MotionToggle isOn={isOn} toggle={() => toggleSetting(item.id)} />
                      </div>
                    );
                  })}
                </div>
              </div>

              {activeCategory === 'ticket' && (
                <div style={{ marginTop: '40px', background: 'rgba(0,0,0,0.2)', padding: '24px', borderRadius: '16px', border: '1px solid var(--panel-border)' }}>
                  <h3 style={{ fontSize: '1.4rem', color: '#fff', marginBottom: '24px' }}>Destek Talebi (Ticket) Sistemi Kurulumu</h3>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                     <div>
                       <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 600 }}>Ticket Kategorisi</label>
                       <select 
                         value={ticketSettings.category_id || ''} 
                         onChange={e => handleTicketSettingChange('category_id', e.target.value)} 
                         style={{ width: '100%', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--panel-border)', color: '#fff', fontSize: '1rem', padding: '12px 16px', borderRadius: '12px' }}
                       >
                          <option value="" style={{ background: 'var(--bg-color)' }}>— Kategori Seçin —</option>
                          {discordCats.map(c => <option key={c.id} value={c.id} style={{ background: 'var(--bg-color)' }}>{c.name}</option>)}
                       </select>
                     </div>

                     <div>
                       <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 600 }}>Destek Rolleri (Birden fazla seçebilirsiniz)</label>
                       <MultiSelectDropdown 
                         options={discordRoles.map(r => ({ value: r.id, label: r.name, color: r.color ? `#${r.color.toString(16).padStart(6, '0')}` : '#fff' }))}
                         selected={getParsedArray(ticketSettings.support_role_id)}
                         onChange={(selected) => setTicketSettings(prev => ({ ...prev, support_role_id: JSON.stringify(selected) }))}
                         placeholder="— Rol Seçin —"
                       />
                     </div>

                     <div>
                       <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 600 }}>Destek Kullanıcıları (Özel izin, opsiyonel)</label>
                       <MultiSelectDropdown 
                         options={discordMembers.map(m => ({ value: m.id, label: m.username }))}
                         selected={getParsedArray(ticketSettings.support_user_ids)}
                         onChange={(selected) => setTicketSettings(prev => ({ ...prev, support_user_ids: JSON.stringify(selected) }))}
                         placeholder="— Kullanıcı Seçin —"
                       />
                     </div>

                     <div>
                       <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 600 }}>Gözetmen/Yönetici Rolleri (Bilet sahiplenilse bile odada kalır)</label>
                       <MultiSelectDropdown 
                         options={discordRoles.map(r => ({ value: r.id, label: r.name, color: r.color ? `#${r.color.toString(16).padStart(6, '0')}` : '#fff' }))}
                         selected={getParsedArray(ticketSettings.admin_role_id)}
                         onChange={(selected) => setTicketSettings(prev => ({ ...prev, admin_role_id: JSON.stringify(selected) }))}
                         placeholder="— Yönetici/Gözetmen Rolü Seçin —"
                       />
                     </div>

                     <div>
                       <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 600 }}>Ticket Log Kanalı</label>
                       <select 
                         value={ticketSettings.log_channel_id || ''} 
                         onChange={e => handleTicketSettingChange('log_channel_id', e.target.value)} 
                         style={{ width: '100%', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--panel-border)', color: '#fff', fontSize: '1rem', padding: '12px 16px', borderRadius: '12px' }}
                       >
                          <option value="" style={{ background: 'var(--bg-color)' }}>— Metin Kanalı Seçin —</option>
                          {availableChannels.map(c => <option key={c.channel_id} value={c.channel_id} style={{ background: 'var(--bg-color)' }}># {c.channel_name}</option>)}
                       </select>
                     </div>

                     <div>
                       <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 600 }}>Panel Başlığı</label>
                       <input 
                         type="text" 
                         value={ticketSettings.panel_title || ''} 
                         onChange={e => handleTicketSettingChange('panel_title', e.target.value)} 
                         placeholder="🎟️ Destek Merkezi"
                         style={{ width: '100%', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--panel-border)', color: '#fff', fontSize: '1rem', padding: '12px 16px', borderRadius: '12px' }}
                       />
                     </div>

                     <div>
                       <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 600 }}>Panel Açıklaması</label>
                       <textarea 
                         value={ticketSettings.panel_desc || ''} 
                         onChange={e => handleTicketSettingChange('panel_desc', e.target.value)} 
                         placeholder="Sorunuz mu var? Destek ekibimizle iletişime geçmek için butona tıklayın."
                         style={{ width: '100%', height: '80px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--panel-border)', color: '#fff', fontSize: '1rem', padding: '12px 16px', borderRadius: '12px', resize: 'vertical' }}
                       />
                     </div>
                     
                     <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)'}}>
                        Not: Ayarları kaydettikten sonra Discord'da destek kanalına giderek <code>f.ticket setup</code> komutunu kullanın. Panel oraya gönderilecektir.
                     </div>

                     <button 
                       onClick={handleTicketSave} 
                       disabled={ticketSaving} 
                       style={{
                         padding: '12px 24px', background: 'var(--accent-green)', color: '#fff', fontWeight: 600,
                         border: 'none', borderRadius: '8px', cursor: ticketSaving ? 'not-allowed' : 'pointer',
                         alignSelf: 'flex-start', marginTop: '8px'
                       }}
                     >
                       {ticketSaving ? 'Kaydediliyor...' : 'Ticket Ayarlarını Kaydet'}
                     </button>
                  </div>
                </div>
              )}

              {activeCategory === 'basvuru' && (
                <div style={{ marginTop: '40px', background: 'rgba(0,0,0,0.2)', padding: '24px', borderRadius: '16px', border: '1px solid var(--panel-border)' }}>
                  <h3 style={{ fontSize: '1.4rem', color: '#fff', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileText size={24} color="var(--accent-blue)" /> Başvuru (Form) Sistemi Kurulumu
                  </h3>
                  <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: '1.6' }}>
                    Başvuru formları, itiraf sistemi veya rol seçim formları oluşturmak; log kanallarını ve bu formların Discord'a düşeceği hedefleri yapılandırmak için Form Yönetimi panelini kullanabilirsiniz.
                  </p>
                  <button 
                    onClick={() => navigate('/dashboard/forms')} 
                    style={{
                      padding: '12px 24px', background: 'var(--accent-blue)', color: '#fff', fontWeight: 600,
                      border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px'
                    }}
                  >
                    <FileText size={18} /> Form Yönetimine Git
                  </button>
                </div>
              )}

          </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
