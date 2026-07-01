import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Filter, Users, Shield, Radio, MessageSquare, AlertTriangle, Ticket, FileText, UserPlus, Tag, Settings, Home, Command, LogOut, ChevronRight, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import GlobalTagSelector from './GlobalTagSelector';

const Sidebar = ({ availableTags, selectedTags, setSelectedTags, setAuthToken }) => {
  const getNavClass = ({ isActive }) => isActive ? "nav-item active" : "nav-item";
  const location = useLocation();
  const isLogsRoute = location.pathname.startsWith('/logs');

  const logItems = [
    { to: "/logs/ses", icon: <Users size={18} />, label: "Ses Logları" },
    { to: "/logs/mesaj", icon: <MessageSquare size={18} />, label: "Mesaj Logları" },
    { to: "/logs/mod", icon: <Shield size={18} />, label: "Mod Logları" },
    { to: "/logs/sunucu", icon: <Settings size={18} />, label: "Sunucu Logları" },
    { to: "/logs/rol", icon: <Tag size={18} />, label: "Rol Logları" },
    { to: "/logs/uyari", icon: <AlertTriangle size={18} />, label: "Uyarı Logları" },
    { to: "/logs/ticket", icon: <Ticket size={18} />, label: "Ticket Logları" },
    { to: "/logs/basvuru", icon: <FileText size={18} />, label: "Başvuru Logları" },
    { to: "/logs/davet", icon: <UserPlus size={18} />, label: "Davet Logları" },
  ];

  const handleLogout = () => {
    localStorage.removeItem('kumiho_token');
    setAuthToken(null);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-title">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
        >
          <Radio size={28} color="var(--accent-green)" />
        </motion.div>
        Kumiho
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
        
        {/* ANA SAYFA */}
        <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
          <NavLink to="/" className={getNavClass} end>
            <Home size={18} /> Ana Sayfa
          </NavLink>
        </motion.div>

        {/* LOG MODÜLÜ BAŞLIĞI */}
        <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} style={{ marginTop: '8px' }}>
          <NavLink to="/logs/ses" className={`nav-item ${isLogsRoute ? 'active' : ''}`} style={{ justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Filter size={18} /> Gözlem (Loglar)
            </div>
            {isLogsRoute ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </NavLink>
        </motion.div>

        {/* ALT LOG MENÜLERİ (SADECE /logs İÇİNDEYSE GÖSTER) */}
        <AnimatePresence>
          {isLogsRoute && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              style={{ overflow: 'hidden', paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '4px' }}
            >
              {logItems.map((item, i) => (
                <motion.div 
                  key={item.to}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <NavLink to={item.to} className={getNavClass} style={{ fontSize: '0.85rem', padding: '8px 12px' }}>
                    {item.icon} {item.label}
                  </NavLink>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
        
        <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px', paddingLeft: '16px' }}>
            Sistem
          </div>

          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <NavLink to="/commands" className={getNavClass}>
              <Command size={18} /> Komut Yönetimi
            </NavLink>
          </motion.div>

          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <NavLink to="/settings" className={getNavClass}>
              <Settings size={18} /> Ayarlar
            </NavLink>
          </motion.div>

          <motion.button 
            onClick={handleLogout}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="nav-item" 
            style={{ 
              width: '100%', 
              background: 'transparent', 
              border: 'none', 
              cursor: 'pointer', 
              textAlign: 'left', 
              color: 'var(--accent-red)', 
              padding: '12px 16px', 
              borderRadius: '12px',
              marginTop: '8px'
            }}
          >
            <LogOut size={18} /> Çıkış Yap
          </motion.button>
        </div>
      </div>

      {isLogsRoute && (
        <GlobalTagSelector availableTags={availableTags} selectedTags={selectedTags} setSelectedTags={setSelectedTags} />
      )}
    </aside>
  );
};

export default Sidebar;
