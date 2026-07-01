export const parseTimestamp = (tsString) => {
  if (!tsString) return 0;
  const tsObj = new Date(tsString.replace(' ', 'T') + 'Z');
  return tsObj.getTime();
};

export const formatTime = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

export const getPercent = (ts, timeMin, timeMax) => {
  if (ts < timeMin) return -10; 
  if (ts > timeMax) return 110; 
  const zoomWindowMs = timeMax - timeMin;
  if (zoomWindowMs === 0) return 0;
  return ((ts - timeMin) / zoomWindowMs) * 100;
};
