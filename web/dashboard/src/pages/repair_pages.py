import os
import glob
import re

directory = r"C:\Users\kIrik\OneDrive - ABDULLAH GUL UNIVERSITESI\Masaüstü\kumiho\web\dashboard\src\pages"
files = glob.glob(os.path.join(directory, "*LogPage.jsx"))

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the component name
    basename = os.path.basename(filepath)
    component_name = basename.replace('.jsx', '')

    # Replace from </TimelineZoomArea> to the end of the file
    new_end = f"""      </TimelineZoomArea>
    </div>
  );
}};

export default {component_name};
"""
    content = re.sub(r"</TimelineZoomArea>[\s\S]*$", new_end, content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Repaired {basename}")

