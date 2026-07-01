import React, { useState } from 'react';
import { Ticket } from 'lucide-react';
import LogPageLayout from '../components/LogPageLayout';
import { useLogFilter } from '../hooks/useLogFilter';
import { getPercent, formatTime } from '../utils/time';

const EVENT_OPTIONS = [
  { value: 'ticket_create', label: 'Ticket Oluşturuldu', color: '#10b981' },
  { value: 'ticket_close', label: 'Ticket Kapatıldı', color: '#ef4444' }
];

const TicketLogPage = ({ logs, viewWindow, setViewWindow, globalRange, selectedTags }) => {
  const [selectedEvents, setSelectedEvents] = useState(['ticket_create', 'ticket_close']);

  const { parsed } = useLogFilter(logs, {
    typeFilter: (log, type) => type.includes('ticket'),
    eventMatcher: (log, type, selected) => selected.includes(type),
    selectedEvents,
    selectedTags
  });

  const timeMin = viewWindow ? viewWindow[0] : 0;
  const timeMax = viewWindow ? viewWindow[1] : 0;
  const hasAnyData = parsed.length > 0;

  return (
    <LogPageLayout
      title="Ticket Logları"
      icon={<Ticket />}
      iconColor="#06b6d4"
      eventOptions={EVENT_OPTIONS}
      selectedEvents={selectedEvents}
      setSelectedEvents={setSelectedEvents}
      viewWindow={viewWindow}
      setViewWindow={setViewWindow}
      globalRange={globalRange}
      hasAnyData={hasAnyData}
      emptyMessage="Seçilen günde ticket etkinliği yok."
    >
        <div style={{ position: 'relative', height: '60px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px' }}>
          <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '4px', background: 'rgba(255,255,255,0.1)', transform: 'translateY(-50%)' }} />
          
          {parsed.map((ev, i) => {
             const pct = getPercent(ev.ts, timeMin, timeMax);
             if (pct < 0 || pct > 100) return null;

             let icon = "🟢"; // Default
             let actionStr = "İşlem";
             if (ev.event_type.includes('close')) { icon = "🔴"; actionStr = "Kapatıldı"; }
             if (ev.event_type.includes('create') || ev.event_type.includes('open')) { icon = "🟢"; actionStr = "Açıldı"; }
             if (ev.event_type.includes('msg')) { icon = "🔵"; actionStr = "Mesaj"; }
             
             return (
               <div key={i} className="msg-dot" style={{ position: 'absolute', left: `${pct}%`, top: '50%', transform: 'translate(-50%, -50%)', cursor: 'pointer', zIndex: 10 }}>
                  <div style={{ fontSize: '20px', filter: 'drop-shadow(0 0 8px rgba(255,255,255,0.5))' }}>{icon}</div>
                  
                     <div className="msg-tooltip" style={{ width: '250px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '8px' }}>
                          <Ticket size={18} />
                          <strong style={{ fontSize: '1rem' }}>Ticket {actionStr}</strong>
                        </div>
                        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '8px' }}>
                          <img src={ev.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'} style={{ width: '30px', height: '30px', borderRadius: '50%' }} alt="User" />
                          <div>
                            <div><strong>{ev.username || ev.user_id || "Bilinmeyen Kullanıcı"}</strong></div>
                            <div style={{ fontSize: '0.85rem', color: '#ccc' }}>{ev.channel_name ? `#${ev.channel_name}` : "Bilinmeyen Kanal"}</div>
                          </div>
                        </div>
                        <div style={{ color: '#aaa', fontSize: '0.85rem', marginBottom: '4px' }}>Saat: {formatTime(ev.ts)}</div>
                        <div style={{ color: '#eee', fontSize: '0.9rem' }}>
                          {ev.details || "Ticket olayı gerçekleşti."}
                        </div>
                     </div>
               </div>
             )
          })}
        </div>
    </LogPageLayout>
  );
};

export default TicketLogPage;
