import os
import glob
import re

directory = r"C:\Users\kIrik\OneDrive - ABDULLAH GUL UNIVERSITESI\Masaüstü\kumiho\web\dashboard\src\pages"
files = glob.glob(os.path.join(directory, "*LogPage.jsx"))

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove the date filter
    content = re.sub(r"^\s*if\s*\(logDate\s*!==\s*selectedDate\)\s*return;\s*$", "", content, flags=re.MULTILINE)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Cleaned {os.path.basename(filepath)}")

