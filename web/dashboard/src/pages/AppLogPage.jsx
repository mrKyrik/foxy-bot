import React, { useState } from 'react';
import { FileText } from 'lucide-react';
import LogPageLayout from '../components/LogPageLayout';
import { useLogFilter } from '../hooks/useLogFilter';
import { getPercent, formatTime } from '../utils/time';

const EVENT_OPTIONS = [
  { value: 'basvuru_create', label: 'Başvuru Yapıldı', color: '#6366f1' },
  { value: 'basvuru_accept', label: 'Onaylandı', color: '#10b981' },
  { value: 'basvuru_reject', label: 'Reddedildi', color: '#ef4444' }
];

const AppLogPage = ({ logs, viewWindow, setViewWindow, globalRange, selectedTags }) => {
  const [selectedEvents, setSelectedEvents] = useState(['basvuru_create', 'basvuru_accept', 'basvuru_reject']);

  const { parsed } = useLogFilter(logs, {
    typeFilter: (log, type) => type.includes('app') || type.includes('basvuru'),
    eventMatcher: (log, type, selected) => selected.some(se => type.includes(se.replace('basvuru_', ''))),
    selectedEvents,
    selectedTags,
    reducer: (filteredLogs) => {
      const apps = {};
      filteredLogs.forEach(log => {
        const appId = log.category_name || "Genel Başvuru";
        if (!apps[appId]) apps[appId] = [];
        apps[appId].push(log);
      });
      return apps;
    }
  });

  const timeMin = viewWindow ? viewWindow[0] : 0;
  const timeMax = viewWindow ? viewWindow[1] : 0;
  const hasAnyData = Object.keys(parsed).length > 0;

  return (
    <LogPageLayout
      title="Başvuru Logları"
      icon={<FileText />}
      iconColor="#6366f1"
      eventOptions={EVENT_OPTIONS}
      selectedEvents={selectedEvents}
      setSelectedEvents={setSelectedEvents}
      viewWindow={viewWindow}
      setViewWindow={setViewWindow}
      globalRange={globalRange}
      hasAnyData={hasAnyData}
      emptyMessage="Seçilen günde başvuru etkinliği yok."
    >
        {Object.entries(parsed).map(([appId, events]) => (
          <div key={appId} style={{ marginBottom: '30px' }}>
            <h3 style={{ fontSize: '1.1rem', color: '#6366f1', marginBottom: '16px' }}>{appId}</h3>
            <div style={{ position: 'relative', height: '40px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px' }}>
              <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '4px', background: 'rgba(255,255,255,0.05)', transform: 'translateY(-50%)' }} />
              
              {events.map((ev, i) => {
                 const pct = getPercent(ev.ts, timeMin, timeMax);
                 if (pct < 0 || pct > 100) return null;

                 let icon = "📄";
                 if (ev.event_type.includes('accept') || ev.event_type.includes('approve')) icon = "✅";
                 if (ev.event_type.includes('reject') || ev.event_type.includes('deny')) icon = "❌";
                 
                 return (
                   <div key={i} className="msg-dot" style={{ position: 'absolute', left: `${pct}%`, top: '50%', transform: 'translate(-50%, -50%)', cursor: 'pointer', zIndex: 10 }}>
                      <div style={{ fontSize: '20px' }}>{icon}</div>
                      
                      <div className="msg-tooltip" style={{ width: '300px' }}>
                         <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '8px' }}>
                           <FileText size={18} />
                           <strong style={{ fontSize: '1rem' }}>Başvuru İşlemi</strong>
                         </div>
                         <div style={{ color: '#ccc', fontSize: '0.85rem', marginBottom: '8px' }}>
                           Saat: {formatTime(ev.ts)}<br/>
                           Kullanıcı: {ev.username || ev.user_id || "Bilinmiyor"}
                         </div>
                         <div style={{ color: '#eee', fontSize: '0.9rem', whiteSpace: 'pre-wrap', maxHeight: '300px', overflowY: 'auto' }}>
                           {(ev.details_obj && ev.details_obj.text) ? ev.details_obj.text : (ev.details || "Başvuru olayı.")}
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

export default AppLogPage;
