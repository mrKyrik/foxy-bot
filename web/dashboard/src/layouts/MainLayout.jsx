import React from 'react';
import { Outlet } from 'react-router-dom';
import MainSidebar from '../components/MainSidebar';

const MainLayout = ({ setAuthToken }) => {
  return (
    <div className="dashboard-layout">
      <MainSidebar setAuthToken={setAuthToken} />
      <main className="main-content" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default MainLayout;
