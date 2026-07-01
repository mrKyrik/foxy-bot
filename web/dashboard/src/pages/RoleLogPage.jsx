import React, { useState } from 'react';
import { Tag } from 'lucide-react';
import LogPageLayout from '../components/LogPageLayout';
import { useLogFilter } from '../hooks/useLogFilter';
import { getPercent, formatTime } from '../utils/time';

const RoleLogPage = ({ logs, viewWindow, setViewWindow, globalRange, selectedTags, onUserClick }) => {
  const [activeTab, setActiveTab] = useState('user'); // user, role, global

  const { parsed } = useLogFilter(logs, {
    typeFilter: (log, type) => type.includes('role'),
    selectedTags,
    reducer: (filteredLogs) => {
      const users = {};
      const roles = {};
      const globalEvs = [];

      filteredLogs.forEach(log => {
        const type = log.event_type;
        const rawRoleId = log.role_id || log.channel_id;
        let roleId = log.role_name ? log.role_name : (rawRoleId && rawRoleId.match(/^\d+$/) ? `Rol <@&${rawRoleId}>` : (rawRoleId || log.details || "Bilinmeyen Rol"));
        if (typeof roleId === 'string') {
           roleId = roleId.replace(/^(Rol Eklendi:|Rol Alındı:|Rol Eklendi|Rol Alındı)\s*/i, '').trim();
        }
        
        const uId = log.user_id || "Bilinmeyen Kullanıcı";
        const uName = log.username || uId;

        globalEvs.push({ ...log, roleId });

        // User grouping
        if (!users[uId]) users[uId] = { id: uId, name: uName, avatar_url: log.avatar_url, roles: {} };
        if (!users[uId].roles[roleId]) users[uId].roles[roleId] = { id: roleId, sessions: [] };
        
        const userRole = users[uId].roles[roleId];
        if (type.includes('add') || type.includes('give')) {
           userRole.sessions.push({ start: log.ts, end: null });
        } else if (type.includes('remove') || type.includes('take')) {
           const activeSession = userRole.sessions.find(s => !s.end);
           if (activeSession) activeSession.end = log.ts;
        }

        // Role grouping
        if (!roles[roleId]) roles[roleId] = { id: roleId, users: {} };
        if (!roles[roleId].users[uId]) roles[roleId].users[uId] = { id: uId, name: uName, avatar_url: log.avatar_url, sessions: [] };
        
        const roleUser = roles[roleId].users[uId];
        if (type.includes('add') || type.includes('give')) {
           roleUser.sessions.push({ start: log.ts, end: null });
        } else if (type.includes('remove') || type.includes('take')) {
           const activeSession = roleUser.sessions.find(s => !s.end);
           if (activeSession) activeSession.end = log.ts;
        }
      });

      return { userParsed: users, roleParsed: roles, globalParsed: globalEvs };
    }
  });

  const timeMin = viewWindow ? viewWindow[0] : 0;
  const timeMax = viewWindow ? viewWindow[1] : 0;
  const hasAnyData = parsed.globalParsed.length > 0;
  const nowTS = Date.now();

  const tabs = (
    <div style={{ display: 'flex', background: 'rgba(0,0,0,0.5)', borderRadius: '8px', padding: '4px' }}>
      <button 
        onClick={() => setActiveTab('user')}
        style={{ padding: '6px 16px', background: activeTab === 'user' ? '#06b6d4' : 'transparent', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', transition: '0.2s' }}>
        Kullanıcı Bazlı
      </button>
      <button 
        onClick={() => setActiveTab('role')}
        style={{ padding: '6px 16px', background: activeTab === 'role' ? '#06b6d4' : 'transparent', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', transition: '0.2s' }}>
        Rol Bazlı
      </button>
      <button 
        onClick={() => setActiveTab('global')}
        style={{ padding: '6px 16px', background: activeTab === 'global' ? '#06b6d4' : 'transparent', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', transition: '0.2s' }}>
        Global Çizgi
      </button>
    </div>
  );

  return (
    <LogPageLayout
      title="Rol Hareketleri"
      icon={<Tag />}
      iconColor="#06b6d4"
      eventOptions={null}
      selectedEvents={null}
      setSelectedEvents={null}
      viewWindow={viewWindow}
      setViewWindow={setViewWindow}
      globalRange={globalRange}
      hasAnyData={hasAnyData}
      emptyMessage="Seçilen zaman diliminde gösterilecek rol etkinliği yok."
      headerRight={tabs}
    >
        {activeTab === 'user' && Object.values(parsed.userParsed).map(user => (
          <div key={user.id} style={{ marginBottom: '30px', background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '12px' }}>
             <div 
               style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', cursor: 'pointer', transition: 'opacity 0.2s' }}
               onClick={() => onUserClick && onUserClick({ id: user.id, name: user.name, avatar_url: user.avatar_url })}
               onMouseOver={(e) => e.currentTarget.style.opacity = '0.8'}
               onMouseOut={(e) => e.currentTarget.style.opacity = '1'}
             >
               <img src={user.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'} style={{ width: '32px', height: '32px', borderRadius: '50%' }} alt="User" />
               <h3 style={{ fontSize: '1.1rem', color: '#fff', margin: 0 }}>{user.name}</h3>
             </div>
             
             {Object.values(user.roles).map(role => (
               <div key={role.id} style={{ display: 'flex', alignItems: 'center', marginBottom: '12px', height: '30px' }}>
                 <div style={{ width: '150px', fontSize: '0.85rem', color: '#ccc', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }} title={role.id}>
                    {role.id.startsWith('<@&') ? `Rol ${role.id}` : role.id}
                 </div>
                 <div style={{ flex: 1, position: 'relative', height: '24px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
                    {role.sessions.map((sess, idx) => {
                       const startPct = getPercent(sess.start, timeMin, timeMax);
                       const endPct = sess.end ? getPercent(sess.end, timeMin, timeMax) : getPercent(nowTS, timeMin, timeMax);
                       const isOngoing = !sess.end;
                       if (endPct < 0 || startPct > 100) return null;
                       return (
                         <div key={idx} style={{ 
                            position: 'absolute', 
                            left: `${Math.max(0, startPct)}%`, 
                            width: `${Math.min(100 - Math.max(0, startPct), endPct - Math.max(0, startPct))}%`, 
                            top: 0, 
                            height: '100%', 
                            background: 'rgba(6, 182, 212, 0.2)', 
                            borderRadius: isOngoing ? '6px 0 0 6px' : '6px', 
                            border: '1px solid #06b6d4',
                            borderRight: isOngoing ? 'none' : '1px solid #06b6d4',
                            boxShadow: 'inset 0 0 8px rgba(6,182,212,0.1)'
                          }}>
                           {isOngoing && endPct >= 100 && (
                             <div style={{ position: 'absolute', right: '-6px', top: '50%', transform: 'translateY(-50%)', width: '0', height: '0', borderTop: '6px solid transparent', borderBottom: '6px solid transparent', borderLeft: '6px solid #06b6d4' }} />
                           )}
                          </div>
                       )
                    })}
                 </div>
               </div>
             ))}
          </div>
        ))}

        {activeTab === 'role' && Object.values(parsed.roleParsed).map(role => (
          <div key={role.id} style={{ marginBottom: '30px', background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <Tag size={20} color="#06b6d4" />
              <h4 style={{ color: '#06b6d4', fontSize: '1.1rem', margin: 0 }}>{role.id.startsWith('<@&') ? `Rol ${role.id}` : role.id}</h4>
            </div>
            
            {Object.values(role.users).map(user => (
               <div key={user.id} style={{ display: 'flex', alignItems: 'center', marginBottom: '12px', height: '30px' }}>
                 <div style={{ width: '150px', display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }} title={user.name}>
                    <img src={user.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'} style={{ width: '20px', height: '20px', borderRadius: '50%' }} alt="User" />
                    <span style={{ fontSize: '0.85rem', color: '#ccc', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>{user.name}</span>
                 </div>
                 <div style={{ flex: 1, position: 'relative', height: '24px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
                    {user.sessions.map((sess, idx) => {
                       const startPct = getPercent(sess.start, timeMin, timeMax);
                       const endPct = sess.end ? getPercent(sess.end, timeMin, timeMax) : getPercent(nowTS, timeMin, timeMax);
                       const isOngoing = !sess.end;
                       if (endPct < 0 || startPct > 100) return null;
                       return (
                         <div key={idx} style={{ 
                            position: 'absolute', 
                            left: `${Math.max(0, startPct)}%`, 
                            width: `${Math.min(100 - Math.max(0, startPct), endPct - Math.max(0, startPct))}%`, 
                            top: 0, 
                            height: '100%', 
                            background: 'rgba(16, 185, 129, 0.2)', 
                            borderRadius: isOngoing ? '6px 0 0 6px' : '6px', 
                            border: '1px solid #10b981',
                            borderRight: isOngoing ? 'none' : '1px solid #10b981',
                            boxShadow: 'inset 0 0 8px rgba(16,185,129,0.1)'
                          }}>
                           {isOngoing && endPct >= 100 && (
                             <div style={{ position: 'absolute', right: '-6px', top: '50%', transform: 'translateY(-50%)', width: '0', height: '0', borderTop: '6px solid transparent', borderBottom: '6px solid transparent', borderLeft: '6px solid #10b981' }} />
                           )}
                          </div>
                       )
                    })}
                 </div>
               </div>
            ))}
          </div>
        ))}

        {activeTab === 'global' && (
          <div style={{ position: 'relative', height: '80px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px', marginTop: '40px' }}>
            <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '4px', background: 'rgba(255,255,255,0.1)', transform: 'translateY(-50%)' }} />
            {parsed.globalParsed.map((ev, i) => {
               const pct = getPercent(ev.ts, timeMin, timeMax);
               if (pct < 0 || pct > 100) return null;
               const isAdd = ev.event_type.includes('add') || ev.event_type.includes('give');
               const color = isAdd ? '#10b981' : '#ef4444';
               const icon = isAdd ? '+' : '-';
               return (
                 <div key={i} className="msg-dot" style={{ position: 'absolute', left: `${pct}%`, top: '50%', transform: 'translate(-50%, -50%)', zIndex: 10, cursor: 'pointer' }}>
                    <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'rgba(0,0,0,0.8)', border: `2px solid ${color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color, fontWeight: 'bold', fontSize: '18px', boxShadow: `0 0 10px ${color}` }}>
                      {icon}
                    </div>
                    <div className="msg-tooltip" style={{ width: '300px' }}>
                       <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '8px' }}>
                         <strong style={{ fontSize: '1.1rem', color }}>{isAdd ? 'Rol Verildi' : 'Rol Alındı'}</strong>
                       </div>
                       <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '8px' }}>
                         <img src={ev.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'} style={{ width: '30px', height: '30px', borderRadius: '50%' }} alt="User" />
                         <div>
                           <div><strong>{ev.username || ev.user_id || "Bilinmeyen Kullanıcı"}</strong></div>
                           <div style={{ fontSize: '0.85rem', color: '#ccc' }}>Rol: {ev.roleId}</div>
                         </div>
                       </div>
                       <div style={{ color: '#aaa', fontSize: '0.85rem' }}>İşlem Saati: {formatTime(ev.ts)}</div>
                    </div>
                 </div>
               )
            })}
          </div>
        )}
    </LogPageLayout>
  );
};

export default RoleLogPage;
