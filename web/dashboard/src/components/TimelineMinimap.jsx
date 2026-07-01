import React, { useState, useRef, useEffect } from 'react';

const TimelineMinimap = ({ globalRange, viewWindow, setViewWindow }) => {
  const containerRef = useRef(null);
  const [isDraggingPan, setIsDraggingPan] = useState(false);
  const [isDraggingLeft, setIsDraggingLeft] = useState(false);
  const [isDraggingRight, setIsDraggingRight] = useState(false);
  const [startX, setStartX] = useState(0);
  const [initialView, setInitialView] = useState([0, 0]);

  if (!globalRange || !viewWindow) return null;

  const [gMin, gMax] = globalRange;
  const [vMin, vMax] = viewWindow;
  const globalDuration = gMax - gMin;

  // Güvenlik: Eğer süre 0 ise (tek log vs) hesaplama patlamasın
  const safeDuration = globalDuration > 0 ? globalDuration : 86400000;

  const leftPercent = Math.max(0, ((vMin - gMin) / safeDuration) * 100);
  const rightPercent = Math.min(100, ((vMax - gMin) / safeDuration) * 100);
  const widthPercent = rightPercent - leftPercent;

  const handlePointerDownPan = (e) => {
    setIsDraggingPan(true);
    setStartX(e.clientX);
    setInitialView([vMin, vMax]);
    e.target.setPointerCapture(e.pointerId);
  };

  const handlePointerDownLeft = (e) => {
    e.stopPropagation();
    setIsDraggingLeft(true);
    setStartX(e.clientX);
    setInitialView([vMin, vMax]);
    e.target.setPointerCapture(e.pointerId);
  };

  const handlePointerDownRight = (e) => {
    e.stopPropagation();
    setIsDraggingRight(true);
    setStartX(e.clientX);
    setInitialView([vMin, vMax]);
    e.target.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e) => {
    if (!isDraggingPan && !isDraggingLeft && !isDraggingRight) return;
    if (!containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const deltaX = e.clientX - startX;
    const deltaPercent = (deltaX / rect.width);
    const deltaTime = deltaPercent * safeDuration;

    if (isDraggingPan) {
      let newStart = initialView[0] + deltaTime;
      let newEnd = initialView[1] + deltaTime;
      
      // Sınırları koru
      if (newStart < gMin) {
        newStart = gMin;
        newEnd = gMin + (initialView[1] - initialView[0]);
      }
      if (newEnd > gMax) {
        newEnd = gMax;
        newStart = gMax - (initialView[1] - initialView[0]);
      }
      setViewWindow([newStart, newEnd]);
    } 
    else if (isDraggingLeft) {
      let newStart = initialView[0] + deltaTime;
      if (newStart < gMin) newStart = gMin;
      if (newStart > vMax - 1000) newStart = vMax - 1000; // minimum 1 saniye pencere
      setViewWindow([newStart, vMax]);
    }
    else if (isDraggingRight) {
      let newEnd = initialView[1] + deltaTime;
      if (newEnd > gMax) newEnd = gMax;
      if (newEnd < vMin + 1000) newEnd = vMin + 1000;
      setViewWindow([vMin, newEnd]);
    }
  };

  const handlePointerUp = (e) => {
    setIsDraggingPan(false);
    setIsDraggingLeft(false);
    setIsDraggingRight(false);
    e.target.releasePointerCapture(e.pointerId);
  };

  // Tarihleri okunaklı formata çevirme
  const formatTime = (ts) => {
    const d = new Date(ts);
    return `${d.getDate().toString().padStart(2, '0')}/${(d.getMonth()+1).toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
  };

  return (
    <div style={{ padding: '16px 20px', background: 'rgba(0,0,0,0.3)', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
        <span>{formatTime(gMin)}</span>
        <span>Maksimum Aralık</span>
        <span>{formatTime(gMax)}</span>
      </div>

      <div 
        ref={containerRef}
        style={{
          position: 'relative',
          height: '40px',
          background: '#1a1a1a',
          borderRadius: '8px',
          boxShadow: 'inset 0 0 10px rgba(0,0,0,0.5)',
          overflow: 'hidden'
        }}
      >
        {/* Timeline Arka Plan Çizgileri (Süsleme) */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, opacity: 0.1, backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 10px, #fff 10px, #fff 11px)' }}></div>

        {/* Aktif Pencere (Viewport Kutusunun Kendisi) */}
        <div 
          onPointerDown={handlePointerDownPan}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          style={{
            position: 'absolute',
            left: `${leftPercent}%`,
            width: `${widthPercent}%`,
            height: '100%',
            background: 'rgba(6, 182, 212, 0.25)',
            borderTop: '2px solid var(--accent-blue)',
            borderBottom: '2px solid var(--accent-blue)',
            cursor: isDraggingPan ? 'grabbing' : 'grab',
            boxShadow: '0 0 15px rgba(6, 182, 212, 0.1)',
            transition: (isDraggingPan || isDraggingLeft || isDraggingRight) ? 'none' : 'all 0.1s ease-out'
          }}
        >
          {/* Sol Handle */}
          <div 
            onPointerDown={handlePointerDownLeft}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              bottom: 0,
              width: '12px',
              background: 'var(--accent-blue)',
              cursor: 'ew-resize',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '2px'
            }}
          >
            <div style={{ width: '2px', height: '12px', background: 'rgba(255,255,255,0.5)' }}></div>
          </div>

          {/* Orta Etiket */}
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#fff', fontSize: '0.75rem', fontWeight: 'bold', pointerEvents: 'none', textShadow: '0 1px 3px rgba(0,0,0,0.8)', whiteSpace: 'nowrap' }}>
            {formatTime(vMin)} - {formatTime(vMax)}
          </div>

          {/* Sağ Handle */}
          <div 
            onPointerDown={handlePointerDownRight}
            style={{
              position: 'absolute',
              right: 0,
              top: 0,
              bottom: 0,
              width: '12px',
              background: 'var(--accent-blue)',
              cursor: 'ew-resize',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '2px'
            }}
          >
            <div style={{ width: '2px', height: '12px', background: 'rgba(255,255,255,0.5)' }}></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimelineMinimap;
