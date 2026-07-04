import React, { useState, useEffect, useRef } from 'react';
import { Mic } from 'lucide-react';
import LogPageLayout from '../components/LogPageLayout';
import { useLogFilter } from '../hooks/useLogFilter';
import { getPercent } from '../utils/time';

const EVENT_OPTIONS = [
  { value: 'ses_join', label: 'Kanala Katıldı', color: 'var(--accent-green)' },
  { value: 'ses_leave', label: 'Kanaldan Ayrıldı', color: 'var(--accent-red)' },
  { value: 'ses_move', label: 'Kanal Değiştirdi', color: 'var(--accent-blue)' },
  { value: 'ses_camera', label: 'Kamera', color: 'var(--accent-green)' },
  { value: 'ses_stream', label: 'Ekran Paylaşımı', color: 'var(--accent-purple)' }
];

const VoiceLogPage = ({ logs, viewWindow, setViewWindow, globalRange, selectedTags, onUserClick }) => {
  const [selectedEvents, setSelectedEvents] = useState(['ses_join', 'ses_leave', 'ses_move', 'ses_camera', 'ses_stream']);
  const containerRef = useRef(null);

  const { parsed } = useLogFilter(logs, {
    typeFilter: (log, type) => type.startsWith('ses_') || type.startsWith('voice'),
    eventMatcher: (log, type, selected) => {
      if (type === 'ses_join' && selected.includes('ses_join')) return true;
      if (type === 'ses_leave' && selected.includes('ses_leave')) return true;
      if ((type === 'ses_switch_join' || type === 'ses_switch_leave') && selected.includes('ses_move')) return true;
      if ((type === 'ses_camera_on' || type === 'ses_camera_off') && selected.includes('ses_camera')) return true;
      if ((type === 'ses_stream_on' || type === 'ses_stream_off') && selected.includes('ses_stream')) return true;
      return false;
    },
    selectedEvents,
    selectedTags,
    reducer: (filteredLogs) => {
      const channels = {};
      const portalList = [];

      filteredLogs.forEach(log => {
        const type = log.event_type;
        const cId = log.channel_id || "Bilinmeyen Kanal";
        const cName = log.channel_name || cId;
        const uId = log.user_id;
        const uname = log.username || (log.details_obj && log.details_obj.username) || uId;
        const uav = log.avatar_url || (log.details_obj && log.details_obj.avatar_url) || null;

        if (!channels[cId]) channels[cId] = { id: cId, name: cName, users: {} };
        if (!channels[cId].users[uId]) {
          channels[cId].users[uId] = { id: uId, username: uname, avatar_url: uav, sessions: [] };
        }

        const userObj = channels[cId].users[uId];
        let activeSession = userObj.sessions.find(s => !s.leave);

        if (type === 'ses_join' || type === 'ses_switch_join') {
          if (!activeSession) {
            userObj.sessions.push({ join: log.ts, leave: null, streams: [], cameras: [] });
            activeSession = userObj.sessions[userObj.sessions.length - 1];
          }
          if (type === 'ses_switch_join') {
            portalList.push({ type: 'join', uId, cId, ts: log.ts });
          }
        } else if (type === 'ses_leave' || type === 'ses_switch_leave') {
          if (activeSession) activeSession.leave = log.ts;
          if (type === 'ses_switch_leave') {
            portalList.push({ type: 'leave', uId, cId, ts: log.ts });
          }
        } else if (type === 'ses_camera_on') {
          const targetSession = activeSession || userObj.sessions[userObj.sessions.length - 1];
          if (targetSession) targetSession.cameras.push({ start: log.ts, end: null });
        } else if (type === 'ses_camera_off') {
          const targetSession = activeSession || userObj.sessions[userObj.sessions.length - 1];
          if (targetSession) {
            let activeCam = targetSession.cameras.find(c => !c.end);
            if (activeCam) activeCam.end = log.ts;
          }
        } else if (type === 'ses_stream_on') {
          const targetSession = activeSession || userObj.sessions[userObj.sessions.length - 1];
          if (targetSession) targetSession.streams.push({ start: log.ts, end: null });
        } else if (type === 'ses_stream_off') {
          const targetSession = activeSession || userObj.sessions[userObj.sessions.length - 1];
          if (targetSession) {
            let activeStream = targetSession.streams.find(s => !s.end);
            if (activeStream) activeStream.end = log.ts;
          }
        }
      });
      return { channels, portals: portalList };
    }
  });

  const nowTS = Date.now();
  const timeMin = viewWindow ? viewWindow[0] : 0;
  const timeMax = viewWindow ? viewWindow[1] : 0;
  const hasAnyData = Object.keys(parsed.channels).length > 0;

  return (
    <LogPageLayout
      title="Ses Hareketleri"
      icon={<Mic />}
      iconColor="var(--accent-green)"
      eventOptions={EVENT_OPTIONS}
      selectedEvents={selectedEvents}
      setSelectedEvents={setSelectedEvents}
      viewWindow={viewWindow}
      setViewWindow={setViewWindow}
      globalRange={globalRange}
      hasAnyData={hasAnyData}
      emptyMessage="Seçilen zaman diliminde gösterilecek ses etkinliği yok."
    >
      <div 
        ref={containerRef}
        style={{ position: 'relative', width: '100%', minHeight: '100%' }}
      >
        {nowTS >= timeMin && nowTS <= timeMax && (
          <div style={{ position: 'absolute', top: 0, bottom: 0, left: `${getPercent(nowTS, timeMin, timeMax)}%`, width: '2px', background: 'var(--accent-red)', zIndex: 5, boxShadow: '0 0 10px red' }} />
        )}

        {Object.values(parsed.channels).map(channel => (
          <div key={channel.id} style={{ marginBottom: '24px' }}>
            <h4 style={{ color: 'var(--text-secondary)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1rem' }}>
              <span style={{ display: 'inline-block', width: '10px', height: '10px', background: 'var(--accent-green)', borderRadius: '50%', boxShadow: '0 0 8px var(--accent-green)' }}></span>
              {channel.name !== channel.id ? channel.name : (channel.id === 'Bilinmeyen Kanal' ? channel.id : `<#${channel.id}>`)}
            </h4>
            
            {Object.values(channel.users).map(user => (
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

                      const portalsInSession = parsed.portals.filter(p => p.uId === user.id && p.cId === channel.id && (Math.abs(p.ts - session.join) < 2000 || Math.abs(p.ts - session.leave) < 2000));

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

                           {session.cameras.map((cam, i) => {
                              const cStart = getPercent(cam.start, timeMin, timeMax);
                              const actualEnd = cam.end ? cam.end : (session.leave ? session.leave : nowTS);
                              const cEnd = getPercent(actualEnd, timeMin, timeMax);
                              if (cEnd < 0 || cStart > 100) return null;
                              return <div key={'c'+i} style={{ position: 'absolute', left: `${Math.max(0, cStart)}%`, width: `${Math.min(100 - Math.max(0, cStart), cEnd - Math.max(0, cStart))}%`, top: '20px', height: '6px', background: 'var(--accent-green)', borderRadius: '2px', boxShadow: '0 0 8px var(--accent-green)' }} title="Kamera" />
                           })}
                           
                           {session.streams.map((str, i) => {
                              const sStart = getPercent(str.start, timeMin, timeMax);
                              const actualEnd = str.end ? str.end : (session.leave ? session.leave : nowTS);
                              const sEnd = getPercent(actualEnd, timeMin, timeMax);
                              if (sEnd < 0 || sStart > 100) return null;
                              return <div key={'s'+i} style={{ position: 'absolute', left: `${Math.max(0, sStart)}%`, width: `${Math.min(100 - Math.max(0, sStart), sEnd - Math.max(0, sStart))}%`, top: '4px', height: '6px', background: 'var(--accent-purple)', borderRadius: '2px', boxShadow: '0 0 8px var(--accent-purple)' }} title="Ekran Paylaşımı" />
                           })}

                           {portalsInSession.map((p, pIdx) => {
                              const pPct = getPercent(p.ts, timeMin, timeMax);
                              if (pPct < 0 || pPct > 100) return null;
                              return (
                                <div 
                                  id={`portal-${p.uId}-${p.ts}`}
                                  key={'p'+pIdx} 
                                  className="portal-container" 
                                  style={{ left: `${pPct}%`, top: '50%', zIndex: 20 }} 
                                  title={`Kanal Değiştirdi (${p.type === 'join' ? 'Buraya Geldi' : 'Buradan Gitti'})`}
                                >
                                  <div className="portal"></div>
                                </div>
                              )
                           })}
                         </div>
                      )
                   })}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </LogPageLayout>
  );
};

export default VoiceLogPage;
