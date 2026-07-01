import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Command, Shield, Plus, X, Save, Loader, ChevronDown, ChevronUp } from 'lucide-react';
import { GUILD_ID, API_BASE_URL } from '../config';

const CommandManagementPage = () => {
  const [categories, setCategories] = useState({});
  const [expandedCats, setExpandedCats] = useState({});
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);

  useEffect(() => {
    fetchCommandPerms();
  }, []);

  const fetchCommandPerms = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/commands/${GUILD_ID}`);
      const perms = res.data.permissions || [];
      const catsData = res.data.categories || {};
      
      const mergedCats = {};
      const initialExpanded = {};

      for (const [catName, cmdList] of Object.entries(catsData)) {
        mergedCats[catName] = cmdList.map(cmd => {
          const dbPerm = perms.find(p => p.command_name === cmd.name);
          return {
            ...cmd,
            is_enabled: dbPerm ? (dbPerm.is_enabled === 1) : true,
            allowed_roles: dbPerm && dbPerm.allowed_roles && dbPerm.allowed_roles !== '[]' 
              ? JSON.parse(dbPerm.allowed_roles) 
              : []
          };
        });
        initialExpanded[catName] = false; // Default kapalı
      }
      
      setCategories(mergedCats);
      setExpandedCats(initialExpanded);
    } catch (err) {
      console.error('Komut izinleri çekilemedi:', err);
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

  const toggleCommand = (catName, cmdName) => {
    const updatedCats = { ...categories };
    const updatedList = updatedCats[catName].map(c => {
      if (c.name === cmdName) {
        const newCmd = { ...c, is_enabled: !c.is_enabled };
        updateCommandAPI(newCmd);
        return newCmd;
      }
      return c;
    });
    updatedCats[catName] = updatedList;
    setCategories(updatedCats);
  };

  const toggleMasterCategory = async (catName) => {
    const cmds = categories[catName];
    if (!cmds || cmds.length === 0) return;
    
    // Eğer hepsi açıksa kapat, biri bile kapalıysa aç
    const allEnabled = cmds.every(c => c.is_enabled);
    const targetState = !allEnabled;
    
    setSavingId(`master-${catName}`);
    
    const updatedCats = { ...categories };
    updatedCats[catName] = cmds.map(c => ({ ...c, is_enabled: targetState }));
    setCategories(updatedCats);
    
    const cmdNames = cmds.map(c => c.name);
    try {
      await axios.post(`${API_BASE_URL}/commands/category/${GUILD_ID}`, {
        commands: cmdNames,
        is_enabled: targetState ? 1 : 0
      });
    } catch (err) {
      console.error(err);
    } finally {
      setSavingId(null);
    }
  };

  const addRoleToCommand = (catName, cmdName, roleId) => {
    if (!roleId.trim()) return;
    const updatedCats = { ...categories };
    updatedCats[catName] = updatedCats[catName].map(c => {
      if (c.name === cmdName) {
        if (!c.allowed_roles.includes(roleId)) {
          const newCmd = { ...c, allowed_roles: [...c.allowed_roles, roleId] };
          updateCommandAPI(newCmd);
          return newCmd;
        }
      }
      return c;
    });
    setCategories(updatedCats);
  };

  const removeRoleFromCommand = (catName, cmdName, roleId) => {
    const updatedCats = { ...categories };
    updatedCats[catName] = updatedCats[catName].map(c => {
      if (c.name === cmdName) {
        const newCmd = { ...c, allowed_roles: c.allowed_roles.filter(id => id !== roleId) };
        updateCommandAPI(newCmd);
        return newCmd;
      }
      return c;
    });
    setCategories(updatedCats);
  };

  const toggleExpand = (catName) => {
    setExpandedCats(prev => ({ ...prev, [catName]: !prev[catName] }));
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {Object.entries(categories).map(([catName, cmds]) => {
            const isExpanded = expandedCats[catName];
            const allEnabled = cmds.every(c => c.is_enabled);
            const masterSaving = savingId === `master-${catName}`;

            return (
              <div key={catName} style={{ 
                background: 'rgba(0,0,0,0.4)', 
                borderRadius: '12px', 
                border: '1px solid var(--panel-border)',
                overflow: 'hidden'
              }}>
                {/* Category Header */}
                <div 
                  onClick={() => toggleExpand(catName)}
                  style={{ 
                    padding: '20px', 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    cursor: 'pointer',
                    borderBottom: isExpanded ? '1px solid var(--panel-border)' : 'none',
                    background: 'rgba(255,255,255,0.02)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {isExpanded ? <ChevronUp size={24} color="var(--text-secondary)" /> : <ChevronDown size={24} color="var(--text-secondary)" />}
                    <div>
                      <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>{catName}</h2>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {cmds.length} komut
                      </div>
                    </div>
                  </div>

                  {/* Master Toggle */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }} onClick={e => e.stopPropagation()}>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Ana Şalter</span>
                    <div 
                      onClick={() => toggleMasterCategory(catName)}
                      style={{
                        width: '48px', height: '26px', borderRadius: '13px',
                        backgroundColor: allEnabled ? 'var(--accent-green)' : 'rgba(255, 255, 255, 0.1)',
                        display: 'flex', alignItems: 'center', padding: '0 3px', cursor: 'pointer',
                        border: '1px solid', borderColor: allEnabled ? 'var(--accent-green-glow)' : 'rgba(255, 255, 255, 0.2)',
                        transition: 'all 0.3s ease',
                        boxShadow: allEnabled ? '0 0 12px var(--accent-green-glow)' : 'none'
                      }}
                    >
                      <motion.div
                        layout
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                        style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#fff', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }}
                        animate={{ x: allEnabled ? 20 : 0 }}
                      />
                    </div>
                    {masterSaving && <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} />}
                  </div>
                </div>

                {/* Commands Grid */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div 
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      style={{ overflow: 'hidden' }}
                    >
                      <div style={{ 
                        display: 'grid', 
                        gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', 
                        gap: '20px', 
                        padding: '20px' 
                      }}>
                        {cmds.map(cmd => (
                          <div 
                            key={cmd.name}
                            className="glass-panel"
                            style={{
                              padding: '20px',
                              borderRadius: '12px',
                              border: `1px solid ${cmd.is_enabled ? 'var(--panel-border-glow)' : 'var(--panel-border)'}`,
                              background: cmd.is_enabled ? 'rgba(0,0,0,0.2)' : 'rgba(0,0,0,0.5)',
                              opacity: cmd.is_enabled ? 1 : 0.6,
                              transition: 'all 0.3s ease'
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                              <div>
                                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: cmd.is_enabled ? '#fff' : 'var(--text-muted)' }}>
                                  /{cmd.name}
                                </div>
                                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                                  {cmd.desc}
                                </div>
                              </div>
                              
                              {/* Toggle Şalteri */}
                              <div 
                                onClick={() => toggleCommand(catName, cmd.name)}
                                style={{
                                  width: '40px', height: '22px', borderRadius: '11px',
                                  backgroundColor: cmd.is_enabled ? 'var(--accent-green)' : 'rgba(255, 255, 255, 0.1)',
                                  display: 'flex', alignItems: 'center', padding: '0 2px', cursor: 'pointer',
                                  border: '1px solid', borderColor: cmd.is_enabled ? 'var(--accent-green-glow)' : 'rgba(255, 255, 255, 0.2)',
                                  transition: 'all 0.3s ease', flexShrink: 0,
                                  boxShadow: cmd.is_enabled ? '0 0 8px var(--accent-green-glow)' : 'none'
                                }}
                              >
                                <motion.div
                                  layout
                                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                                  style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#fff', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }}
                                  animate={{ x: cmd.is_enabled ? 18 : 0 }}
                                />
                              </div>
                            </div>

                            {/* İzinli Roller */}
                            <div style={{ borderTop: '1px solid var(--panel-border)', paddingTop: '12px' }}>
                              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <Shield size={14} /> Ekstra Rol Kısıtlaması
                              </div>
                              
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
                                {cmd.allowed_roles.map(roleId => (
                                  <div key={roleId} style={{
                                    background: 'rgba(59, 130, 246, 0.15)', border: '1px solid var(--accent-blue)',
                                    color: 'var(--accent-blue)', padding: '2px 8px', borderRadius: '12px',
                                    fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px'
                                  }}>
                                    {roleId}
                                    <X size={10} style={{ cursor: 'pointer', opacity: 0.7 }} onClick={() => removeRoleFromCommand(catName, cmd.name, roleId)} />
                                  </div>
                                ))}
                                {cmd.allowed_roles.length === 0 && (
                                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>Boş (Bot varsayılan yetkileri geçerli)</span>
                                )}
                              </div>

                              {/* Rol Ekleme Input'u */}
                              <form 
                                onSubmit={(e) => {
                                  e.preventDefault();
                                  addRoleToCommand(catName, cmd.name, e.target.roleInput.value);
                                  e.target.roleInput.value = '';
                                }}
                                style={{ display: 'flex', gap: '6px' }}
                              >
                                <input 
                                  name="roleInput"
                                  disabled={!cmd.is_enabled}
                                  placeholder="Role ID ekle..."
                                  style={{
                                    flex: 1, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)',
                                    color: '#fff', padding: '6px 10px', borderRadius: '6px', fontSize: '0.85rem', outline: 'none'
                                  }}
                                />
                                <button type="submit" disabled={!cmd.is_enabled} style={{
                                  background: 'rgba(255,255,255,0.05)', border: '1px solid var(--panel-border)',
                                  color: '#fff', padding: '0 10px', borderRadius: '6px', cursor: cmd.is_enabled ? 'pointer' : 'not-allowed',
                                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                                }}>
                                  {savingId === cmd.name ? <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Plus size={14} />}
                                </button>
                              </form>
                            </div>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default CommandManagementPage;
