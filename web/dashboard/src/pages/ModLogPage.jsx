import React, { useState } from 'react';
import { Shield, Hammer, UserMinus, FileEdit } from 'lucide-react';
import LogPageLayout from '../components/LogPageLayout';
import { useLogFilter } from '../hooks/useLogFilter';
import { getPercent, formatTime } from '../utils/time';

const EVENT_OPTIONS = [
  { value: 'mod_ban', label: 'Ban İşlemleri', color: '#ef4444' },
  { value: 'mod_kick', label: 'Kick İşlemleri', color: '#f97316' },
  { value: 'mod_timeout', label: 'Zamanaşımı', color: '#eab308' },
  { value: 'mod_role', label: 'Rol İşlemi', color: '#10b981' },
];

const ModLogPage = ({ logs, viewWindow, setViewWindow, globalRange, selectedTags, onUserClick }) => {
  const [selectedEvents, setSelectedEvents] = useState(['mod_ban', 'mod_kick', 'mod_timeout', 'mod_role']);

  const { parsed } = useLogFilter(logs, {
    // Hem 'mod_' prefix'li (db_event_logs) hem admin kaynaklı (admin_events) logları al
    typeFilter: (log, type) => {
      const ltype = type.toLowerCase();
      return ltype.startsWith('mod_') || log.source === 'admin';
    },
    eventMatcher: (log, type, selected) => {
      const ltype = type.toLowerCase();
      return selected.some(se => {
        const lse = se.toLowerCase();
        // 'mod_ban' filtresi: mod_ban, ban, BAN hepsini eşleştir
        const keyword = lse.replace('mod_', '');
        return ltype.includes(keyword);
      });
    },
    selectedEvents,
    selectedTags,
    reducer: (filteredLogs) => {
      const mods = {};
      filteredLogs.forEach(log => {
        const modId = log.user_id || "Bilinmeyen Yetkili";
        const modName = log.username || modId;

        if (!mods[modId]) mods[modId] = { id: modId, name: modName, avatar_url: log.avatar_url, events: [] };
        mods[modId].events.push(log);
      });
      return mods;
    }
  });

  const timeMin = viewWindow ? viewWindow[0] : 0;
  const timeMax = viewWindow ? viewWindow[1] : 0;
  const hasAnyData = Object.keys(parsed).length > 0;

  return (
    <LogPageLayout
      title="Moderatör İşlemleri"
      icon={<Shield />}
      iconColor="#f43f5e"
      eventOptions={EVENT_OPTIONS}
      selectedEvents={selectedEvents}
      setSelectedEvents={setSelectedEvents}
      viewWindow={viewWindow}
      setViewWindow={setViewWindow}
      globalRange={globalRange}
      hasAnyData={hasAnyData}
      emptyMessage="Seçilen günde yetkili işlemi yok."
    >
      {Object.values(parsed).map(mod => (
        <div key={mod.id} style={{ display: 'flex', alignItems: 'center', marginBottom: '24px', position: 'relative' }}>
          <div 
            style={{ width: '200px', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', transition: 'opacity 0.2s' }}
            onClick={() => onUserClick && onUserClick({ id: mod.id, name: mod.name, avatar_url: mod.avatar_url })}
            onMouseOver={(e) => e.currentTarget.style.opacity = '0.8'}
            onMouseOut={(e) => e.currentTarget.style.opacity = '1'}
          >
            <img src={mod.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'} style={{ width: '40px', height: '40px', borderRadius: '50%' }} alt="Mod" />
            <span style={{ fontWeight: 'bold', fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {mod.name}
            </span>
          </div>
          
          <div style={{ flex: 1, position: 'relative', height: '40px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px' }}>
              <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '4px', background: 'rgba(255,255,255,0.05)', transform: 'translateY(-50%)' }} />
              
              {mod.events.map((ev, i) => {
                const pct = getPercent(ev.ts, timeMin, timeMax);
                if (pct < 0 || pct > 100) return null;

                let icon = <FileEdit size={16} color="#3b82f6" />;
                let actionStr = "Düzenleme";
                const ltype = ev.event_type.toLowerCase();
                if (ltype.includes('ban') || ltype.includes('timeout')) { icon = <Hammer size={16} color="#ef4444" />; actionStr = "Yaptırım"; }
                if (ltype.includes('kick')) { icon = <UserMinus size={16} color="#f97316" />; actionStr = "Uzaklaştırma"; }
                if (ltype.includes('role') || ltype.includes('rol')) { icon = <Shield size={16} color="#10b981" />; actionStr = "Rol İşlemi"; }
                
                return (
                  <div key={i} className="msg-dot" style={{ position: 'absolute', left: `${pct}%`, top: '50%', transform: 'translate(-50%, -50%)', cursor: 'pointer', zIndex: 10 }}>
                      <div style={{ background: 'rgba(0,0,0,0.8)', padding: '6px', borderRadius: '50%', border: '1px solid rgba(255,255,255,0.2)' }}>
                        {icon}
                      </div>
                      
                      <div className="msg-tooltip" style={{ width: '280px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '8px' }}>
                          {icon}
                          <strong style={{ fontSize: '1rem' }}>{actionStr}</strong>
                        </div>
                        <div style={{ marginBottom: '8px' }}>
                          <span style={{ color: '#aaa', fontSize: '0.85rem' }}>Hedef: </span>
                          <strong style={{ color: '#fff', fontSize: '0.95rem' }}>{ev.target_name || ev.target_id || ev.user_id || "Bilinmiyor"}</strong>
                        </div>
                        <div style={{ color: '#ccc', fontSize: '0.85rem', marginBottom: '4px' }}>Saat: {formatTime(ev.ts)}</div>
                        <div style={{ color: '#eee', fontSize: '0.9rem', padding: '6px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', fontStyle: 'italic' }}>
                          <span style={{ color: '#aaa' }}>Sebep: </span> {ev.reason || ev.details || "Belirtilmemiş"}
                        </div>
                      </div>
                  </div>
                )
              })}
          </div>
        </div>
      ))}
    </LogPageLayout>
  );
};

export default ModLogPage;
