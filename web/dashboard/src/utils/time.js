export const parseTimestamp = (tsString) => {
  if (!tsString || tsString === 'Z' || tsString === 'null') return 0;
  if (typeof tsString === 'number') return tsString;
  let cleanStr = String(tsString).trim().replace(' ', 'T');
  if (!cleanStr.endsWith('Z')) {
    cleanStr += 'Z';
  }
  const tsObj = new Date(cleanStr);
  const time = tsObj.getTime();
  return isNaN(time) ? 0 : time;
};

export const formatTime = (ts) => {
  if (!ts) return "";
  const tsNum = typeof ts === 'string' ? parseTimestamp(ts) : ts;
  if (!tsNum || isNaN(tsNum)) return "";
  const d = new Date(tsNum);
  return d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

export const getPercent = (ts, timeMin, timeMax) => {
  const tsNum = typeof ts === 'string' ? parseTimestamp(ts) : ts;
  if (tsNum < timeMin) return -10; 
  if (tsNum > timeMax) return 110; 
  const zoomWindowMs = timeMax - timeMin;
  if (zoomWindowMs === 0) return 0;
  return ((tsNum - timeMin) / zoomWindowMs) * 100;
};
