import os
import glob
import re

directory = r"C:\Users\kIrik\OneDrive - ABDULLAH GUL UNIVERSITESI\Masaüstü\kumiho\web\dashboard\src\pages"
files = glob.glob(os.path.join(directory, "*LogPage.jsx"))

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove useState for zoomRange
    content = re.sub(r"const\s+\[zoomRange,\s*setZoomRange\]\s*=\s*useState\(\[0,\s*100\]\);\s*\n?", "", content)

    # 2. Update props
    content = re.sub(r"\(\{\s*logs,\s*selectedDate,\s*selectedTags\s*\}\)", "({ logs, viewWindow, setViewWindow, globalRange, selectedTags })", content)

    # 3. Update timeMin and timeMax
    old_time_block = r"const\s+selectedDayStart\s*=\s*new\s+Date\(selectedDate\);\s*\n\s*selectedDayStart\.setHours\(0,0,0,0\);\s*\n\s*const\s+timeMin\s*=\s*selectedDayStart\.getTime\(\);\s*\n\s*const\s+timeMax\s*=\s*timeMin\s*\+\s*24\s*\*\s*60\s*\*\s*60\s*\*\s*1000;"
    new_time_block = "const timeMin = viewWindow ? viewWindow[0] : 0;\n  const timeMax = viewWindow ? viewWindow[1] : 0;"
    content = re.sub(old_time_block, new_time_block, content)

    # 4. Update getPercent
    old_percent_block = r"const\s+getPercent\s*=\s*\(ts\)\s*=>\s*\{\s*\n\s*const\s+rawPct\s*=\s*\(\(ts\s*-\s*timeMin\)\s*/\s*\(timeMax\s*-\s*timeMin\)\)\s*\*\s*100;\s*\n\s*return\s*\(\(rawPct\s*-\s*zoomRange\[0\]\)\s*/\s*\(zoomRange\[1\]\s*-\s*zoomRange\[0\]\)\)\s*\*\s*100;\s*\n\s*\};"
    new_percent_block = """const getPercent = (ts) => {
    if (!viewWindow) return 0;
    const windowDuration = viewWindow[1] - viewWindow[0];
    if (windowDuration === 0) return 0;
    return ((ts - viewWindow[0]) / windowDuration) * 100;
  };"""
    content = re.sub(old_percent_block, new_percent_block, content)

    # 5. Update TimelineZoomArea props
    content = re.sub(r"<TimelineZoomArea\s+zoomRange=\{zoomRange\}\s+setZoomRange=\{setZoomRange\}>", "<TimelineZoomArea viewWindow={viewWindow} setViewWindow={setViewWindow} globalRange={globalRange}>", content)

    # 6. Replace zoomRange with viewWindow in dependency arrays
    content = content.replace(", zoomRange,", ", viewWindow,")
    content = content.replace("[parsed, zoomRange]", "[parsed, viewWindow]")
    content = content.replace("[logs, zoomRange", "[logs, viewWindow")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated {os.path.basename(filepath)}")

