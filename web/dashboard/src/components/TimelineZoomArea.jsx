import React, { useRef, useState } from 'react';

const TimelineZoomArea = ({ children, viewWindow, setViewWindow, globalRange }) => {
  const containerRef = useRef(null);
  const [dragStart, setDragStart] = useState(null);
  const [dragCurrent, setDragCurrent] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleContextMenu = (e) => {
    e.preventDefault(); 
  };

  const handleMouseDown = (e) => {
    if (e.button !== 2) return; // Only trigger on right click
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    setDragStart(x);
    setDragCurrent(x);
    setIsDragging(true);
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    const rect = containerRef.current.getBoundingClientRect();
    let x = e.clientX - rect.left;
    x = Math.max(0, Math.min(x, rect.width));
    setDragCurrent(x);
  };

  const handleMouseUp = (e) => {
    if (!isDragging) return;
    setIsDragging(false);
    
    // Ignore accidental clicks
    if (Math.abs(dragStart - dragCurrent) < 10) return; 

    const rect = containerRef.current.getBoundingClientRect();
    const minX = Math.min(dragStart, dragCurrent);
    const maxX = Math.max(dragStart, dragCurrent);

    const pctStart = minX / rect.width;
    const pctEnd = maxX / rect.width;

    const currentSpan = viewWindow[1] - viewWindow[0];
    const newZ0 = viewWindow[0] + (pctStart * currentSpan);
    const newZ1 = viewWindow[0] + (pctEnd * currentSpan);

    setViewWindow([newZ0, newZ1]);
  };

  const handleDoubleClick = (e) => {
      if (globalRange) {
          setViewWindow(globalRange);
      }
  };

  return (
    <div 
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onContextMenu={handleContextMenu}
      onDoubleClick={handleDoubleClick}
      style={{ 
          position: 'relative', 
          width: '100%', 
          height: '100%', 
          cursor: isDragging ? 'col-resize' : 'crosshair',
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          minHeight: 0
      }}
    >
      {children}
      {isDragging && (
        <div style={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          left: Math.min(dragStart, dragCurrent),
          width: Math.abs(dragStart - dragCurrent),
          backgroundColor: 'rgba(6, 182, 212, 0.2)',
          borderLeft: '1px solid #06b6d4',
          borderRight: '1px solid #06b6d4',
          pointerEvents: 'none',
          zIndex: 9999
        }} />
      )}
    </div>
  );
};

export default TimelineZoomArea;
