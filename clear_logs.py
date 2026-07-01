import sqlite3
import os

USER_DB = "Data/USER-DB.db"
ADMIN_DB = "Data/ADMIN-EVENTS.db"

def clear_logs():
    if os.path.exists(USER_DB):
        conn = sqlite3.connect(USER_DB)
        c = conn.cursor()
        c.execute("DELETE FROM db_event_logs")
        deleted = c.rowcount
        conn.commit()
        conn.close()
        print(f"db_event_logs tablosundan {deleted} log silindi.")
        
    if os.path.exists(ADMIN_DB):
        conn = sqlite3.connect(ADMIN_DB)
        c = conn.cursor()
        c.execute("DELETE FROM admin_events")
        deleted = c.rowcount
        conn.commit()
        conn.close()
        print(f"admin_events tablosundan {deleted} log silindi.")

if __name__ == "__main__":
    clear_logs()
