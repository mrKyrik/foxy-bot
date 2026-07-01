import sqlite3
import json
conn = sqlite3.connect('Data/USER-DB.db')
c = conn.cursor()
c.execute("SELECT * FROM db_event_logs WHERE event_type LIKE '%role%' LIMIT 10")
rows = c.fetchall()
for r in rows:
    print(r)
