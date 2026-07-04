import React, { useState } from 'react';
import { Settings, PlusCircle, Trash2, Edit } from 'lucide-react';
import LogPageLayout from '../components/LogPageLayout';
import { useLogFilter } from '../hooks/useLogFilter';
import { getPercent, formatTime } from '../utils/time';
import DiscordMention from '../components/DiscordMention';

const EVENT_OPTIONS = [
  { value: 'create', label: 'Oluşturma', color: '#10b981' },
  { value: 'delete', label: 'Silme', color: '#ef4444' },
  { value: 'update', label: 'Güncelleme', color: '#3b82f6' }
];

const ServerLogPage = ({ logs, viewWindow, setViewWindow, globalRange, selectedTags }) => {
  const [selectedEvents, setSelectedEvents] = useState(['create', 'delete', 'update']);

  const { parsed } = useLogFilter(logs, {
    typeFilter: (log, type) => type.startsWith('srv_') || type.includes('channel') || type.includes('emoji'),
    eventMatcher: (log, type, selected) => {
        const detailStr = String(log.details || "").toLowerCase();
        const isCreate = type.includes('create') || type.includes('add') || detailStr.includes('oluşturuldu') || detailStr.includes('eklendi');
        const isDelete = type.includes('delete') || type.includes('remove') || detailStr.includes('silindi');
        const isUpdate = type.includes('update') || type.includes('edit') || detailStr.includes('güncellendi') || type === 'srv_perm';
        
        return selected.some(se => {
            if (se === 'create') return isCreate;
            if (se === 'delete') return isDelete;
            if (se === 'update') return isUpdate;
            return false;
        });
    },
    selectedEvents,
    selectedTags,
    reducer: (filteredLogs) => {
      const categories = {
        "Kanal Olayları": [],
        "Emoji/Sticker Olayları": [],
        "Genel Ayarlar": []
      };

      filteredLogs.forEach(log => {
        const type = log.event_type;
        if (type.includes('channel')) {
            categories["Kanal Olayları"].push(log);
        } else if (type.includes('emoji') || type.includes('sticker')) {
            categories["Emoji/Sticker Olayları"].push(log);
        } else {
            categories["Genel Ayarlar"].push(log);
        }
      });
      return categories;
    }
  });

  const timeMin = viewWindow ? viewWindow[0] : 0;
  const timeMax = viewWindow ? viewWindow[1] : 0;
  const hasAnyData = Object.values(parsed).some(arr => arr.length > 0);

  return (
    <LogPageLayout
      title="Sunucu Yapılandırma Logları"
      icon={<Settings />}
      iconColor="#a855f7"
      eventOptions={EVENT_OPTIONS}
      selectedEvents={selectedEvents}
      setSelectedEvents={setSelectedEvents}
      viewWindow={viewWindow}
      setViewWindow={setViewWindow}
      globalRange={globalRange}
      hasAnyData={hasAnyData}
      emptyMessage="Seçilen günde sunucu yapılandırma olayı yok."
    >
      {Object.entries(parsed).map(([catName, events]) => {
          if (events.length === 0) return null;
          
          return (
            <div key={catName} style={{ marginBottom: '30px' }}>
              <h3 style={{ fontSize: '1.1rem', color: '#a855f7', marginBottom: '16px' }}>{catName}</h3>
              <div style={{ position: 'relative', height: '40px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px' }}>
                <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '4px', background: 'rgba(255,255,255,0.05)', transform: 'translateY(-50%)' }} />
                
                {events.map((ev, i) => {
                    const pct = getPercent(ev.ts, timeMin, timeMax);
                    if (pct < 0 || pct > 100) return null;

                    let icon = <Edit size={16} color="#3b82f6" />;
                    let actionStr = "Değiştirildi";
                    const detailStr = String(ev.details || "").toLowerCase();
                    if (ev.event_type.includes('create') || ev.event_type.includes('add') || detailStr.includes('oluşturuldu') || detailStr.includes('eklendi')) { icon = <PlusCircle size={16} color="#10b981" />; actionStr = "Oluşturuldu"; }
                    if (ev.event_type.includes('delete') || ev.event_type.includes('remove') || detailStr.includes('silindi')) { icon = <Trash2 size={16} color="#ef4444" />; actionStr = "Silindi"; }
                    
                    return (
                      <div key={i} className="msg-dot" style={{ position: 'absolute', left: `${pct}%`, top: '50%', transform: 'translate(-50%, -50%)', cursor: 'pointer', zIndex: 10 }}>
                        <div style={{ background: 'rgba(0,0,0,0.8)', padding: '6px', borderRadius: '50%', border: '1px solid rgba(255,255,255,0.2)' }}>
                            {icon}
                        </div>
                        
                        <div className="msg-tooltip" style={{ width: '250px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '8px' }}>
                              {icon}
                              <strong style={{ fontSize: '1rem' }}>{actionStr}</strong>
                            </div>
                            <div style={{ color: '#ccc', fontSize: '0.85rem', marginBottom: '4px' }}>Saat: {formatTime(ev.ts)}</div>
                            <div style={{ color: '#eee', fontSize: '0.9rem' }}>
                              <DiscordMention text={ev.details || "Ayar değişti."} />
                            </div>
                        </div>
                      </div>
                    )
                })}
              </div>
            </div>
          )
      })}
    </LogPageLayout>
  );
};

export default ServerLogPage;
