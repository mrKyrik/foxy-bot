import subprocess

command = [
    'ssh', '-i', r'C:\Users\kIrik\Downloads\ssh-key-2026-07-16 (3).key',
    '-o', 'StrictHostKeyChecking=no', 'ubuntu@144.24.243.224',
    "sqlite3 /home/ubuntu/prc/foxy/kumiho.db \"SELECT guild_id, form_id FROM custom_forms LIMIT 5;\""
]

result = subprocess.run(command, capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
