import React from 'react';
import { motion } from 'framer-motion';
import TimelineZoomArea from './TimelineZoomArea';
import EventCheckboxFilter from './EventCheckboxFilter';

const LogPageLayout = ({ 
    title, 
    icon, 
    iconColor, 
    eventOptions, 
    selectedEvents, 
    setSelectedEvents, 
    viewWindow, 
    setViewWindow, 
    globalRange, 
    hasAnyData,
    emptyMessage,
    children,
    headerRight
}) => {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="glass-panel timeline-container" 
      style={{ flex: 1, minHeight: 0 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            {React.cloneElement(icon, { size: 24, color: iconColor })} {title}
          </h2>
          {headerRight && <div>{headerRight}</div>}
      </div>
      
      {eventOptions && (
         <EventCheckboxFilter 
            options={eventOptions} 
            selectedEvents={selectedEvents} 
            setSelectedEvents={setSelectedEvents} 
         />
      )}

      <TimelineZoomArea viewWindow={viewWindow} setViewWindow={setViewWindow} globalRange={globalRange}>
        <div style={{ flex: 1, minHeight: 0, overflowX: 'hidden', overflowY: 'auto', position: 'relative', paddingRight: '10px' }}>
          {!hasAnyData && (
            <motion.div 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }}
              style={{ color: '#666', textAlign: 'center', padding: '80px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}
            >
              <p>{emptyMessage || "Seçilen zaman diliminde gösterilecek etkinlik yok."}</p>
            </motion.div>
          )}
          {hasAnyData && (
             <motion.div
                initial="hidden"
                animate="visible"
                variants={{
                  hidden: { opacity: 0 },
                  visible: {
                    opacity: 1,
                    transition: { staggerChildren: 0.1 }
                  }
                }}
             >
               {children}
             </motion.div>
          )}
        </div>
      </TimelineZoomArea>
    </motion.div>
  );
};

export default LogPageLayout;
