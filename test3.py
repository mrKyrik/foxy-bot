import sqlite3
import os

ADMIN_DB_PATH = os.path.abspath(os.path.join('Data', 'ADMIN-EVENTS.db'))
conn = sqlite3.connect(ADMIN_DB_PATH)
c = conn.cursor()
c.execute("SELECT * FROM admin_events")
rows = c.fetchall()
with open("admin_events_dump.txt", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(str(r) + "\n")
conn.close()
