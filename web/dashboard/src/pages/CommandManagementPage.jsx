import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Command, Shield, Plus, X, Save, Loader } from 'lucide-react';
import { GUILD_ID, API_BASE_URL } from '../config';

// ── Varsayılan Bot Komutları Listesi ──
// Eğer veritabanında henüz ayar yoksa, arayüzde bu listeyi göstereceğiz
const DEFAULT_COMMANDS = [
  { name: 'ban', desc: 'Bir kullanıcıyı sunucudan yasaklar.' },
  { name: 'kick', desc: 'Bir kullanıcıyı sunucudan atar.' },
  { name: 'mute', desc: 'Bir kullanıcıyı metin/ses kanallarında susturur.' },
  { name: 'timeout', desc: 'Kullanıcıya geçici süreli timeout atar.' },
  { name: 'clear', desc: 'Belirtilen sayıda mesajı temizler.' },
  { name: 'lock', desc: 'Kanalı kilitler.' },
  { name: 'unlock', desc: 'Kanal kilidini açar.' },
  { name: 'warn', desc: 'Kullanıcıya uyarı ekler.' },
];

const CommandManagementPage = () => {
  const [commands, setCommands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);

  // Sayfa yüklendiğinde DB'den mevcut ayarları çek
  useEffect(() => {
    fetchCommandPerms();
  }, []);

  const fetchCommandPerms = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/commands/${GUILD_ID}`);
      const perms = res.data.permissions || [];
      
      // DB'deki ayarlar ile varsayılan komutları birleştir
      const merged = DEFAULT_COMMANDS.map(cmd => {
        const dbPerm = perms.find(p => p.command_name === cmd.name);
        return {
          ...cmd,
          is_enabled: dbPerm ? (dbPerm.is_enabled === 1) : true,
          allowed_roles: dbPerm && dbPerm.allowed_roles && dbPerm.allowed_roles !== '[]' 
            ? JSON.parse(dbPerm.allowed_roles) 
            : []
        };
      });
      setCommands(merged);
    } catch (err) {
      console.error('Komut izinleri çekilemedi:', err);
      // Hata olsa da en azından varsayılan listeyi gösterelim
      setCommands(DEFAULT_COMMANDS.map(c => ({ ...c, is_enabled: true, allowed_roles: [] })));
    } finally {
      setLoading(false);
    }
  };

  const updateCommandAPI = async (cmdToUpdate) => {
    setSavingId(cmdToUpdate.name);
    try {
      await axios.post(`${API_BASE_URL}/commands/${GUILD_ID}`, {
        command_name: cmdToUpdate.name,
        is_enabled: cmdToUpdate.is_enabled ? 1 : 0,
        allowed_roles: JSON.stringify(cmdToUpdate.allowed_roles)
      });
    } catch (err) {
      console.error('Komut güncellenemedi:', err);
    } finally {
      setSavingId(null);
    }
  };

  const toggleCommand = (cmdName) => {
    const updated = commands.map(c => {
      if (c.name === cmdName) {
        const newCmd = { ...c, is_enabled: !c.is_enabled };
        updateCommandAPI(newCmd); // API'ye gönder
        return newCmd;
      }
      return c;
    });
    setCommands(updated);
  };

  const addRoleToCommand = (cmdName, roleId) => {
    if (!roleId.trim()) return;
    const updated = commands.map(c => {
      if (c.name === cmdName) {
        if (!c.allowed_roles.includes(roleId)) {
          const newCmd = { ...c, allowed_roles: [...c.allowed_roles, roleId] };
          updateCommandAPI(newCmd);
          return newCmd;
        }
      }
      return c;
    });
    setCommands(updated);
  };

  const removeRoleFromCommand = (cmdName, roleId) => {
    const updated = commands.map(c => {
      if (c.name === cmdName) {
        const newCmd = { ...c, allowed_roles: c.allowed_roles.filter(id => id !== roleId) };
        updateCommandAPI(newCmd);
        return newCmd;
      }
      return c;
    });
    setCommands(updated);
  };

  return (
    <div style={{ padding: '32px', color: '#fff', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
      <header style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Command size={32} color="var(--accent-green)" />
          Komut Yönetimi
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>
          Hangi komutun açık olacağını ve hangi roller tarafından kullanılabileceğini belirleyin.
        </p>
      </header>

      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text-secondary)' }}>
          <Loader size={24} style={{ animation: 'spin 1s linear infinite' }} /> Komut ayarları yükleniyor...
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '24px' }}>
          {commands.map(cmd => (
            <motion.div 
              key={cmd.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-panel"
              style={{
                padding: '24px',
                borderRadius: '16px',
                border: `1px solid ${cmd.is_enabled ? 'var(--panel-border-glow)' : 'var(--panel-border)'}`,
                background: cmd.is_enabled ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.6)',
                opacity: cmd.is_enabled ? 1 : 0.7,
                transition: 'all 0.3s ease'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: cmd.is_enabled ? '#fff' : 'var(--text-muted)' }}>
                    /{cmd.name}
                  </div>
                  <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    {cmd.desc}
                  </div>
                </div>
                
                {/* Toggle Şalteri */}
                <div 
                  onClick={() => toggleCommand(cmd.name)}
                  style={{
                    width: '48px', height: '26px', borderRadius: '13px',
                    backgroundColor: cmd.is_enabled ? 'var(--accent-green)' : 'rgba(255, 255, 255, 0.1)',
                    display: 'flex', alignItems: 'center', padding: '0 3px', cursor: 'pointer',
                    border: '1px solid', borderColor: cmd.is_enabled ? 'var(--accent-green-glow)' : 'rgba(255, 255, 255, 0.2)',
                    transition: 'all 0.3s ease', flexShrink: 0,
                    boxShadow: cmd.is_enabled ? '0 0 12px var(--accent-green-glow)' : 'none'
                  }}
                >
                  <motion.div
                    layout
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                    style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#fff', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }}
                    animate={{ x: cmd.is_enabled ? 20 : 0 }}
                  />
                </div>
              </div>

              {/* İzinli Roller */}
              <div style={{ borderTop: '1px solid var(--panel-border)', paddingTop: '16px' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Shield size={14} /> İzinli Roller (Boşsa herkes kullanabilir)
                </div>
                
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                  {cmd.allowed_roles.map(roleId => (
                    <div key={roleId} style={{
                      background: 'rgba(59, 130, 246, 0.15)', border: '1px solid var(--accent-blue)',
                      color: 'var(--accent-blue)', padding: '4px 10px', borderRadius: '20px',
                      fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px'
                    }}>
                      {roleId}
                      <X size={12} style={{ cursor: 'pointer', opacity: 0.7 }} onClick={() => removeRoleFromCommand(cmd.name, roleId)} />
                    </div>
                  ))}
                  {cmd.allowed_roles.length === 0 && (
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>Kısıtlama yok</span>
                  )}
                </div>

                {/* Rol Ekleme Input'u */}
                <form 
                  onSubmit={(e) => {
                    e.preventDefault();
                    addRoleToCommand(cmd.name, e.target.roleInput.value);
                    e.target.roleInput.value = '';
                  }}
                  style={{ display: 'flex', gap: '8px' }}
                >
                  <input 
                    name="roleInput"
                    disabled={!cmd.is_enabled}
                    placeholder="Role ID ekle..."
                    style={{
                      flex: 1, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)',
                      color: '#fff', padding: '8px 12px', borderRadius: '8px', fontSize: '0.9rem', outline: 'none'
                    }}
                  />
                  <button type="submit" disabled={!cmd.is_enabled} style={{
                    background: 'rgba(255,255,255,0.05)', border: '1px solid var(--panel-border)',
                    color: '#fff', padding: '0 12px', borderRadius: '8px', cursor: cmd.is_enabled ? 'pointer' : 'not-allowed',
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                  }}>
                    {savingId === cmd.name ? <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Plus size={16} />}
                  </button>
                </form>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CommandManagementPage;
