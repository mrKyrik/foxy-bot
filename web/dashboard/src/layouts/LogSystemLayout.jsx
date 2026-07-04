import React, { useState, useEffect, useRef, useContext } from 'react';
import axios from 'axios';
import { Routes, Route, useLocation } from 'react-router-dom';
import LogSidebar from '../components/LogSidebar';
import TimelineMinimap from '../components/TimelineMinimap';
import GlobalTimePicker from '../components/GlobalTimePicker';
import UserLookPanel from '../components/UserLookPanel';

// Pages
import VoiceLogPage from '../pages/VoiceLogPage';
import MessageLogPage from '../pages/MessageLogPage';
import ModLogPage from '../pages/ModLogPage';
import ServerLogPage from '../pages/ServerLogPage';
import WarnLogPage from '../pages/WarnLogPage';
import TicketLogPage from '../pages/TicketLogPage';
import AppLogPage from '../pages/AppLogPage';
import InviteLogPage from '../pages/InviteLogPage';
import RoleLogPage from '../pages/RoleLogPage';
import SettingsPage from '../pages/SettingsPage';

import { API_BASE_URL } from '../config';
import { GuildContext } from '../GuildContext';

const LogSystemLayout = () => {
  const { activeGuildId } = useContext(GuildContext);
  const location = useLocation();
  const isSettings = location.pathname.includes('/settings');
  const [logs, setLogs] = useState([]);
  
  // User Look Panel State
  const [selectedUserForLook, setSelectedUserForLook] = useState(null);
  
  // Zaman State'leri
  const [fetchRange, setFetchRange] = useState(() => {
    const end = Date.now();
    const start = end - (86400000 * 7); // Default: Son 7 gün
    return { start, end, isLive: true, hours: 168 };
  });
  const [globalRange, setGlobalRange] = useState(null);
  const [viewWindow, setViewWindow] = useState(null);

  const [selectedTags, setSelectedTags] = useState([]);
  const [availableTags, setAvailableTags] = useState([]);

  const lastDataSignature = useRef('');

  useEffect(() => {
    fetchData();
    const pollInterval = setInterval(fetchData, 5000);
    return () => clearInterval(pollInterval);
  }, [fetchRange]);

  const fetchData = async () => {
    try {
      let currentStart = fetchRange.start;
      let currentEnd = fetchRange.end;
      
      if (fetchRange.isLive && fetchRange.hours) {
        currentEnd = Date.now();
        currentStart = currentEnd - (fetchRange.hours * 60 * 60 * 1000);
      }
      
      if (!activeGuildId) return;

      const url = `${API_BASE_URL}/logs/${activeGuildId}?start_time=${currentStart}&end_time=${currentEnd}`;
      const logRes = await axios.get(url);
      const allLogs = logRes.data.logs || []; 
      
      const newSig = allLogs.length > 0 ? `${allLogs.length}-${allLogs[0].id}-${allLogs[allLogs.length-1].id}` : 'empty';
      if (lastDataSignature.current === newSig) {
        setGlobalRange([currentStart, currentEnd]);
        return;
      }
      lastDataSignature.current = newSig;

      const userMap = new Map();
      const channelMap = new Map();
      const categoryMap = new Map();
      const roleMap = new Map();

      setGlobalRange([currentStart, currentEnd]);
      setViewWindow(prev => {
          if (!prev || prev[0] < currentStart || prev[1] > currentEnd) {
              return [currentStart, currentEnd];
          }
          return prev;
      });

      allLogs.forEach(l => {
         l.ts = l.timestamp; // Fix ev.ts undefined issue
         // Users
         if (l.user_id && !userMap.has(l.user_id)) {
            userMap.set(l.user_id, { type: 'user', id: l.user_id, name: l.username || l.user_id, avatar_url: l.avatar_url });
         }
         if (l.admin_id && !userMap.has(l.admin_id)) {
            userMap.set(l.admin_id, { type: 'user', id: l.admin_id, name: l.admin_name || l.admin_id, avatar_url: l.admin_avatar_url });
         }
         // Roles & Channels
         const isRoleEvent = l.event_type && (l.event_type.includes('role') || l.event_type.includes('rol'));
         if (isRoleEvent) {
             const rId = l.role_id || l.channel_id;
             if (rId && !roleMap.has(rId)) {
                 roleMap.set(rId, { type: 'role', id: rId, name: l.role_name || rId });
             }
         } else {
             if (l.channel_id && !channelMap.has(l.channel_id)) {
                 channelMap.set(l.channel_id, { type: 'channel', id: l.channel_id, name: l.channel_name || l.channel_id });
             }
         }
         
         // Categories
         if (l.category_id && !categoryMap.has(l.category_id)) {
            categoryMap.set(l.category_id, { type: 'category', id: l.category_id, name: l.category_name || l.category_id });
         }
      });
      setAvailableTags([...userMap.values(), ...roleMap.values(), ...channelMap.values(), ...categoryMap.values()]);
      setLogs(allLogs);

    } catch (error) {
      console.error("Veri çekme hatası:", error);
    }
  };

  return (
    <div className="dashboard-layout">
      <LogSidebar availableTags={availableTags} selectedTags={selectedTags} setSelectedTags={setSelectedTags} />
      
      <main className="main-content" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          
          {!isSettings && (
            <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexShrink: 0, position: 'relative' }}>
              <div>
                <h1 style={{ fontSize: '2rem', fontWeight: 'bold' }}>Sistem Logları</h1>
                <p style={{ color: 'var(--text-secondary)' }}>Kumiho gelişmiş izleme paneli.</p>
              </div>
              <GlobalTimePicker fetchRange={fetchRange} setFetchRange={setFetchRange} />
            </header>
          )}
          
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <Routes>
              <Route path="ses" element={<VoiceLogPage logs={logs} viewWindow={viewWindow} setViewWindow={setViewWindow} globalRange={globalRange} selectedTags={selectedTags} onUserClick={setSelectedUserForLook} />} />
              <Route path="mesaj" element={<MessageLogPage logs={logs} viewWindow={viewWindow} setViewWindow={setViewWindow} globalRange={globalRange} selectedTags={selectedTags} onUserClick={setSelectedUserForLook} />} />
              <Route path="mod" element={<ModLogPage logs={logs} viewWindow={viewWindow} setViewWindow={setViewWindow} globalRange={globalRange} selectedTags={selectedTags} onUserClick={setSelectedUserForLook} />} />
              <Route path="sunucu" element={<ServerLogPage logs={logs} viewWindow={viewWindow} setViewWindow={setViewWindow} globalRange={globalRange} selectedTags={selectedTags} onUserClick={setSelectedUserForLook} />} />
              <Route path="uyari" element={<WarnLogPage logs={logs} viewWindow={viewWindow} setViewWindow={setViewWindow} globalRange={globalRange} selectedTags={selectedTags} onUserClick={setSelectedUserForLook} />} />
              <Route path="ticket" element={<TicketLogPage logs={logs} viewWindow={viewWindow} setViewWindow={setViewWindow} globalRange={globalRange} selectedTags={selectedTags} onUserClick={setSelectedUserForLook} />} />
              <Route path="basvuru" element={<AppLogPage logs={logs} viewWindow={viewWindow} setViewWindow={setViewWindow} globalRange={globalRange} selectedTags={selectedTags} onUserClick={setSelectedUserForLook} />} />
              <Route path="davet" element={<InviteLogPage logs={logs} viewWindow={viewWindow} setViewWindow={setViewWindow} globalRange={globalRange} selectedTags={selectedTags} onUserClick={setSelectedUserForLook} />} />
              <Route path="rol" element={<RoleLogPage logs={logs} viewWindow={viewWindow} setViewWindow={setViewWindow} globalRange={globalRange} selectedTags={selectedTags} onUserClick={setSelectedUserForLook} />} />
              <Route path="settings" element={<SettingsPage />} />
            </Routes>
          </div>

          {!isSettings && globalRange && viewWindow && (
            <div style={{ flexShrink: 0, marginTop: '24px' }}>
              <TimelineMinimap globalRange={globalRange} viewWindow={viewWindow} setViewWindow={setViewWindow} />
            </div>
          )}
          
        </div>
      </main>

      {selectedUserForLook && (
        <UserLookPanel 
          user={selectedUserForLook} 
          allLogs={logs} 
          onClose={() => setSelectedUserForLook(null)} 
        />
      )}
    </div>
  );
};

export default LogSystemLayout;
