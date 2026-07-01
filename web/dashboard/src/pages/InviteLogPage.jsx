import React, { useState } from 'react';
import { UserPlus } from 'lucide-react';
import LogPageLayout from '../components/LogPageLayout';
import { useLogFilter } from '../hooks/useLogFilter';
import { getPercent, formatTime } from '../utils/time';

const EVENT_OPTIONS = [
  { value: 'invite_create', label: 'Davet Oluşturuldu', color: '#3b82f6' },
  { value: 'invite_use', label: 'Davet Kullanıldı', color: '#10b981' }
];

const InviteLogPage = ({ logs, viewWindow, setViewWindow, globalRange, selectedTags }) => {
  const [selectedEvents, setSelectedEvents] = useState(['invite_create', 'invite_use']);

  const { parsed } = useLogFilter(logs, {
    typeFilter: (log, type) => type.includes('invite') || type.includes('davet'),
    eventMatcher: (log, type, selected) => selected.includes(type),
    selectedEvents,
    selectedTags
  });

  const timeMin = viewWindow ? viewWindow[0] : 0;
  const timeMax = viewWindow ? viewWindow[1] : 0;
  const hasAnyData = parsed.length > 0;

  return (
    <LogPageLayout
      title="Davet Logları"
      icon={<UserPlus />}
      iconColor="#3b82f6"
      eventOptions={EVENT_OPTIONS}
      selectedEvents={selectedEvents}
      setSelectedEvents={setSelectedEvents}
      viewWindow={viewWindow}
      setViewWindow={setViewWindow}
      globalRange={globalRange}
      hasAnyData={hasAnyData}
      emptyMessage="Seçilen günde davet etkinliği yok."
    >
        <div style={{ position: 'relative', height: '60px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px' }}>
          <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '4px', background: 'rgba(255,255,255,0.1)', transform: 'translateY(-50%)' }} />
          
          {parsed.map((ev, i) => {
             const pct = getPercent(ev.ts, timeMin, timeMax);
             if (pct < 0 || pct > 100) return null;

             let icon = "↗️"; // Join
             let actionStr = "Katıldı";
             let iconColor = "#10b981";
             if (ev.event_type.includes('leave') || ev.event_type.includes('quit')) { 
               icon = "↘️"; actionStr = "Ayrıldı"; iconColor = "#ef4444"; 
             }
             
             return (
               <div key={i} className="msg-dot" style={{ position: 'absolute', left: `${pct}%`, top: '50%', transform: 'translate(-50%, -50%)', cursor: 'pointer', zIndex: 10 }}>
                  <div style={{ fontSize: '20px', filter: `drop-shadow(0 0 8px ${iconColor})` }}>{icon}</div>
                  
                  <div className="msg-tooltip" style={{ width: '250px' }}>
                     <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '8px' }}>
                       <UserPlus size={18} color={iconColor} />
                       <strong style={{ fontSize: '1rem', color: iconColor }}>{actionStr}</strong>
                     </div>
                     <div style={{ color: '#ccc', fontSize: '0.85rem', marginBottom: '4px' }}>Saat: {formatTime(ev.ts)}</div>
                     <div style={{ color: '#eee', fontSize: '0.9rem' }}>
                       {ev.details || "Davet olayı."}
                     </div>
                  </div>
               </div>
             )
          })}
        </div>
    </LogPageLayout>
  );
};

export default InviteLogPage;
