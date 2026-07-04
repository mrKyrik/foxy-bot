export const parseTimestamp = (tsString) => {
  if (!tsString) return 0;
  let cleanStr = tsString.replace(' ', 'T');
  if (!cleanStr.endsWith('Z')) {
    cleanStr += 'Z';
  }
  const tsObj = new Date(cleanStr);
  return tsObj.getTime();
};

export const formatTime = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
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
