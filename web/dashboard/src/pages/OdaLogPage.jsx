import React, { useState, useEffect, useRef } from 'react';
import { Headphones, ChevronDown, ChevronRight, Settings, Users } from 'lucide-react';
import LogPageLayout from '../components/LogPageLayout';
import RoomAdminPanel from '../components/RoomAdminPanel';
import RoomSettingsModal from '../components/RoomSettingsModal';
import { useLogFilter } from '../hooks/useLogFilter';
import { getPercent } from '../utils/time';

const EVENT_OPTIONS = [
  { value: 'oda_create', label: 'Oda Oluşturma', color: 'var(--accent-green)' },
  { value: 'oda_delete', label: 'Oda Silinme', color: 'var(--accent-red)' },
  { value: 'oda_update', label: 'Oda Ayar Değişikliği', color: 'var(--accent-blue)' },
  { value: 'oda_participant', label: 'Oda Katılımcı Hareketi', color: 'var(--accent-purple)' }
];

const OdaLogPage = ({ logs, viewWindow, setViewWindow, globalRange, selectedTags, onUserClick }) => {
  const [selectedEvents, setSelectedEvents] = useState(['oda_create', 'oda_delete', 'oda_update', 'oda_participant']);
  const [expandedRooms, setExpandedRooms] = useState({});
  const [modalState, setModalState] = useState({ isOpen: false, userId: null, userName: '' });
  const containerRef = useRef(null);

  const { parsed } = useLogFilter(logs, {
    typeFilter: (log, type) => type.startsWith('oda_'),
    eventMatcher: (log, type, selected) => {
      if (type === 'oda_create' && selected.includes('oda_create')) return true;
      if (type === 'oda_delete' && selected.includes('oda_delete')) return true;
      if (type === 'oda_update' && selected.includes('oda_update')) return true;
      if (type === 'oda_participant' && selected.includes('oda_participant')) return true;
      return false;
    },
    selectedEvents,
    selectedTags,
    reducer: (filteredLogs) => {
      // 1. Aşama: Hangi oda (channel_id) kimin? (owner_id)
      const roomOwners = {};
      filteredLogs.forEach(log => {
        if (['oda_create', 'oda_update', 'oda_delete'].includes(log.event_type) && log.channel_id) {
          if (!roomOwners[log.channel_id]) {
            roomOwners[log.channel_id] = {
              userId: log.user_id,
              username: log.username || (log.details_obj && log.details_obj.username) || (log.details && log.details.username) || log.user_id,
              avatar: log.avatar_url || (log.details_obj && log.details_obj.avatar_url) || (log.details && log.details.avatar_url) || null
            };
          }
        }
      });

      // 2. Aşama: Kullanıcı (Owner) bazlı gruplama
      const groups = {};
      filteredLogs.forEach(log => {
        let ownerId = log.user_id; // Default to log's user
        let ownerName = log.username || (log.details_obj && log.details_obj.username) || (log.details && log.details.username) || ownerId;
        let ownerAvatar = log.avatar_url || (log.details_obj && log.details_obj.avatar_url) || (log.details && log.details.avatar_url) || null;

        // Katılımcı olayları (participant) oda sahibine yazılmalı
        if (log.event_type === 'oda_participant' && log.channel_id && roomOwners[log.channel_id]) {
            const owner = roomOwners[log.channel_id];
            ownerId = owner.userId;
            ownerName = owner.username;
            ownerAvatar = owner.avatar;
        }

        const groupId = `user_${ownerId}`;
        
        if (!groups[groupId]) {
            groups[groupId] = { 
                id: groupId, 
                userId: ownerId,
                name: ownerName, 
                avatar: ownerAvatar,
                events: [],
                lastChannelId: null,
                participants: {} // For the voice-log style timeline
            };
        }
        groups[groupId].events.push(log);
        
        if (log.channel_id && log.event_type !== 'oda_participant') {
            groups[groupId].lastChannelId = log.channel_id;
        }

        // Katılımcı olayıysa session'a çevir
        if (log.event_type === 'oda_participant') {
            const pId = log.user_id; // Katılan kişinin ID'si
            const pName = log.username || (log.details_obj && log.details_obj.username) || (log.details && log.details.username) || pId;
            const pAvatar = log.avatar_url || (log.details_obj && log.details_obj.avatar_url) || (log.details && log.details.avatar_url) || null;
            const text = (log.details_obj && log.details_obj.text) ? log.details_obj.text : ((log.details && log.details.text) ? log.details.text : "");

            if (!groups[groupId].participants[pId]) {
                groups[groupId].participants[pId] = {
                    id: pId, username: pName, avatar_url: pAvatar, sessions: []
                };
            }
            const pUser = groups[groupId].participants[pId];
            let activeSession = pUser.sessions.find(s => !s.leave);

            if (text.includes("katıldı")) {
                if (!activeSession) {
                    pUser.sessions.push({ join: log.ts, leave: null, streams: [], cameras: [] });
                }
            } else if (text.includes("ayrıldı")) {
                if (activeSession) activeSession.leave = log.ts;
            } else if (text.includes("Kamerasını açtı")) {
                const targetSession = activeSession || pUser.sessions[pUser.sessions.length - 1];
                if (targetSession) targetSession.cameras.push({ start: log.ts, end: null });
            } else if (text.includes("Kamerasını kapattı")) {
                const targetSession = activeSession || pUser.sessions[pUser.sessions.length - 1];
                if (targetSession) {
                    let activeCam = targetSession.cameras.find(c => !c.end);
                    if (activeCam) activeCam.end = log.ts;
                }
            } else if (text.includes("Ekran yayını açtı")) {
                const targetSession = activeSession || pUser.sessions[pUser.sessions.length - 1];
                if (targetSession) targetSession.streams.push({ start: log.ts, end: null });
            } else if (text.includes("Yayını kapattı")) {
                const targetSession = activeSession || pUser.sessions[pUser.sessions.length - 1];
                if (targetSession) {
                    let activeStream = targetSession.streams.find(s => !s.end);
                    if (activeStream) activeStream.end = log.ts;
                }
            }
        }
      });

      return Object.values(groups).sort((a, b) => {
         const lastA = a.events[a.events.length - 1];
         const lastB = b.events[b.events.length - 1];
         return (lastB?.ts || 0) - (lastA?.ts || 0);
      });
    }
  });

  const nowTS = Date.now();
  const timeMin = viewWindow ? viewWindow[0] : 0;
  const timeMax = viewWindow ? viewWindow[1] : 0;
  const hasAnyData = Object.keys(parsed).length > 0;

  const toggleRoom = (roomId) => {
    setExpandedRooms(prev => ({ ...prev, [roomId]: !prev[roomId] }));
  };

  const renderLogDetail = (ev) => {
    let color = 'rgba(255,255,255,0.2)';
    let text = ev.event_type;
    if (ev.event_type === 'oda_create') { color = 'var(--accent-green)'; text = 'Oda Oluşturuldu'; }
    if (ev.event_type === 'oda_delete') { color = 'var(--accent-red)'; text = 'Oda Silindi'; }
    if (ev.event_type === 'oda_update') { color = 'var(--accent-blue)'; text = 'Oda Ayarı Değişti'; }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <span style={{
            display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%',
            background: color, boxShadow: `0 0 8px ${color}`
          }}></span>
          <span style={{ fontWeight: 600, color: '#fff' }}>{text}</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {new Date(ev.ts).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }
          </span>
        </div>

        {(() => {
          const uName = ev.username || (ev.details_obj && ev.details_obj.username) || (ev.details && ev.details.username);
          const uAv = ev.avatar_url || (ev.details_obj && ev.details_obj.avatar_url) || (ev.details && ev.details.avatar_url);
          const uText = (ev.details_obj && ev.details_obj.text) ? ev.details_obj.text : ((ev.details && ev.details.text) ? ev.details.text : null);
          
          return (
            <>
              {uName && (
                <div
                  style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', padding: '4px', borderRadius: '6px' }}
                  onClick={(e) => { e.stopPropagation(); onUserClick && onUserClick(ev.user_id); }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  {uAv ? (
                    <img src={uAv} alt="" style={{ width: '20px', height: '20px', borderRadius: '50%' }} />
                  ) : (
                    <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px' }}>?</div>
                  )}
                  <span style={{ color: 'var(--accent-blue)', fontWeight: 500, fontSize: '0.9rem' }}>{uName}</span>
                </div>
              )}

              {uText && (
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: '6px', borderLeft: `2px solid ${color}`, whiteSpace: 'pre-wrap' }}>
                  {uText}
                </div>
              )}
            </>
          );
        })()}
      </div>
    );
  };

  const renderTimeline = (events) => {
    return (
      <div className="timeline-row" style={{ height: '40px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', position: 'relative', overflow: 'visible', marginBottom: '8px' }}>
        <div style={{ position: 'absolute', top: '50%', left: 0, width: '100%', height: '2px', background: 'rgba(255,255,255,0.05)', transform: 'translateY(-50%)' }}></div>
        
        {events.map((ev, i) => {
            const pct = getPercent(ev.ts, timeMin, timeMax);
            if (pct < 0 || pct > 100) return null;

            let dotColor = 'rgba(255,255,255,0.5)';
            if (ev.event_type === 'oda_create') dotColor = 'var(--accent-green)';
            if (ev.event_type === 'oda_delete') dotColor = 'var(--accent-red)';
            if (ev.event_type === 'oda_update') dotColor = 'var(--accent-blue)';

            return (
              <div
                key={ev.id || i}
                className="event-dot"
                style={{
                  position: 'absolute',
                  left: `${pct}%`,
                  top: '50%',
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: dotColor,
                  transform: 'translate(-50%, -50%)',
                  cursor: 'pointer',
                  boxShadow: `0 0 6px ${dotColor}`,
                  zIndex: 10
                }}
              >
                <div className="tooltip" style={{
                  position: 'absolute',
                  bottom: '100%',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  background: 'rgba(15,23,42,0.95)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  padding: '12px',
                  borderRadius: '8px',
                  minWidth: '220px',
                  marginBottom: '8px',
                  zIndex: 100,
                  backdropFilter: 'blur(10px)',
                  pointerEvents: 'auto',
                  boxShadow: '0 8px 16px rgba(0,0,0,0.4)'
                }}>
                  {renderLogDetail(ev)}
                </div>
              </div>
            );
        })}
      </div>
    );
  };

  const renderParticipantSessions = (participants) => {
    return Object.values(participants).map(user => (
      <div key={user.id} className="user-track" style={{ display: 'flex', alignItems: 'center', marginBottom: '12px', height: '40px', position: 'relative' }}>
        <div style={{ width: '48px', minWidth: '48px', marginRight: '16px' }}>
          <img 
            src={user.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'} 
            alt={user.username} 
            style={{ width: '40px', height: '40px', borderRadius: '50%', border: '2px solid rgba(255,255,255,0.2)', cursor: 'pointer', transition: 'border 0.2s' }} 
            title={`${user.username} (Detaylar için tıkla)`} 
            onClick={() => onUserClick && onUserClick({ id: user.id, name: user.username, avatar_url: user.avatar_url })}
            onMouseOver={(e) => e.currentTarget.style.borderColor = 'var(--panel-border-glow)'}
            onMouseOut={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'}
          />
        </div>

        <div style={{ flex: 1, height: '100%', position: 'relative', background: 'rgba(0,0,0,0.4)', borderRadius: '8px', overflow: 'hidden' }}>
            {user.sessions.map((session, idx) => {
              const startPct = getPercent(session.join, timeMin, timeMax);
              const endPct = session.leave ? getPercent(session.leave, timeMin, timeMax) : 100;
              const isOngoing = !session.leave;
              
              if (endPct < 0 || startPct > 100) return null;

              return (
                  <div key={'s'+idx}>
                    <div style={{ 
                      position: 'absolute', 
                      left: `${Math.max(0, startPct)}%`, 
                      width: `${Math.min(100 - Math.max(0, startPct), endPct - Math.max(0, startPct))}%`, 
                      top: '50%',
                      transform: 'translateY(-50%)',
                      height: '30px', 
                      background: 'rgba(59, 130, 246, 0.15)', 
                      border: '1px solid rgba(59, 130, 246, 0.5)',
                      borderRadius: isOngoing ? '6px 0 0 6px' : '6px',
                      borderRight: isOngoing ? 'none' : '1px solid rgba(59, 130, 246, 0.5)',
                      boxShadow: 'inset 0 0 10px rgba(59,130,246,0.1)'
                    }}>
                      {isOngoing && endPct >= 100 && (
                        <div style={{ position: 'absolute', right: '-6px', top: '50%', transform: 'translateY(-50%)', width: '0', height: '0', borderTop: '8px solid transparent', borderBottom: '8px solid transparent', borderLeft: '8px solid rgba(59, 130, 246, 0.8)' }} />
                      )}
                    </div>

                    {session.cameras && session.cameras.map((cam, i) => {
                      const cStart = getPercent(cam.start, timeMin, timeMax);
                      const actualEnd = cam.end ? cam.end : (session.leave ? session.leave : nowTS);
                      const cEnd = getPercent(actualEnd, timeMin, timeMax);
                      if (cEnd < 0 || cStart > 100) return null;
                      return <div key={'c'+i} style={{ position: 'absolute', left: `${Math.max(0, cStart)}%`, width: `${Math.min(100 - Math.max(0, cStart), cEnd - Math.max(0, cStart))}%`, top: '20px', height: '6px', background: 'var(--accent-green)', borderRadius: '2px', boxShadow: '0 0 8px var(--accent-green)' }} title="Kamera" />
                    })}
                    
                    {session.streams && session.streams.map((str, i) => {
                      const sStart = getPercent(str.start, timeMin, timeMax);
                      const actualEnd = str.end ? str.end : (session.leave ? session.leave : nowTS);
                      const sEnd = getPercent(actualEnd, timeMin, timeMax);
                      if (sEnd < 0 || sStart > 100) return null;
                      return <div key={'s'+i} style={{ position: 'absolute', left: `${Math.max(0, sStart)}%`, width: `${Math.min(100 - Math.max(0, sStart), sEnd - Math.max(0, sStart))}%`, top: '4px', height: '6px', background: 'var(--accent-purple)', borderRadius: '2px', boxShadow: '0 0 8px var(--accent-purple)' }} title="Ekran Paylaşımı" />
                    })}
                  </div>
              )
            })}
        </div>
      </div>
    ));
  };

  return (
    <LogPageLayout
      title="Özel Oda Hareketleri (İnteraktif Paneller)"
      icon={<Headphones />}
      iconColor="var(--accent-purple)"
      eventOptions={EVENT_OPTIONS}
      selectedEvents={selectedEvents}
      setSelectedEvents={setSelectedEvents}
      viewWindow={viewWindow}
      setViewWindow={setViewWindow}
      globalRange={globalRange}
      hasAnyData={hasAnyData}
      emptyMessage="Seçilen filtrelerde özel oda etkinliği yok."
    >
      <div ref={containerRef}>
        {(Array.isArray(parsed) ? parsed : Object.values(parsed)).map(group => {
          const isExpanded = expandedRooms[group.id];
          const settingsEvents = group.events.filter(e => e.event_type !== 'oda_participant');
          const latestEvent = group.events[group.events.length - 1];
          const isDeleted = latestEvent?.event_type === 'oda_delete';
          const hasParticipants = Object.keys(group.participants).length > 0;

          return (
            <div key={group.id} style={{ marginBottom: '24px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', overflow: 'hidden' }}>
              <div 
                onClick={() => toggleRoom(group.id)}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px', cursor: 'pointer', background: isExpanded ? 'rgba(255,255,255,0.05)' : 'transparent', transition: 'background 0.2s' }}
              >
                <h4 style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                  {group.avatar ? (
                     <img src={group.avatar} alt={group.name} style={{ width: '24px', height: '24px', borderRadius: '50%', border: '1px solid rgba(255,255,255,0.1)' }} />
                  ) : (
                     <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Users size={14} /></div>
                  )}
                  <span style={{ fontWeight: 600, color: 'var(--accent-blue)' }}>{group.name}</span> 
                  <span style={{ color: 'var(--text-muted)' }}>adlı kullanıcının Odaları</span>
                  {isDeleted && <span style={{ fontSize: '0.75rem', background: 'rgba(239, 68, 68, 0.2)', color: 'var(--accent-red)', padding: '2px 6px', borderRadius: '4px', marginLeft: '8px' }}>ODA SİLİNDİ</span>}
                </h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    {group.events.length} Olay
                  </div>
                  <button 
                    onClick={(e) => { e.stopPropagation(); setModalState({ isOpen: true, userId: group.userId, userName: group.name }); }}
                    style={{ background: 'rgba(59, 130, 246, 0.1)', color: 'var(--accent-blue)', border: '1px solid rgba(59, 130, 246, 0.2)', padding: '6px 12px', borderRadius: '6px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', transition: 'all 0.2s' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.2)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.1)'}
                  >
                    <Settings size={14} /> Ayarları Yönet
                  </button>
                </div>
              </div>

              {isExpanded && (
                <div style={{ padding: '16px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ marginBottom: '24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      <Settings size={14} /> Tüm Oda Kurulum ve Ayar Geçmişi
                    </div>
                    {renderTimeline(settingsEvents)}
                  </div>
                  
                  {hasParticipants && (
                    <div style={{ marginBottom: '16px', position: 'relative' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        <Users size={14} /> Odaya Katılanlar ve Etkileşimler
                      </div>
                      
                      {nowTS >= timeMin && nowTS <= timeMax && (
                        <div style={{ position: 'absolute', top: '30px', bottom: 0, left: `${getPercent(nowTS, timeMin, timeMax)}%`, width: '2px', background: 'var(--accent-red)', zIndex: 5, boxShadow: '0 0 10px red' }} />
                      )}
                      
                      {renderParticipantSessions(group.participants)}
                    </div>
                  )}

                  {group.lastChannelId && !isDeleted && (
                    <div style={{ marginTop: '24px' }}>
                      <RoomAdminPanel channelId={group.lastChannelId} guildId={latestEvent?.guild_id} />
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <RoomSettingsModal 
        isOpen={modalState.isOpen} 
        onClose={() => setModalState({ isOpen: false, userId: null, userName: '' })}
        userId={modalState.userId}
        userName={modalState.userName}
      />
    </LogPageLayout>
  );
};

export default OdaLogPage;
