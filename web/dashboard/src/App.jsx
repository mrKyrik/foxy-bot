import React, { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

// Layouts
import MainLayout from './layouts/MainLayout';
import LogSystemLayout from './layouts/LogSystemLayout';

// Pages
import LoginPage from './pages/LoginPage';
import OverviewPage from './pages/OverviewPage';
import CommandManagementPage from './pages/CommandManagementPage';
import FormManagementPage from './pages/FormManagementPage';
import PanelAuthPage from './pages/PanelAuthPage';

import CallbackPage from './pages/CallbackPage';

import { GuildProvider } from './GuildContext';
import './index.css';

function App() {
  const [authToken, setAuthToken] = useState(localStorage.getItem('kumiho_token'));

  if (!authToken) {
    return (
      <Routes>
        <Route path="/auth/callback" element={<CallbackPage />} />
        <Route path="*" element={<LoginPage />} />
      </Routes>
    );
  }

  return (
    <GuildProvider>
      <Routes>
        {/* Genel Yönetim Sayfaları (Main Layout) */}
        <Route path="/" element={<MainLayout setAuthToken={setAuthToken} />}>
          <Route index element={<OverviewPage />} />
          <Route path="commands" element={<CommandManagementPage />} />
          <Route path="forms" element={<FormManagementPage />} />
          <Route path="auth" element={<PanelAuthPage />} />
        </Route>

        {/* Log Sistemi (Log Layout) */}
        <Route path="/logs/*" element={<LogSystemLayout />} />

        {/* Fallback Route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </GuildProvider>
  );
}

export default App;
