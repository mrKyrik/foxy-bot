import React, { useState, useEffect } from 'react';
import { MessageSquare, ChevronDown, ChevronRight } from 'lucide-react';
import LogPageLayout from '../components/LogPageLayout';
import { useLogFilter } from '../hooks/useLogFilter';
import { getPercent, formatTime } from '../utils/time';

const EVENT_OPTIONS = [
  { value: 'msg_delete', label: 'Silinen Mesajlar', color: '#ef4444' },
  { value: 'msg_edit', label: 'Düzenlenen Mesajlar', color: '#f97316' }
];

const MessageLogPage = ({ logs, viewWindow, setViewWindow, globalRange, selectedTags, onUserClick }) => {
  const [selectedEvents, setSelectedEvents] = useState(['msg_delete', 'msg_edit']);
  const [expandedCategories, setExpandedCategories] = useState({});

  const { parsed } = useLogFilter(logs, {
      typeFilter: (log, type) => type.startsWith('msg_'),
      eventMatcher: (log, type, selected) => selected.includes(type),
      selectedEvents,
      selectedTags,
      reducer: (filteredLogs) => {
          const categories = {};
          filteredLogs.forEach(log => {
              const cId = log.channel_id || "Bilinmeyen Kanal";
              const cName = log.channel_name || cId;
              const catName = log.category_name || "Genel Kanallar";

              if (!categories[catName]) categories[catName] = {};
              if (!categories[catName][cId]) categories[catName][cId] = { id: cId, name: cName, events: [] };
              categories[catName][cId].events.push(log);
          });
          return categories;
      }
  });

  // İlk kategori geldiğinde otomatik aç — sadece henüz hiç açılmamışsa
  useEffect(() => {
    const keys = Object.keys(parsed);
    if (keys.length > 0) {
      setExpandedCategories(prev => {
        // Eğer hiç açık kategori yoksa ilkini aç
        const anyOpen = Object.values(prev).some(Boolean);
        if (!anyOpen) {
          return { [keys[0]]: true };
        }
        return prev;
      });
    }
  }, [parsed]);

  const toggleCategory = (cat) => {
    setExpandedCategories(prev => ({ ...prev, [cat]: !prev[cat] }));
  };

  const timeMin = viewWindow ? viewWindow[0] : 0;
  const timeMax = viewWindow ? viewWindow[1] : 0;
  const hasAnyData = Object.keys(parsed).length > 0;

  return (
    <LogPageLayout
      title="Mesaj Hareketleri"
      icon={<MessageSquare />}
      iconColor="var(--accent-blue)"
      eventOptions={EVENT_OPTIONS}
      selectedEvents={selectedEvents}
      setSelectedEvents={setSelectedEvents}
      viewWindow={viewWindow}
      setViewWindow={setViewWindow}
      globalRange={globalRange}
      hasAnyData={hasAnyData}
      emptyMessage="Seçilen filtrelerde mesaj etkinliği yok."
    >
      {Object.entries(parsed).map(([catName, channels]) => {
        const isExpanded = !!expandedCategories[catName];
        return (
          <div key={catName} style={{ marginBottom: '24px' }}>
            <div
              onClick={() => toggleCategory(catName)}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px', marginBottom: '12px' }}
            >
              {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
              <h3 style={{ fontSize: '1.1rem', margin: 0 }}>{catName}</h3>
              <span style={{ marginLeft: 'auto', background: 'rgba(0,0,0,0.5)', padding: '2px 8px', borderRadius: '12px', fontSize: '0.8rem' }}>
                {Object.keys(channels).length} Kanal
              </span>
            </div>

            {isExpanded && Object.values(channels).map(channel => (
              <div key={channel.id} style={{ marginLeft: '24px', marginBottom: '20px' }}>
                <h4 style={{ color: 'var(--text-secondary)', marginBottom: '8px', fontSize: '0.9rem' }}>
                  # {channel.name !== channel.id ? channel.name : channel.id}
                </h4>
                
                <div className="timeline-row" style={{ height: '40px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', position: 'relative', overflow: 'visible' }}>
                  <div style={{ position: 'absolute', top: '50%', left: 0, width: '100%', height: '2px', background: 'rgba(255,255,255,0.05)', transform: 'translateY(-50%)' }}></div>
                  
                  {channel.events.map((ev, i) => {
                      const pct = getPercent(ev.ts, timeMin, timeMax);
                      if (pct < 0 || pct > 100) return null;
                      
                      const isDelete = ev.event_type === 'msg_delete';
                      const dotColor = isDelete ? 'var(--accent-red)' : '#f97316';
                      
                      return (
                        <div
                            key={i}
                            className="msg-dot"
                            style={{ position: 'absolute', left: `${pct}%`, top: '50%', transform: 'translate(-50%, -50%)', cursor: 'pointer', zIndex: 7 }}
                        >
                            <div style={{width:'14px', height:'14px', background: dotColor, borderRadius:'50%', boxShadow: `0 0 10px ${dotColor}`}}></div>
                            
                            <div className="msg-tooltip" style={{ width: '280px' }}>
                              <div 
                                style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', cursor: 'pointer' }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (onUserClick) onUserClick({ id: ev.user_id || ev.username, name: ev.username || ev.user_id || "Bilinmeyen Kullanıcı", avatar_url: ev.avatar_url });
                                }}
                              >
                                <img src={ev.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'} style={{width:'24px', height:'24px', borderRadius:'50%'}} alt="avatar" />
                                <strong style={{ fontSize: '0.9rem', transition: 'color 0.2s' }} onMouseOver={(e) => e.currentTarget.style.color = 'var(--accent-blue)'} onMouseOut={(e) => e.currentTarget.style.color = '#fff'}>{ev.username || ev.user_id || "Bilinmeyen Kullanıcı"}</strong>
                              </div>
                              <div style={{ fontSize: '0.85rem', color: '#ccc', marginBottom: '8px' }}>
                                <span style={{ color: dotColor, fontWeight: 'bold' }}>{isDelete ? 'Sildi' : 'Düzenledi'}</span> - {formatTime(ev.ts)}
                              </div>
                              <div style={{ fontSize: '0.85rem', color: '#fff', wordBreak: 'break-word', background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}>
                                {ev.details_obj ? (
                                  ev.event_type === 'msg_delete' || ev.event_type === 'mod_msg_delete' ? (
                                    <>
                                    <div style={{color: 'var(--accent-red)', marginBottom: '4px', opacity: 0.8}}>Silinen İçerik:</div>
                                    <div>{ev.details_obj.content}</div>
                                    {ev.details_obj.mod_username && <div style={{marginTop: '8px', fontSize: '0.8rem', color: '#aaa'}}>Silen Yetkili: {ev.details_obj.mod_username}</div>}
                                    </>
                                  ) : (
                                    <>
                                    <div style={{color: 'var(--accent-red)', marginBottom: '4px', textDecoration: 'line-through', opacity: 0.8}}>{ev.details_obj.old_content}</div>
                                    <div style={{color: 'var(--accent-green)', marginTop: '4px'}}>{ev.details_obj.new_content}</div>
                                    {ev.details_obj.message_url && <a href={ev.details_obj.message_url} target="_blank" rel="noreferrer" style={{color: 'var(--accent-blue)', display: 'block', marginTop: '8px', fontSize: '0.8rem'}}>Mesaja Git</a>}
                                    </>
                                  )
                                ) : (
                                  ev.details || "İçerik bulunamadı"
                                )}
                              </div>
                            </div>
                        </div>
                      )
                  })}
                </div>
              </div>
            ))}
          </div>
        );
      })}
    </LogPageLayout>
  );
};

export default MessageLogPage;
