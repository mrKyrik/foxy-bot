import sqlite3

conn = sqlite3.connect('Data/USER-DB.db')
c = conn.cursor()

c.execute("DELETE FROM db_event_logs WHERE event_type LIKE 'ses_%'")

try:
    c.execute("ALTER TABLE db_event_logs ADD COLUMN channel_id TEXT")
except sqlite3.OperationalError:
    pass

c.execute("""
CREATE TABLE IF NOT EXISTS user_cache (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    avatar_url TEXT
)
""")

conn.commit()
conn.close()
print("DB Schema Updated Successfully.")
