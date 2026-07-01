import sqlite3
import json

try:
    conn = sqlite3.connect("Data/USER-DB.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT log_id, event_type, user_id, details FROM db_event_logs ORDER BY timestamp DESC LIMIT 5")
    rows = cursor.fetchall()
    print("----- db_event_logs -----")
    for row in rows:
        print(dict(row))
    
    cursor.execute("SELECT * FROM user_cache LIMIT 5")
    print("----- user_cache -----")
    for row in cursor.fetchall():
        print(dict(row))
        
except sqlite3.Error as e:
    print("SQLite Error:", e)
except Exception as e:
    print("Error:", e)
