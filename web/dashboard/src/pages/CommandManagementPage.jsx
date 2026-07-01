import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Command, Shield, Plus, X, Loader, ChevronDown, ChevronUp, Search, Users } from 'lucide-react';
import { GUILD_ID, API_BASE_URL } from '../config';

// ── Rol Arama Bileşeni (Autocomplete) ──
const RoleSearch = ({ onSelect, placeholder, disabled, currentRoles = [] }) => {
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
      setResults([]);
      return;
    }
    const fetchRoles = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`${API_BASE_URL}/roles/${GUILD_ID}?q=${query}`);
        // Daha önce eklenenleri gösterme
        const filtered = (res.data.roles || []).filter(r => !currentRoles.includes(r.role_id));
        setResults(filtered);
      } catch (err) {
        console.error('Roller aranırken hata:', err);
      } finally {
        setLoading(false);
      }
    };
    const timer = setTimeout(fetchRoles, 300); // 300ms gecikmeli istek (Debounce)
    return () => clearTimeout(timer);
  }, [query, currentRoles]);

  return (
    <div ref={dropdownRef} style={{ position: 'relative', flex: 1, display: 'flex' }}>
      <div style={{ position: 'relative', flex: 1 }}>
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
            width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--panel-border)',
            color: '#fff', padding: '6px 10px', paddingLeft: '28px', borderRadius: '6px', fontSize: '0.85rem', outline: 'none'
          }}
        />
        <Search size={14} style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
        {loading && <Loader size={12} style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', animation: 'spin 1s linear infinite', color: 'var(--text-secondary)' }} />}
      </div>

      <AnimatePresence>
        {showDropdown && results.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            style={{
              position: 'absolute', top: '100%', left: 0, right: 0, marginTop: '4px',
              background: '#1e1e24', border: '1px solid var(--panel-border)',
              borderRadius: '6px', maxHeight: '150px', overflowY: 'auto', zIndex: 50,
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
            }}
          >
            {results.map(role => (
              <div
                key={role.role_id}
                onClick={() => {
                  onSelect(role.role_id, role.role_name);
                  setQuery('');
                  setShowDropdown(false);
                }}
                style={{
                  padding: '8px 12px', fontSize: '0.85rem', cursor: 'pointer',
                  borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: '8px',
                  color: '#e2e8f0'
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-blue)' }} />
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
  const [categories, setCategories] = useState({});
  const [expandedCats, setExpandedCats] = useState({});
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  
  // Rol isimlerini cachelemek için (Aksi halde veritabanındaki rolleri ID olarak görürüz)
  const [roleCache, setRoleCache] = useState({});

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

      // Sayfa yüklenirken ID'den isim eşleştirmesi yapabilmek için Rol Cache'i doldurabiliriz
      // Ancak şu an için sadece arama yapıldıkça cache'e ekliyoruz (Aşağıdaki metodlarda var).
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
    
    // Optimistic UI Update
    const updatedCats = { ...categories };
    updatedCats[catName] = cmds.map(c => {
      if (!c.allowed_roles.includes(roleId)) {
        return { ...c, allowed_roles: [...c.allowed_roles, roleId] };
      }
      return c;
    });
    setCategories(updatedCats);

    try {
      await axios.post(`${API_BASE_URL}/commands/category/${GUILD_ID}/roles`, {
        commands: cmdNames,
        role_id: roleId
      });
    } catch (err) {
      console.error(err);
    } finally {
      setSavingId(null);
    }
  };

  const toggleExpand = (catName) => {
    setExpandedCats(prev => ({ ...prev, [catName]: !prev[catName] }));
  };

  return (
    // SCROLL BAR FIX: overflowY: 'auto' ve maxHeight: '100vh' eklendi!
    <div style={{ padding: '32px', color: '#fff', maxWidth: '1200px', margin: '0 auto', width: '100%', height: 'calc(100vh - 64px)', overflowY: 'auto', paddingBottom: '100px' }}>
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
            const catRoleSaving = savingId === `catRole-${catName}`;

            return (
              <div key={catName} style={{ 
                background: 'rgba(0,0,0,0.4)', 
                borderRadius: '12px', 
                border: '1px solid var(--panel-border)',
                overflow: 'visible' // Dropdownların dışarı taşabilmesi için visible yaptık
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

                  {/* Kategori Bazlı Aksiyonlar */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }} onClick={e => e.stopPropagation()}>
                    
                    {/* Toplu Rol Ekleme (Master Role Assigner) */}
                    {isExpanded && (
                       <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                         <Users size={16} color="var(--text-secondary)" />
                         <div style={{ width: '200px' }}>
                            <RoleSearch 
                              placeholder="Tüm Kategoriye Rol Ekle..." 
                              onSelect={(rId, rName) => addRoleToCategory(catName, rId, rName)}
                            />
                         </div>
                         {catRoleSaving && <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} />}
                       </div>
                    )}

                    <div style={{ width: '1px', height: '24px', background: 'var(--panel-border)' }} />

                    {/* Master Toggle */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Kategoriyi {allEnabled ? "Kapat" : "Aç"}</span>
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
                </div>

                {/* Commands Grid */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div 
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      style={{ overflow: 'visible' }} // İçerideki dropdownların taşmasına izin ver
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
                              transition: 'all 0.3s ease',
                              overflow: 'visible'
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
                                    color: 'var(--accent-blue)', padding: '4px 8px', borderRadius: '12px',
                                    fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '6px'
                                  }}>
                                    {/* Eğer ismini biliyorsak ismini yaz, bilmiyorsak ID'yi yaz */}
                                    {roleCache[roleId] ? roleCache[roleId] : roleId}
                                    <X size={10} style={{ cursor: 'pointer', opacity: 0.7 }} onClick={() => removeRoleFromCommand(catName, cmd.name, roleId)} />
                                  </div>
                                ))}
                                {cmd.allowed_roles.length === 0 && (
                                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>Boş (Bot varsayılan yetkileri geçerli)</span>
                                )}
                              </div>

                              {/* Akıllı Rol Arama Input'u */}
                              <div style={{ display: 'flex', gap: '6px' }}>
                                <RoleSearch 
                                  disabled={!cmd.is_enabled}
                                  currentRoles={cmd.allowed_roles}
                                  onSelect={(rId, rName) => addRoleToCommand(catName, cmd.name, rId, rName)}
                                />
                                {savingId === cmd.name && (
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 8px' }}>
                                    <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
                                  </div>
                                )}
                              </div>
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
