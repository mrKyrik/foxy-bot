import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import LoginPage from './pages/LoginPage';
import OverviewPage from './pages/OverviewPage';
import SettingsPage from './pages/SettingsPage';
import CommandManagementPage from './pages/CommandManagementPage';
import VoiceLogPage from './pages/VoiceLogPage';
import MessageLogPage from './pages/MessageLogPage';
import ModLogPage from './pages/ModLogPage';
import ServerLogPage from './pages/ServerLogPage';
import WarnLogPage from './pages/WarnLogPage';
import TicketLogPage from './pages/TicketLogPage';
import AppLogPage from './pages/AppLogPage';
import InviteLogPage from './pages/InviteLogPage';
import RoleLogPage from './pages/RoleLogPage';
import TimelineMinimap from './components/TimelineMinimap';
import GlobalTimePicker from './components/GlobalTimePicker';
import UserLookPanel from './components/UserLookPanel';
import { GUILD_ID, API_BASE_URL } from './config';
import './index.css';

function App() {
  const [authToken, setAuthToken] = useState(localStorage.getItem('kumiho_token'));
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({ total_events: 0, admin_actions: 0, voice_events: 0 });
  
  // User Look Panel State
  const [selectedUserForLook, setSelectedUserForLook] = useState(null);
  
  // Yeni Zaman State'leri
  const [fetchRange, setFetchRange] = useState(() => {
    const end = Date.now();
    const start = end - 86400000; // Default: Son 24 saat
    return { start, end, isLive: true, hours: 24 };
  });
  const [globalRange, setGlobalRange] = useState(null);
  const [viewWindow, setViewWindow] = useState(null);

  const [selectedTags, setSelectedTags] = useState([]);
  const [availableTags, setAvailableTags] = useState([]);

  useEffect(() => {
    fetchData();
    const pollInterval = setInterval(fetchData, 3000);
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

      const url = `${API_BASE_URL}/logs/${GUILD_ID}?start_time=${currentStart}&end_time=${currentEnd}`;
      const logRes = await axios.get(url);
      const allLogs = logRes.data.logs || []; // fallback to [] if undefined
      
      const userMap = new Map();
      const channelMap = new Map();
      const categoryMap = new Map();
      const roleMap = new Map();

      // Set globalRange and viewWindow explicitly based on fetchRange
      setGlobalRange([currentStart, currentEnd]);
      setViewWindow(prev => {
          // If viewWindow is outside fetchRange or null, reset it to full fetchRange
          if (!prev || prev[0] < currentStart || prev[1] > currentEnd) {
              return [currentStart, currentEnd];
          }
          return prev;
      });

      allLogs.forEach(l => {
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

      const statRes = await axios.get(`${API_BASE_URL}/stats/${GUILD_ID}`);
      setStats(statRes.data);
    } catch (error) {
      console.error("Veri çekme hatası:", error);
    }
  };

  if (!authToken) {
    return <LoginPage setAuthToken={setAuthToken} />;
  }

  return (
    <div className="dashboard-layout">
      <Sidebar availableTags={availableTags} selectedTags={selectedTags} setSelectedTags={setSelectedTags} setAuthToken={setAuthToken} />
      <main className="main-content" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <Routes>
            {/* Yönetim / Ana Sayfalar (Timeline Yok) */}
            <Route path="/">
              <Route index element={<OverviewPage />} />
              <Route path="commands" element={<CommandManagementPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            {/* Log Sayfaları (Timeline Var) */}
            <Route path="/logs/*" element={
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexShrink: 0, position: 'relative' }}>
                  <div>
                    <h1 style={{ fontSize: '2rem', fontWeight: 'bold' }}>Sistem Logları</h1>
                    <p style={{ color: 'var(--text-secondary)' }}>Kumiho gelişmiş izleme paneli.</p>
                  </div>
                  <GlobalTimePicker fetchRange={fetchRange} setFetchRange={setFetchRange} />
                </header>
                
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
                  </Routes>
                </div>

                {globalRange && viewWindow && (
                  <div style={{ flexShrink: 0, marginTop: '24px' }}>
                    <TimelineMinimap globalRange={globalRange} viewWindow={viewWindow} setViewWindow={setViewWindow} />
                  </div>
                )}
              </div>
            } />
          </Routes>
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
}

export default App;
