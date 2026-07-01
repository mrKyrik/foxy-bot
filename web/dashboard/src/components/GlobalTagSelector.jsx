import React, { useState, useRef, useEffect } from 'react';
import { X, Search, Hash, Tag, User, FolderTree } from 'lucide-react';

const GlobalTagSelector = ({ availableTags, selectedTags, setSelectedTags }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  const typeOrder = { 'user': 1, 'role': 2, 'category': 3, 'channel': 4 };

  const filteredTags = availableTags.filter(t => 
    !selectedTags.find(st => st.id === t.id && st.type === t.type) &&
    ((t.name && t.name.toLowerCase().includes(searchTerm.toLowerCase())) || 
     (t.id && t.id.includes(searchTerm)))
  ).sort((a, b) => typeOrder[a.type] - typeOrder[b.type] || (a.name || '').localeCompare(b.name || '')).slice(0, 15);

  const handleSelect = (tag) => {
    setSelectedTags(prev => [...prev, tag]);
    setSearchTerm('');
    setIsOpen(false);
  };

  const handleRemove = (tagToRemove) => {
    setSelectedTags(prev => prev.filter(t => !(t.id === tagToRemove.id && t.type === tagToRemove.type)));
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const getTagColor = (type) => {
    if (type === 'user') return { bg: 'rgba(16, 185, 129, 0.2)', border: 'rgba(16, 185, 129, 0.5)', text: '#10b981' };
    if (type === 'role') return { bg: 'rgba(244, 63, 94, 0.2)', border: 'rgba(244, 63, 94, 0.5)', text: '#f43f5e' };
    if (type === 'category') return { bg: 'rgba(168, 85, 247, 0.2)', border: 'rgba(168, 85, 247, 0.5)', text: '#a855f7' };
    if (type === 'channel') return { bg: 'rgba(59, 130, 246, 0.2)', border: 'rgba(59, 130, 246, 0.5)', text: '#3b82f6' };
    return { bg: 'rgba(255, 255, 255, 0.2)', border: 'rgba(255, 255, 255, 0.5)', text: '#fff' };
  };

  const getIcon = (type, url) => {
    if (type === 'user') return url ? <img src={url} style={{ width: '16px', height: '16px', borderRadius: '50%' }} alt="" /> : <User size={14} />;
    if (type === 'role') return <Tag size={14} />;
    if (type === 'category') return <FolderTree size={14} />;
    if (type === 'channel') return <Hash size={14} />;
    return null;
  };

  return (
    <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }} ref={containerRef}>
      
      {/* Seçili Kapsüller */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {selectedTags.map((t, idx) => {
          const colors = getTagColor(t.type);
          return (
            <div key={idx} style={{ 
              display: 'flex', alignItems: 'center', gap: '6px', 
              background: colors.bg, border: `1px solid ${colors.border}`, 
              padding: '4px 8px', borderRadius: '16px', fontSize: '0.85rem', color: '#fff' 
            }}>
              {getIcon(t.type, t.avatar_url)}
              <span>{t.name || t.id}</span>
              <X size={14} style={{ cursor: 'pointer', color: '#ff4d4f', marginLeft: '4px' }} onClick={() => handleRemove(t)} />
            </div>
          )
        })}
      </div>

      <div style={{ position: 'relative' }}>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Search size={16} color="#888" style={{ position: 'absolute', left: '10px' }} />
          <input 
            type="text" 
            placeholder="Kullanıcı, Kanal veya Rol Ara..." 
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); setIsOpen(true); }}
            onFocus={() => setIsOpen(true)}
            style={{ 
              width: '100%', padding: '10px 10px 10px 32px', borderRadius: '8px', 
              background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', 
              color: 'white', outline: 'none', transition: 'border 0.2s'
            }} 
          />
        </div>

        {isOpen && searchTerm && filteredTags.length > 0 && (
          <div style={{ 
            position: 'absolute', bottom: '100%', left: 0, width: '100%', marginBottom: '4px',
            background: '#1f2937', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', 
            maxHeight: '200px', overflowY: 'auto', zIndex: 100, boxShadow: '0 -4px 10px rgba(0,0,0,0.5)'
          }}>
            {filteredTags.map((t, idx) => {
              const colors = getTagColor(t.type);
              return (
                <div 
                  key={idx}
                  onClick={() => handleSelect(t)}
                  style={{ 
                    display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', 
                    cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.05)'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
                  onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <div style={{ color: colors.text, display: 'flex', alignItems: 'center' }}>
                    {getIcon(t.type, t.avatar_url)}
                  </div>
                  <span style={{ fontSize: '0.9rem', color: '#e5e7eb' }}>
                    {t.name || t.id}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: '#888', marginLeft: 'auto', textTransform: 'uppercase' }}>
                    {t.type}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default GlobalTagSelector;
