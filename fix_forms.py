import subprocess

script = """
import sys

file_path = '/home/ubuntu/prc/foxy/Commands/forms.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('setting_key="app_create_on",', 'setting_key=None,')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Replaced setting_key in forms.py")
"""

command = [
    'ssh', '-i', r'C:\Users\kIrik\Downloads\ssh-key-2026-07-16 (3).key',
    '-o', 'StrictHostKeyChecking=no', 'ubuntu@144.24.243.224',
    f"python3 -c \"{script}\""
]

result = subprocess.run(command, capture_output=True, text=True)
print("OUT:", result.stdout)
print("ERR:", result.stderr)
