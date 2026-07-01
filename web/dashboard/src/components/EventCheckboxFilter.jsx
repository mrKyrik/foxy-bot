import React from 'react';
import { motion } from 'framer-motion';

const EventCheckboxFilter = ({ options, selectedEvents, setSelectedEvents }) => {
  const toggleOption = (optValue) => {
    if (selectedEvents.includes(optValue)) {
      setSelectedEvents(selectedEvents.filter(e => e !== optValue));
    } else {
      setSelectedEvents([...selectedEvents, optValue]);
    }
  };

  return (
    <div style={{ 
        display: 'flex', 
        flexWrap: 'wrap', 
        gap: '12px', 
        marginBottom: '16px', 
        background: 'rgba(0,0,0,0.2)', 
        padding: '12px', 
        borderRadius: '12px',
        border: '1px solid rgba(255,255,255,0.05)'
    }}>
      {options.map(opt => {
        const isSelected = selectedEvents.includes(opt.value);
        return (
          <motion.div
            key={opt.value}
            onClick={() => toggleOption(opt.value)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px', 
              cursor: 'pointer', 
              fontSize: '0.9rem', 
              fontWeight: 500,
              color: isSelected ? '#fff' : '#94a3b8',
              background: isSelected ? (opt.color ? `${opt.color}33` : 'rgba(255,255,255,0.1)') : 'rgba(255,255,255,0.02)',
              border: `1px solid ${isSelected ? (opt.color || 'var(--accent-blue)') : 'rgba(255,255,255,0.05)'}`,
              padding: '6px 14px',
              borderRadius: '20px',
              boxShadow: isSelected ? `0 0 10px ${opt.color ? opt.color + '40' : 'rgba(255,255,255,0.1)'}` : 'none',
              transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)'
            }}
          >
             {opt.color && (
                 <div style={{
                     width:'10px', 
                     height:'10px', 
                     borderRadius:'50%', 
                     background: isSelected ? opt.color : 'rgba(255,255,255,0.2)', 
                     transition: 'background 0.2s ease',
                     boxShadow: isSelected ? `0 0 8px ${opt.color}` : 'none'
                 }}></div>
             )}
             {opt.label}
          </motion.div>
        );
      })}
    </div>
  );
};

export default EventCheckboxFilter;
