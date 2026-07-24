import React, { useContext } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Terminal, LogOut, Activity, Server, Shield, FileText } from 'lucide-react';
import { motion } from 'framer-motion';
import { GuildContext } from '../GuildContext';

const MainSidebar = ({ setAuthToken }) => {
  const { guilds, activeGuildId, changeGuild, guildPermission } = useContext(GuildContext);
  const getNavClass = ({ isActive }) => isActive ? "nav-item active" : "nav-item";

    const navItems = [
      { to: "/", icon: <LayoutDashboard size={18} />, label: "Genel Bakış" },
      { to: "/commands", icon: <Terminal size={18} />, label: "Komut Yönetimi" },
      { to: "/forms", icon: <FileText size={18} />, label: "Form Yönetimi" },
      { to: "/logs/ses", icon: <Activity size={18} />, label: "Log Sistemi" },
    ];

  if (guildPermission === 'owner') {
    navItems.splice(2, 0, { to: "/auth", icon: <Shield size={18} />, label: "Yetkilendirme" });
  }

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
          <img src="/foxy-bot-pp.webp" alt="Foxy Bot Logo" style={{ width: '28px', height: '28px', borderRadius: '50%' }} />
        </motion.div>
        Kumiho Panel
      </div>
      
      {/* Guild Selector */}
      {guilds && guilds.length > 0 && (
        <div style={{ marginBottom: '16px', padding: '0 8px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Server size={12} /> Seçili Sunucu
          </div>
          <select 
            value={activeGuildId || ''} 
            onChange={(e) => changeGuild(e.target.value)}
            style={{ 
              width: '100%', 
              padding: '8px', 
              background: 'rgba(255,255,255,0.05)', 
              color: 'var(--text-primary)',
              border: '1px solid rgba(255,255,255,0.1)', 
              borderRadius: '8px',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            {guilds.map(g => (
              <option key={g.id} value={g.id} style={{ background: '#09090b', color: '#fff' }}>
                {g.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
        {navItems.map((item, i) => (
          <motion.div 
            key={item.to}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <NavLink 
              to={item.to} 
              className={getNavClass} 
              end={item.to === "/"}
            >
              {item.icon} {item.label}
            </NavLink>
          </motion.div>
        ))}
        
        <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
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
              borderRadius: '12px'
            }}
          >
            <LogOut size={18} /> Çıkış Yap
          </motion.button>
        </div>
      </div>
    </aside>
  );
};

export default MainSidebar;
