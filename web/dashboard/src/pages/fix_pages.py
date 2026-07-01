import os
import glob
import re

directory = r"C:\Users\kIrik\OneDrive - ABDULLAH GUL UNIVERSITESI\Masaüstü\kumiho\web\dashboard\src\pages"
files = glob.glob(os.path.join(directory, "*LogPage.jsx"))

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove handleSliderChange block
    content = re.sub(r"const\s+handleSliderChange\s*=\s*\(idx,\s*e\)\s*=>\s*\{[\s\S]*?^\s*\};\n", "", content, flags=re.MULTILINE)

    # 2. Remove the old baseMin, baseMax, zoomWindowMs, timeMin, timeMax block
    content = re.sub(r"let\s+baseMin,\s*baseMax;[\s\S]*?const\s+zoomWindowMs\s*=\s*timeMax\s*-\s*timeMin;\n", "", content)
    content = re.sub(r"const\s+timeMin\s*=\s*baseMin.*?\n\s*const\s+timeMax\s*=\s*baseMin.*?\n", "", content)

    # Ensure timeMin and timeMax are correctly defined
    if "const timeMin = viewWindow ? viewWindow[0] : 0;" not in content:
        content = content.replace("const getPercent =", "const timeMin = viewWindow ? viewWindow[0] : 0;\n  const timeMax = viewWindow ? viewWindow[1] : 0;\n\n  const getPercent =")

    # 3. Remove the bottom slider UI (the entire div after TimelineZoomArea)
    content = re.sub(r"^\s*<div\s+style=\{\{\s*marginTop:\s*'auto',\s*paddingTop:\s*'20px'\s*\}\}>[\s\S]*?(?=\s*</div\s*>\s*$)", "", content, flags=re.MULTILINE)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed {os.path.basename(filepath)}")

