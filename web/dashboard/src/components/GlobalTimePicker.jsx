import React, { useState, useRef, useEffect } from 'react';
import { Calendar, Clock, Filter } from 'lucide-react';

const PRESETS = [
  { label: 'Son 1 Saat', hours: 1 },
  { label: 'Son 24 Saat', hours: 24 },
  { label: 'Son 7 Gün', hours: 24 * 7 },
  { label: 'Son 30 Gün', hours: 24 * 30 },
];

const GlobalTimePicker = ({ fetchRange, setFetchRange }) => {
  const [mode, setMode] = useState('preset'); // 'preset' or 'custom'
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  
  // Custom date states
  const [customStart, setCustomStart] = useState(() => {
    const d = new Date();
    d.setHours(d.getHours() - 24);
    // Convert to YYYY-MM-DDTHH:MM for datetime-local input
    return d.toISOString().slice(0, 16);
  });
  
  const [customEnd, setCustomEnd] = useState(() => {
    return new Date().toISOString().slice(0, 16);
  });

  const applyPreset = (hours) => {
    const end = Date.now();
    const start = end - (hours * 60 * 60 * 1000);
    setFetchRange({ start, end, isLive: true, hours });
    setMode('preset');
    setIsOpen(false);
  };

  const applyCustom = () => {
    if (!customStart || !customEnd) return;
    const start = new Date(customStart).getTime();
    const end = new Date(customEnd).getTime();
    if (start >= end) {
      alert("Bitiş zamanı başlangıçtan büyük olmalıdır.");
      return;
    }
    setFetchRange({ start, end, isLive: false });
    setMode('custom');
    setIsOpen(false);
  };

  // Dışarı tıklayınca dropdown'ı kapat
  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  return (
    <div ref={containerRef} style={{ position: 'relative', zIndex: 50 }}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        style={{ 
          display: 'flex', alignItems: 'center', gap: '8px', 
          padding: '8px 16px', borderRadius: '6px', 
          background: 'var(--bg-card)', border: '1px solid var(--border-color)', 
          color: 'var(--text-primary)', fontSize: '0.95rem',
          cursor: 'pointer'
        }}
      >
        <Clock size={18} />
        {mode === 'preset' ? 'Zaman Aralığı' : 'Özel Tarih'}
      </button>

      {isOpen && (
        <div style={{ 
          position: 'absolute', top: '100%', right: 0, marginTop: '8px',
          background: '#1a1b1e', border: '1px solid var(--border-color)',
          borderRadius: '8px', width: '320px', padding: '16px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.8)',
          display: 'flex', flexDirection: 'column', gap: '16px',
          backdropFilter: 'blur(10px)'
        }}>
          
          <div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px', textTransform: 'uppercase' }}>Hızlı Seçim</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {PRESETS.map(p => (
                <button 
                  key={p.hours}
                  onClick={() => applyPreset(p.hours)}
                  style={{
                    padding: '6px 12px', background: 'var(--bg-card)', 
                    border: '1px solid var(--border-color)', borderRadius: '4px',
                    color: 'var(--text-primary)', cursor: 'pointer', fontSize: '0.9rem',
                    flex: '1 1 calc(50% - 8px)'
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px', textTransform: 'uppercase' }}>Özel Aralık</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px' }}>Başlangıç</label>
                <input 
                  type="datetime-local" 
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                  style={{ width: '100%', padding: '8px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '4px', color: '#fff', boxSizing: 'border-box' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px' }}>Bitiş</label>
                <input 
                  type="datetime-local" 
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                  style={{ width: '100%', padding: '8px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '4px', color: '#fff', boxSizing: 'border-box' }}
                />
              </div>
              <button 
                onClick={applyCustom}
                style={{
                  width: '100%', padding: '8px', background: 'var(--accent-blue)', 
                  border: 'none', borderRadius: '4px', color: '#fff', 
                  fontWeight: 'bold', cursor: 'pointer', marginTop: '8px'
                }}
              >
                Uygula
              </button>
            </div>
          </div>

        </div>
      )}
    </div>
  );
};

export default GlobalTimePicker;
