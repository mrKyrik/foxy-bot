import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import MainSidebar from '../components/MainSidebar';

const MainLayout = ({ setAuthToken }) => {
  const location = useLocation();

  return (
    <div className="dashboard-layout">
      <MainSidebar setAuthToken={setAuthToken} />
      <main className="main-content" style={{ display: 'flex', flexDirection: 'column' }}>
        <AnimatePresence mode="wait">
          <motion.div 
            key={location.pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
};

export default MainLayout;
