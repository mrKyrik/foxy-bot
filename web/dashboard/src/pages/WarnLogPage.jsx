import React, { useState } from 'react';
import { AlertTriangle, Shield } from 'lucide-react';
import LogPageLayout from '../components/LogPageLayout';
import { useLogFilter } from '../hooks/useLogFilter';
import { getPercent, formatTime } from '../utils/time';

const EVENT_OPTIONS = [
  { value: 'warn_add', label: 'Uyarı Eklendi', color: '#eab308' },
  { value: 'warn_remove', label: 'Uyarı Silindi', color: '#ef4444' }
];

const WarnLogPage = ({ logs, viewWindow, setViewWindow, globalRange, selectedTags, onUserClick }) => {
  const [activeTab, setActiveTab] = useState('global'); // global, admin
  const [selectedEvents, setSelectedEvents] = useState(['warn_add', 'warn_remove']);

  const { parsed } = useLogFilter(logs, {
    typeFilter: (log, type) => type.includes('uyari') || type.includes('warn'),
    eventMatcher: (log, type, selected) => selected.some(se => type.includes(se.replace('warn_', ''))),
    selectedEvents,
    selectedTags,
    reducer: (filteredLogs) => {
      const globalEvents = [];
      const adminEvents = {};

      filteredLogs.forEach(log => {
        globalEvents.push(log);
        const adminId = log.admin_id || "Sistem";
        const adminName = log.admin_name || adminId;
        if (!adminEvents[adminId]) adminEvents[adminId] = { id: adminId, name: adminName, avatar_url: log.admin_avatar_url, events: [] };
        adminEvents[adminId].events.push(log);
      });

      return { parsedGlobal: globalEvents, parsedAdmin: adminEvents };
    }
  });

  const timeMin = viewWindow ? viewWindow[0] : 0;
  const timeMax = viewWindow ? viewWindow[1] : 0;
  const hasAnyData = parsed.parsedGlobal.length > 0;

  const tabs = (
    <div style={{ display: 'flex', background: 'rgba(0,0,0,0.5)', borderRadius: '8px', padding: '4px' }}>
      <button 
        onClick={() => setActiveTab('global')}
        style={{ padding: '6px 16px', background: activeTab === 'global' ? '#eab308' : 'transparent', color: activeTab === 'global' ? '#000' : 'white', fontWeight: activeTab === 'global' ? 'bold' : 'normal', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
        Global Zaman Çizgisi
      </button>
      <button 
        onClick={() => setActiveTab('admin')}
        style={{ padding: '6px 16px', background: activeTab === 'admin' ? '#eab308' : 'transparent', color: activeTab === 'admin' ? '#000' : 'white', fontWeight: activeTab === 'admin' ? 'bold' : 'normal', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
        Yetkiliye (Admin) Göre
      </button>
    </div>
  );

  return (
    <LogPageLayout
      title="Uyarı Logları"
      icon={<AlertTriangle />}
      iconColor="#eab308"
      eventOptions={EVENT_OPTIONS}
      selectedEvents={selectedEvents}
      setSelectedEvents={setSelectedEvents}
      viewWindow={viewWindow}
      setViewWindow={setViewWindow}
      globalRange={globalRange}
      hasAnyData={hasAnyData}
      emptyMessage="Seçilen filtrelerde uyarı yok."
      headerRight={tabs}
    >
        {activeTab === 'global' && (
          parsed.parsedGlobal.length === 0 ? (
            <div style={{ color: '#666', textAlign: 'center', padding: '40px' }}>Seçilen filtrelerde uyarı yok.</div>
          ) : (
            <div style={{ position: 'relative', height: '60px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px' }}>
              <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '4px', background: 'rgba(255,255,255,0.1)', transform: 'translateY(-50%)' }} />
              
              {parsed.parsedGlobal.map((ev, i) => {
                 const pct = getPercent(ev.ts, timeMin, timeMax);
                 if (pct < 0 || pct > 100) return null;
                 const isRemove = ev.event_type.includes('remove');
                 const color = isRemove ? '#ef4444' : '#eab308';
                 const icon = isRemove ? '🗑️' : '⚠️';
                 
                 return (
                   <div key={i} className="msg-dot" style={{ position: 'absolute', left: `${pct}%`, top: '50%', transform: 'translate(-50%, -50%)', cursor: 'pointer', zIndex: 10 }}>
                      <div style={{ fontSize: '24px', filter: `drop-shadow(0 0 8px ${color})` }}>{icon}</div>
                      
                       <div className="msg-tooltip" style={{ width: '320px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '8px' }}>
                            <AlertTriangle size={18} color={color} />
                            <strong style={{ fontSize: '1rem', color }}>{isRemove ? 'Uyarı Silindi' : 'Uyarı Verildi'}</strong>
                          </div>
                          <div style={{ color: '#eee', fontSize: '0.9rem', marginBottom: '8px' }}>
                            Yetkili <strong>{ev.admin_name || ev.admin_id || 'Sistem'}</strong>, Kullanıcı <strong>{ev.username || ev.user_id}</strong>'yi uyardı.
                          </div>
                          <div style={{ color: '#aaa', fontSize: '0.85rem', marginBottom: '8px' }}>Saat: {formatTime(ev.ts)}</div>
                          <div style={{ color: '#fff', fontSize: '0.9rem', padding: '8px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', fontStyle: 'italic', wordBreak: 'break-word' }}>
                            <span style={{ color: '#aaa', fontWeight: 'bold' }}>Sebep: </span>
                            {ev.reason || ev.details || "Belirtilmemiş"}
                          </div>
                       </div>
                   </div>
                 )
              })}
            </div>
          )
        )}

        {activeTab === 'admin' && (
          Object.keys(parsed.parsedAdmin).length === 0 ? (
            <div style={{ color: '#666', textAlign: 'center', padding: '40px' }}>Seçilen filtrelerde yetkili işlemi yok.</div>
          ) : (
            Object.values(parsed.parsedAdmin).map(admin => (
              <div key={admin.id} style={{ display: 'flex', alignItems: 'center', marginBottom: '30px', position: 'relative' }}>
                <div 
                  style={{ width: '200px', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', transition: 'opacity 0.2s' }}
                  onClick={() => onUserClick && onUserClick({ id: admin.id, name: admin.name, avatar_url: admin.avatar_url })}
                  onMouseOver={(e) => e.currentTarget.style.opacity = '0.8'}
                  onMouseOut={(e) => e.currentTarget.style.opacity = '1'}
                >
                  <img src={admin.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'} style={{ width: '40px', height: '40px', borderRadius: '50%' }} alt="Admin" />
                  <span style={{ fontWeight: 'bold', fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {admin.name}
                  </span>
                </div>
                
                <div style={{ flex: 1, position: 'relative', height: '40px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px' }}>
                   <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '4px', background: 'rgba(255,255,255,0.05)', transform: 'translateY(-50%)' }} />
                   
                   {admin.events.map((ev, i) => {
                      const pct = getPercent(ev.ts, timeMin, timeMax);
                      if (pct < 0 || pct > 100) return null;

                      const isRemove = ev.event_type.includes('remove');
                      const color = isRemove ? '#ef4444' : '#eab308';
                      const icon = isRemove ? '🗑️' : '⚠️';
                      
                      return (
                        <div key={i} className="msg-dot" style={{ position: 'absolute', left: `${pct}%`, top: '50%', transform: 'translate(-50%, -50%)', cursor: 'pointer', zIndex: 10 }}>
                           <div style={{ fontSize: '20px', filter: `drop-shadow(0 0 8px ${color})` }}>{icon}</div>
                           
                           <div className="msg-tooltip" style={{ width: '300px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '8px' }}>
                                <Shield size={18} color={color} />
                                <strong style={{ fontSize: '1rem', color }}>{isRemove ? 'Uyarı İptal Etti' : 'Uyarı Verdi'}</strong>
                              </div>
                              <div style={{ marginBottom: '8px' }}>
                                <span style={{ color: '#aaa', fontSize: '0.85rem', marginRight: '4px' }}>Kullanıcı: </span>
                                <img src={ev.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'} style={{ width: '20px', height: '20px', borderRadius: '50%', verticalAlign: 'middle', marginRight: '6px' }} />
                                <strong style={{ fontSize: '0.9rem', color: '#fff' }}>{ev.username || ev.user_id}</strong>
                              </div>
                              <div style={{ color: '#aaa', fontSize: '0.85rem', marginBottom: '8px' }}>Saat: {formatTime(ev.ts)}</div>
                              <div style={{ color: '#fff', fontSize: '0.9rem', padding: '8px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', fontStyle: 'italic', wordBreak: 'break-word' }}>
                                <span style={{ color: '#aaa', fontWeight: 'bold' }}>Sebep: </span>
                                {ev.reason || ev.details || "Belirtilmemiş"}
                              </div>
                           </div>
                        </div>
                      )
                   })}
                </div>
              </div>
            ))
          )
        )}
    </LogPageLayout>
  );
};

export default WarnLogPage;
