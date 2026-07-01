import os
import glob
import re

directory = r"C:\Users\kIrik\OneDrive - ABDULLAH GUL UNIVERSITESI\Masaüstü\kumiho\web\dashboard\src\pages"
files = glob.glob(os.path.join(directory, "*LogPage.jsx"))

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    basename = os.path.basename(filepath)
    component_name = basename.replace('.jsx', '')

    new_end = f"""      </TimelineZoomArea>
    </div>
  );
}};

export default {component_name};
"""
    
    # Let's search for '<div className="custom-slider"' and remove everything from its PRECEDING '</div>' to the EOF.
    # Actually, we can just find `<div className="custom-slider"` and replace everything from 2 lines above it to EOF.
    # Or just use regex to match the exact pattern we see.
    pattern = r"\s*</div>\s*<div className=\"custom-slider\"[\s\S]*$"
    
    if re.search(pattern, content):
        content = re.sub(pattern, "\n" + new_end, content)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {basename}")
    else:
        print(f"Pattern not found in {basename}")
