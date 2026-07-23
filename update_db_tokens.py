import sqlite3

conn = sqlite3.connect('kumiho.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS upload_tokens (
    token       TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    expires_at  INTEGER NOT NULL
)
''')
conn.commit()
conn.close()
print('Table upload_tokens created.')
