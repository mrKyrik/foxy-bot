import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Terminal, LogOut, Activity } from 'lucide-react';
import { motion } from 'framer-motion';

const MainSidebar = ({ setAuthToken }) => {
  const getNavClass = ({ isActive }) => isActive ? "nav-item active" : "nav-item";

  const navItems = [
    { to: "/", icon: <LayoutDashboard size={18} />, label: "Genel Bakış" },
    { to: "/commands", icon: <Terminal size={18} />, label: "Komut Yönetimi" },
    { to: "/logs/ses", icon: <Activity size={18} />, label: "Log Sistemi", special: true },
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
          <LayoutDashboard size={28} color="var(--accent-blue)" />
        </motion.div>
        Kumiho Panel
      </div>
      
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
            {item.special ? (
              <a 
                href={item.to} 
                className={getNavClass({ isActive: false })} 
                style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--accent-green)', border: '1px solid var(--accent-green-glow)', textDecoration: 'none' }}
              >
                {item.icon} {item.label}
              </a>
            ) : (
              <NavLink 
                to={item.to} 
                className={getNavClass} 
                end={item.to === "/"}
              >
                {item.icon} {item.label}
              </NavLink>
            )}
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
