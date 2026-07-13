import React from 'react';
import { NavLink } from 'react-router-dom';
import { Users, Shield, MessageSquare, AlertTriangle, Ticket, FileText, UserPlus, Tag, Settings, ArrowLeft, Filter, Headphones } from 'lucide-react';
import { motion } from 'framer-motion';
import GlobalTagSelector from './GlobalTagSelector';

const LogSidebar = ({ availableTags, selectedTags, setSelectedTags }) => {
  const getNavClass = ({ isActive }) => isActive ? "nav-item active" : "nav-item";

  const logItems = [
    { to: "/logs/ses", icon: <Users size={18} />, label: "Ses Logları" },
    { to: "/logs/mesaj", icon: <MessageSquare size={18} />, label: "Mesaj Logları" },
    { to: "/logs/mod", icon: <Shield size={18} />, label: "Mod Logları" },
    { to: "/logs/sunucu", icon: <Settings size={18} />, label: "Sunucu Logları" },
    { to: "/logs/rol", icon: <Tag size={18} />, label: "Rol Logları" },
    { to: "/logs/oda", icon: <Headphones size={18} />, label: "Oda Logları" },
    { to: "/logs/uyari", icon: <AlertTriangle size={18} />, label: "Uyarı Logları" },
    { to: "/logs/ticket", icon: <Ticket size={18} />, label: "Ticket Logları" },
    { to: "/logs/basvuru", icon: <FileText size={18} />, label: "Başvuru Logları" },
    { to: "/logs/davet", icon: <UserPlus size={18} />, label: "Davet Logları" },
    { to: "/logs/settings", icon: <Settings size={18} />, label: "Log Ayarları" },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-title" style={{ fontSize: '1.25rem', marginBottom: '16px' }}>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
        >
          <Filter size={24} color="var(--accent-green)" />
        </motion.div>
        Log Sistemi
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
        {logItems.map((item, i) => (
          <motion.div 
            key={item.to}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <NavLink to={item.to} className={getNavClass} style={{ fontSize: '0.9rem', padding: '10px 14px' }}>
              {item.icon} {item.label}
            </NavLink>
          </motion.div>
        ))}
        
        <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          <motion.div
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <a href="/" className="nav-item" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)', textDecoration: 'none' }}>
              <ArrowLeft size={18} /> Ana Panele Dön
            </a>
          </motion.div>
        </div>
      </div>

      <GlobalTagSelector availableTags={availableTags} selectedTags={selectedTags} setSelectedTags={setSelectedTags} />
    </aside>
  );
};

export default LogSidebar;
