import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Command, Shield, Plus, X, Loader, Search, Users, Hash } from 'lucide-react';
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
      if (results.length !== 0) {
        setResults([]);
      }
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, activeGuildId]);

  return (
    <div ref={dropdownRef} className="role-search-wrapper">
      <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
      <input
        className="role-search-input"
        disabled={disabled}
        value={query}
        onChange={e => {
          setQuery(e.target.value);
          setShowDropdown(true);
        }}
        onFocus={() => { if (query) setShowDropdown(true); }}
        placeholder={placeholder || "Rol Ara..."}
      />
      {loading && <Loader size={12} style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', animation: 'spin 1s linear infinite', color: 'var(--text-secondary)' }} />}

      <AnimatePresence>
        {showDropdown && results.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="role-dropdown"
          >
            {results.map(role => (
              <div
                key={role.role_id}
                className="role-option"
                onClick={() => {
                  onSelect(role.role_id, role.role_name);
                  setQuery('');
                  setShowDropdown(false);
                }}
              >
                <div className="role-color-dot" />
                {role.role_name}
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const CommandManagementPage = () => {
  const { activeGuildId } = useContext(GuildContext);
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

  
  // Arama filtreleme
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

  return (
    <div className="cmd-mgmt-container">
      <header className="cmd-header">
        <h1 className="cmd-title">
          <Command size={32} color="var(--accent-green)" />
          Komut Yönetimi
        </h1>
        <p className="cmd-subtitle">
          Sunucunuzdaki bot komutlarını kategoriler halinde yönetin ve rol bazlı erişim atayın.
        </p>
      </header>

      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text-secondary)' }}>
          <Loader size={24} style={{ animation: 'spin 1s linear infinite' }} /> Komut ayarları yükleniyor...
        </div>
      ) : (
        <div className="cmd-layout">
          {/* Sidebar */}
          <div className="cmd-sidebar">
            <div className="cmd-search-box">
              <div className="cmd-search-input-wrapper">
                <Search size={16} className="cmd-search-icon" />
                <input 
                  type="text" 
                  className="cmd-search-input" 
                  placeholder="Komutlarda Ara..." 
                  value={globalSearch}
                  onChange={(e) => setGlobalSearch(e.target.value)}
                />
              </div>
            </div>
            
            <div className="cmd-category-list">
              {categoryNames.map(cat => (
                <div 
                  key={cat} 
                  className={`cmd-category-item ${activeCategory === cat ? 'active' : ''}`}
                  onClick={() => { setActiveCategory(cat); setGlobalSearch(''); }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <Hash size={16} />
                    <span className="cmd-category-name">{cat}</span>
                  </div>
                  <span className="cmd-category-count">{categories[cat].length}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Main Content Area */}
          <div className="cmd-main-content">
            {activeCategory && (
              <>
                <div className="cmd-main-header">
                  <div className="cmd-main-header-info">
                    <h2>{activeCategory} Kategorisi</h2>
                    <p>{categories[activeCategory].length} komut bulunuyor. {globalSearch && `Arama sonucu: ${activeCommands.length}`}</p>
                  </div>
                  <div className="cmd-main-actions">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Users size={18} color="var(--text-secondary)" />
                        <div style={{ width: '220px' }}>
                           <RoleSearch 
                             placeholder="Kategoriye Toplu Rol Ekle..." 
                             onSelect={(rId, rName) => addRoleToCategory(activeCategory, rId, rName)}
                           />
                        </div>
                        {savingId === `catRole-${activeCategory}` && <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} />}
                      </div>
                      
                      {categoryRoles.length > 0 && (
                        <div className="category-bulk-roles" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                          <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>Etkin Roller:</span>
                          {categoryRoles.map(rId => (
                            <div key={rId} className="role-badge" style={{ padding: '2px 8px', fontSize: '12px' }}>
                              {roleCache[rId] || rId}
                              <X size={12} className="role-badge-remove" onClick={() => removeRoleFromCategory(activeCategory, rId)} />
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="master-toggle-wrapper">
                      <span className="master-toggle-label">Tümünü {allEnabled ? 'Kapat' : 'Aç'}</span>
                      <div 
                        className={`toggle-switch ${allEnabled ? 'on' : ''}`}
                        onClick={() => toggleMasterCategory(activeCategory)}
                      >
                        <motion.div
                          layout
                          transition={{ type: "spring", stiffness: 500, damping: 30 }}
                          className="toggle-thumb"
                          animate={{ x: allEnabled ? 20 : 0 }}
                        />
                      </div>
                      {savingId === `master-${activeCategory}` && <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} />}
                    </div>
                  </div>
                </div>

                <div className="cmd-grid">
                  <AnimatePresence>
                    {activeCommands.map(cmd => (
                      <motion.div 
                        key={cmd.name}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className={`cmd-card ${cmd.is_enabled ? 'enabled' : 'disabled'}`}
                      >
                        <div className="cmd-card-header">
                          <div>
                            <div className="cmd-name">/{cmd.name}</div>
                            <div className="cmd-desc">{cmd.desc}</div>
                          </div>
                          
                          <div 
                            className={`toggle-switch ${cmd.is_enabled ? 'on' : ''}`}
                            onClick={() => toggleCommand(activeCategory, cmd.name)}
                          >
                            <motion.div
                              layout
                              transition={{ type: "spring", stiffness: 500, damping: 30 }}
                              className="toggle-thumb"
                              animate={{ x: cmd.is_enabled ? 20 : 0 }}
                            />
                          </div>
                        </div>

                        <div className="cmd-roles-section">
                          <div className="cmd-roles-title">
                            <Shield size={14} /> Erişim Rolleri
                          </div>
                          
                          <div className="cmd-roles-list">
                            {cmd.allowed_roles.map(roleId => (
                              <div key={roleId} className="role-badge">
                                {roleCache[roleId] ? roleCache[roleId] : roleId}
                                <X size={12} className="role-badge-remove" onClick={() => removeRoleFromCommand(activeCategory, cmd.name, roleId)} />
                              </div>
                            ))}
                            {cmd.allowed_roles.length === 0 && (
                              <span className="empty-roles">Varsayılan yetkiler geçerli (Sınırsız)</span>
                            )}
                          </div>

                          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                            <RoleSearch 
                              disabled={!cmd.is_enabled}
                              currentRoles={cmd.allowed_roles}
                              onSelect={(rId, rName) => addRoleToCommand(activeCategory, cmd.name, rId, rName)}
                              placeholder="Kısıtlama Ekle..."
                            />
                            {savingId === cmd.name && (
                              <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
                            )}
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
        </div>
      )}
    </div>
  );
};

export default CommandManagementPage;
