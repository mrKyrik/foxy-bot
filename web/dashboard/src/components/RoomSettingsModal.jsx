import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Settings, X, Save, Lock, Unlock, Eye, EyeOff, Users, Headphones } from 'lucide-react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import { GuildContext } from '../GuildContext';

const RoomSettingsModal = ({ isOpen, onClose, userId, userName }) => {
  const { activeGuildId } = React.useContext(GuildContext);
  const [settings, setSettings] = useState({
    room_name: '',
    user_limit: 0,
    bitrate: 64000,
    is_locked: false,
    is_hidden: false
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen && userId) {
      fetchSettings();
    }
  }, [isOpen, userId]);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/voice_settings/${userId}`);
      if (res.data && !res.data.error) {
        setSettings({
          room_name: res.data.room_name || '',
          user_limit: res.data.user_limit || 0,
          bitrate: res.data.bitrate || 64000,
          is_locked: res.data.is_locked || false,
          is_hidden: res.data.is_hidden || false
        });
      } else {
        // Varsayılan değerler
        setSettings({
          room_name: `${userName}'in Odası`,
          user_limit: 0,
          bitrate: 64000,
          is_locked: false,
          is_hidden: false
        });
      }
    } catch (err) {
      console.error("Error fetching room settings", err);
    }
    setLoading(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const url = activeGuildId 
        ? `${API_BASE_URL}/voice_settings/${userId}?guild_id=${activeGuildId}`
        : `${API_BASE_URL}/voice_settings/${userId}`;
      await axios.patch(url, settings);
      onClose();
    } catch (err) {
      console.error("Error saving room settings", err);
    }
    setSaving(false);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 99999
        }}
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          style={{
            background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '16px', padding: '24px', width: '400px', maxWidth: '90%',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
          }}
          onClick={e => e.stopPropagation()}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Settings size={20} color="var(--accent-blue)" />
              Oda Ayarları ({userName})
            </h2>
            <button onClick={onClose} style={{ background: 'transparent', border: 'none', padding: '4px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
              <X size={20} />
            </button>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-secondary)' }}>Yükleniyor...</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              {/* Oda Adı */}
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Oda Adı</label>
                <input
                  type="text"
                  value={settings.room_name}
                  onChange={e => setSettings({...settings, room_name: e.target.value})}
                  placeholder="Kullanıcının Oda Adı"
                  style={{ width: '100%', padding: '10px 14px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff', outline: 'none' }}
                />
              </div>

              {/* Kullanıcı Limiti */}
              <div>
                <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Users size={16} /> Kullanıcı Limiti</span>
                  <span style={{ color: 'var(--accent-blue)' }}>{settings.user_limit === 0 ? 'Sınırsız' : settings.user_limit}</span>
                </label>
                <input
                  type="range"
                  min="0" max="99"
                  value={settings.user_limit}
                  onChange={e => setSettings({...settings, user_limit: parseInt(e.target.value)})}
                  style={{ width: '100%', accentColor: 'var(--accent-blue)' }}
                />
              </div>

              {/* Bitrate */}
              <div>
                <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Headphones size={16} /> Bitrate</span>
                  <span style={{ color: 'var(--accent-purple)' }}>{Math.round(settings.bitrate / 1000)} kbps</span>
                </label>
                <input
                  type="range"
                  min="8000" max="96000" step="1000"
                  value={settings.bitrate}
                  onChange={e => setSettings({...settings, bitrate: parseInt(e.target.value)})}
                  style={{ width: '100%', accentColor: 'var(--accent-purple)' }}
                />
              </div>

              {/* Toggles */}
              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  onClick={() => setSettings({...settings, is_locked: !settings.is_locked})}
                  style={{
                    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                    padding: '12px', borderRadius: '8px', border: 'none', cursor: 'pointer',
                    background: settings.is_locked ? 'rgba(244, 63, 94, 0.2)' : 'rgba(255,255,255,0.05)',
                    color: settings.is_locked ? 'var(--accent-red)' : 'var(--text-secondary)',
                    transition: 'all 0.2s'
                  }}
                >
                  {settings.is_locked ? <Lock size={18} /> : <Unlock size={18} />}
                  {settings.is_locked ? 'Kilitli' : 'Açık'}
                </button>

                <button
                  onClick={() => setSettings({...settings, is_hidden: !settings.is_hidden})}
                  style={{
                    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                    padding: '12px', borderRadius: '8px', border: 'none', cursor: 'pointer',
                    background: settings.is_hidden ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255,255,255,0.05)',
                    color: settings.is_hidden ? 'var(--accent-blue)' : 'var(--text-secondary)',
                    transition: 'all 0.2s'
                  }}
                >
                  {settings.is_hidden ? <EyeOff size={18} /> : <Eye size={18} />}
                  {settings.is_hidden ? 'Gizli' : 'Görünür'}
                </button>
              </div>

              {/* Save Button */}
              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  width: '100%', padding: '12px', borderRadius: '8px', border: 'none', cursor: 'pointer',
                  background: 'var(--accent-green)', color: '#000', fontWeight: 600,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                  marginTop: '12px', opacity: saving ? 0.7 : 1
                }}
              >
                <Save size={18} />
                {saving ? 'Kaydediliyor...' : 'Ayarları Kaydet'}
              </button>

            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default RoomSettingsModal;
