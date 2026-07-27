import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Command, Shield, Plus, X, Loader, Search, Users, Hash, Check } from 'lucide-react';
import { API_BASE_URL } from '../config';
import { GuildContext } from '../GuildContext';
import './CommandManagement.css';

// ── Role Search Component ──
const RoleSearch = ({ onSelect, placeholder, disabled, currentRoles = [] }) => {
  const { activeGuildId } = useContext(GuildContext);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (query.trim().length === 0) {
      if (results.length !== 0) setResults([]);
      return;
    }
    const fetchRoles = async () => {
      setLoading(true);
      try {
        if (!activeGuildId) return;
        const res = await axios.get(`${API_BASE_URL}/roles/${activeGuildId}?q=${query}`);
        const filtered = (res.data.roles || []).filter(r => !currentRoles.includes(r.role_id));
        setResults(filtered);
      } catch (err) {
        console.error('Roller aranırken hata:', err);
      } finally {
        setLoading(false);
      }
    };
    const timer = setTimeout(fetchRoles, 300);
    return () => clearTimeout(timer);
  }, [query, activeGuildId, currentRoles]);

  return (
    <div ref={dropdownRef} style={{ position: 'relative', width: '100%' }}>
      <Search size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
      <input
        disabled={disabled}
        value={query}
        onChange={e => {
          setQuery(e.target.value);
          setShowDropdown(true);
        }}
        onFocus={() => { if (query) setShowDropdown(true); }}
        placeholder={placeholder || "Rol Ara..."}
        style={{
          width: '100%', padding: '8px 12px 8px 32px',
          background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)',
          color: '#fff', borderRadius: '8px', outline: 'none', fontSize: '0.85rem'
        }}
      />
      {loading && <Loader size={12} style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', animation: 'spin 1s linear infinite', color: 'var(--text-secondary)' }} />}

      <AnimatePresence>
        {showDropdown && results.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            style={{
              position: 'absolute', zIndex: 10, width: '100%', marginTop: '4px',
              background: 'var(--panel-bg)', border: '1px solid var(--panel-border)',
              borderRadius: '8px', overflow: 'hidden', boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
            }}
          >
            <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
              {results.map(role => (
                <div
                  key={role.role_id}
                  onClick={() => {
                    onSelect(role.role_id, role.role_name);
                    setQuery('');
                    setShowDropdown(false);
                  }}
                  style={{
                    padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '8px',
                    cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.02)', color: '#fff', fontSize: '0.85rem'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: role.role_color ? `#${role.role_color.toString(16)}` : '#99aab5' }} />
                  {role.role_name}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const CommandManagementPage = () => {
  const { activeGuildId, guildPermission } = useContext(GuildContext);
  const [categories, setCategories] = useState({});
  const [activeCategory, setActiveCategory] = useState(null);
  const [globalSearch, setGlobalSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [roleCache, setRoleCache] = useState({});

  const fetchCommandPerms = async () => {
    setLoading(true);
    try {
      if (!activeGuildId) return;
      const res = await axios.get(`${API_BASE_URL}/commands/${activeGuildId}`);
      const perms = res.data.permissions || [];
      const catsData = res.data.categories || {};
      
      const mergedCats = {};
      for (const [catName, cmdList] of Object.entries(catsData)) {
        mergedCats[catName] = cmdList.map(cmd => {
          const dbPerm = perms.find(p => p.command_name === cmd.name);
          let parsedRoles = [];
          if (dbPerm && dbPerm.allowed_roles && dbPerm.allowed_roles !== '[]') {
            try {
              parsedRoles = JSON.parse(dbPerm.allowed_roles);
            } catch (parseErr) {
              console.error(`Error parsing roles for ${cmd.name}:`, parseErr);
            }
          }
          return {
            ...cmd,
            is_enabled: dbPerm ? (dbPerm.is_enabled === 1) : true,
            allowed_roles: parsedRoles
          };
        });
      }
      
      setCategories(mergedCats);
      const catNames = Object.keys(mergedCats);
      if (catNames.length > 0) {
        setActiveCategory(catNames[0]);
      }
    } catch (err) {
      console.error('Komut izinleri çekilemedi:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCommandPerms();
  }, [activeGuildId]);

  const updateCommandAPI = async (cmdToUpdate) => {
    setSavingId(cmdToUpdate.name);
    try {
      await axios.post(`${API_BASE_URL}/commands/${activeGuildId}`, {
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
    if (guildPermission === 'read') return;
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
    if (guildPermission === 'read') return;
    const cmds = categories[catName];
    if (!cmds || cmds.length === 0) return;
    
    const allEnabled = cmds.every(c => c.is_enabled);
    const targetState = !allEnabled;
    
    setSavingId(`master-${catName}`);
    
    const updatedCats = { ...categories };
    updatedCats[catName] = cmds.map(c => ({ ...c, is_enabled: targetState }));
    setCategories(updatedCats);
    
    const cmdNames = cmds.map(c => c.name);
    try {
      await axios.post(`${API_BASE_URL}/commands/category/${activeGuildId}`, {
        commands: cmdNames,
        is_enabled: targetState ? 1 : 0
      });
    } catch (err) {
      console.error(err);
    } finally {
      setSavingId(null);
    }
  };

  const addRoleToCommand = (catName, cmdName, roleId, roleName) => {
    if (guildPermission === 'read') return;
    if (!roleId) return;
    if (roleName) setRoleCache(prev => ({ ...prev, [roleId]: roleName }));

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
    if (guildPermission === 'read') return;
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

  const addRoleToCategory = async (catName, roleId, roleName) => {
    if (!roleId) return;
    if (roleName) setRoleCache(prev => ({ ...prev, [roleId]: roleName }));
    
    setSavingId(`catRole-${catName}`);
    const cmds = categories[catName];
    const cmdNames = cmds.map(c => c.name);
    
    const updatedCats = { ...categories };
    updatedCats[catName] = cmds.map(c => {
      if (!c.allowed_roles.includes(roleId)) {
        return { ...c, allowed_roles: [...c.allowed_roles, roleId] };
      }
      return c;
    });
    setCategories(updatedCats);

    try {
      await axios.post(`${API_BASE_URL}/commands/category/${activeGuildId}/roles`, {
        commands: cmdNames,
        role_id: roleId
      });
    } catch (err) {
      console.error(err);
    } finally {
      setSavingId(null);
    }
  };

  const removeRoleFromCategory = async (catName, roleId) => {
    if (!roleId) return;
    
    setSavingId(`catRoleRem-${catName}-${roleId}`);
    const cmds = categories[catName];
    const cmdNames = cmds.map(c => c.name);
    
    const updatedCats = { ...categories };
    updatedCats[catName] = cmds.map(c => {
      if (c.allowed_roles.includes(roleId)) {
        return { ...c, allowed_roles: c.allowed_roles.filter(r => r !== roleId) };
      }
      return c;
    });
    setCategories(updatedCats);

    try {
      await axios.post(`${API_BASE_URL}/commands/category/${activeGuildId}/roles/remove`, {
        commands: cmdNames,
        role_id: roleId
      });
    } catch (err) {
      console.error(err);
    } finally {
      setSavingId(null);
    }
  };

  const categoryNames = Object.keys(categories);
  
  const getFilteredCommands = () => {
    if (!activeCategory || !categories[activeCategory]) return [];
    let cmds = categories[activeCategory];
    if (globalSearch.trim() !== '') {
      const q = globalSearch.toLowerCase();
      cmds = cmds.filter(c => c.name.toLowerCase().includes(q) || c.desc.toLowerCase().includes(q));
    }
    return cmds;
  };

  const categoryRoles = React.useMemo(() => {
    if (!activeCategory || !categories[activeCategory]) return [];
    const rolesSet = new Set();
    categories[activeCategory].forEach(cmd => {
      cmd.allowed_roles.forEach(r => rolesSet.add(r));
    });
    return Array.from(rolesSet);
  }, [activeCategory, categories]);

  const activeCommands = getFilteredCommands();
  const allEnabled = activeCategory && categories[activeCategory] && categories[activeCategory].length > 0 && categories[activeCategory].every(c => c.is_enabled);

  if (loading) {
    return (
      <div style={{ padding: '32px', color: 'var(--text-secondary)' }}>Yükleniyor...</div>
    );
  }

  return (
    <div style={{ padding: '32px', height: '100%', overflowY: 'auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Command size={32} color="var(--color-cyan)" /> Komut Yönetimi
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>
            Sunucunuzdaki bot komutlarını kategoriler halinde yönetin ve rol bazlı erişim atayın.
          </p>
        </div>
        <div style={{ position: 'relative', width: '250px' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
          <input 
            type="text" 
            placeholder="Komut Ara..." 
            value={globalSearch}
            onChange={(e) => setGlobalSearch(e.target.value)}
            style={{
              width: '100%', padding: '10px 12px 10px 36px',
              background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)',
              color: '#fff', borderRadius: '8px', outline: 'none'
            }}
          />
        </div>
      </header>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', paddingBottom: '12px', marginBottom: '24px', borderBottom: '1px solid var(--panel-border)' }}>
        {categoryNames.map(cat => (
          <button
            key={cat}
            onClick={() => { setActiveCategory(cat); setGlobalSearch(''); }}
            style={{
              background: activeCategory === cat ? 'rgba(0, 210, 255, 0.1)' : 'transparent',
              color: activeCategory === cat ? 'var(--color-cyan)' : 'var(--text-secondary)',
              border: `1px solid ${activeCategory === cat ? 'var(--color-cyan)' : 'transparent'}`,
              padding: '8px 16px',
              borderRadius: '99px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s'
            }}
          >
            <Hash size={16} />
            {cat}
            <span style={{ 
              background: activeCategory === cat ? 'var(--color-cyan)' : 'rgba(255,255,255,0.1)', 
              color: activeCategory === cat ? '#000' : 'var(--text-secondary)', 
              padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem' 
            }}>
              {categories[cat].length}
            </span>
          </button>
        ))}
      </div>

      {activeCategory && (
        <>
          <div className="glass-panel" style={{ padding: '24px', borderRadius: '16px', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 style={{ fontSize: '1.2rem', color: '#fff', marginBottom: '8px' }}>{activeCategory} Kategorisi Seçenekleri</h2>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <div style={{ width: '220px' }}>
                  <RoleSearch 
                    placeholder="Tüm kategoriye rol ekle..." 
                    onSelect={(rId, rName) => addRoleToCategory(activeCategory, rId, rName)}
                  />
                </div>
                {savingId === `catRole-${activeCategory}` && <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} />}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                Kategoriyi {allEnabled ? 'Kapat' : 'Aç'}
              </span>
              <div 
                className={`toggle-switch ${allEnabled ? 'on' : ''} ${guildPermission === 'read' ? 'disabled' : ''}`}
                onClick={() => toggleMasterCategory(activeCategory)}
                style={{ cursor: guildPermission === 'read' ? 'not-allowed' : 'pointer', opacity: guildPermission === 'read' ? 0.6 : 1 }}
              >
                <motion.div
                  layout
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  className="toggle-thumb"
                  animate={{ x: allEnabled ? 20 : 0 }}
                />
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
            <AnimatePresence>
              {activeCommands.map(cmd => (
                <motion.div 
                  key={cmd.name}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="glass-panel"
                  style={{ 
                    padding: '20px', borderRadius: '12px', display: 'flex', flexDirection: 'column', gap: '16px',
                    border: `1px solid ${cmd.is_enabled ? 'var(--panel-border)' : 'rgba(239, 68, 68, 0.2)'}`,
                    opacity: cmd.is_enabled ? 1 : 0.6
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: '4px' }}>/{cmd.name}</div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{cmd.desc}</div>
                    </div>
                    <div 
                      className={`toggle-switch ${cmd.is_enabled ? 'on' : ''} ${guildPermission === 'read' ? 'disabled' : ''}`}
                      onClick={() => toggleCommand(activeCategory, cmd.name)}
                      style={{ cursor: guildPermission === 'read' ? 'not-allowed' : 'pointer', opacity: guildPermission === 'read' ? 0.6 : 1 }}
                    >
                      <motion.div
                        layout
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                        className="toggle-thumb"
                        animate={{ x: cmd.is_enabled ? 20 : 0 }}
                      />
                    </div>
                  </div>

                  <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '16px' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Shield size={14} /> Erişim Rolleri
                    </div>
                    
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
                      {cmd.allowed_roles.map(roleId => (
                        <div key={roleId} style={{ 
                          background: 'rgba(0,0,0,0.3)', border: '1px solid var(--panel-border)', padding: '4px 8px',
                          borderRadius: '6px', fontSize: '0.75rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '6px'
                        }}>
                          {roleCache[roleId] ? roleCache[roleId] : roleId}
                          {guildPermission !== 'read' && (
                            <X size={12} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => removeRoleFromCommand(activeCategory, cmd.name, roleId)} />
                          )}
                        </div>
                      ))}
                      {cmd.allowed_roles.length === 0 && (
                        <span style={{
                          padding: '4px 10px', 
                          background: cmd.default_access === 'owner' ? 'rgba(234, 179, 8, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                          color: cmd.default_access === 'owner' ? 'var(--accent-yellow)' : 'var(--color-cyan)',
                          borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600
                        }}>
                          Varsayılan: {cmd.default_access === 'owner' ? '🔒 Sadece Yöneticiler' : '🌍 Herkese Açık'}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <RoleSearch 
                        onSelect={(roleId, roleName) => addRoleToCommand(activeCategory, cmd.name, roleId, roleName)} 
                        placeholder="Erişim izni için rol ekle..."
                        currentRoles={cmd.allowed_roles}
                        disabled={guildPermission === 'read' || !cmd.is_enabled}
                      />
                      {savingId === cmd.name && <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            
            {activeCommands.length === 0 && (
              <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                Aradığınız kriterlere uygun komut bulunamadı.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default CommandManagementPage;
