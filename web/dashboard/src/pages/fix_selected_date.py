import os
import glob

directory = r"C:\Users\kIrik\OneDrive - ABDULLAH GUL UNIVERSITESI\Masaüstü\kumiho\web\dashboard\src\pages"
files = glob.glob(os.path.join(directory, "*LogPage.jsx"))

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    changed = False

    if ", selectedDate" in content:
        content = content.replace(", selectedDate", "")
        changed = True

    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Removed selectedDate from {os.path.basename(filepath)}")
