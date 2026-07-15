import os
import re

with open('web/api/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update DB paths and remove USER_DB_PATH, ADMIN_DB_PATH
content = re.sub(r'USER_DB_PATH = .*?\n', '', content)
content = re.sub(r'ADMIN_DB_PATH = .*?\n', '', content)
content = content.replace('USER_DB_PATH', 'MAIN_DB_PATH')
content = content.replace('ADMIN_DB_PATH', 'MAIN_DB_PATH')
content = content.replace('DB_PATH', 'MAIN_DB_PATH') # Just in case

# 2. Update get_db_connection
new_get_db = '''def get_db_connection(db_path=MAIN_DB_PATH):
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn'''

content = re.sub(r'def get_db_connection\(db_path\):.*?(?=\ndef init_db)', new_get_db + '\n\n', content, flags=re.DOTALL)

# 3. Fix get_guild_logs
# Currently, it does ATTACH DATABASE 'MAIN_DB_PATH' AS userdb and 'MAIN_DB_PATH' AS admindb.
# We don't need ATTACH anymore since everything is in MAIN_DB_PATH.
# Let's replace the logic in get_guild_logs.
# We can just remove the ATTACH DATABASE commands and replace `userdb.` and `admindb.` with nothing.
content = re.sub(r'c\.execute\(f"ATTACH DATABASE \'{MAIN_DB_PATH}\' AS userdb"\)\n\s*', '', content)
content = re.sub(r'c\.execute\(f"ATTACH DATABASE \'{MAIN_DB_PATH}\' AS admindb"\)\n\s*', '', content)
content = content.replace('userdb.', '')
content = content.replace('admindb.', '')

with open('web/api/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated web/api/main.py successfully')
