import subprocess

command = [
    'ssh', '-i', r'C:\Users\kIrik\Downloads\ssh-key-2026-07-16 (3).key',
    '-o', 'StrictHostKeyChecking=no', 'ubuntu@144.24.243.224',
    "sqlite3 /home/ubuntu/prc/foxy/kumiho.db \"UPDATE db_log_settings SET app_create_on = 1 WHERE guild_id = '1507723513182818544';\""
]

result = subprocess.run(command, capture_output=True, text=True)
print("OUT:", result.stdout)
print("ERR:", result.stderr)
