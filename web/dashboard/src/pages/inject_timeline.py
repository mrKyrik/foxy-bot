import os
import glob
import re

directory = r"C:\Users\kIrik\OneDrive - ABDULLAH GUL UNIVERSITESI\Masaüstü\kumiho\web\dashboard\src\pages"
files = glob.glob(os.path.join(directory, "*LogPage.jsx"))

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip VoiceLogPage since it's already correct
    if "VoiceLogPage.jsx" in filepath:
        continue

    changed = False

    # 1. Inject import
    if "import TimelineZoomArea from '../components/TimelineZoomArea';" not in content:
        content = content.replace("import React", "import TimelineZoomArea from '../components/TimelineZoomArea';\nimport React")
        changed = True

    # 2. Inject opening tag
    if "<TimelineZoomArea" not in content:
        # Find <EventCheckboxFilter ... />
        pattern = r"(<EventCheckboxFilter[^>]+/>)"
        replacement = r"\1\n\n      <TimelineZoomArea viewWindow={viewWindow} setViewWindow={setViewWindow} globalRange={globalRange}>"
        content = re.sub(pattern, replacement, content)
        changed = True

    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Injected TimelineZoomArea into {os.path.basename(filepath)}")
