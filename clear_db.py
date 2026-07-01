import sqlite3

try:
    conn_user = sqlite3.connect('Data/USER-DB.db')
    c_user = conn_user.cursor()
    c_user.execute("DELETE FROM db_event_logs")
    conn_user.commit()
    conn_user.close()
    print("USER-DB.db -> db_event_logs cleared.")
except Exception as e:
    print(f"Error clearing USER-DB.db: {e}")

try:
    conn_admin = sqlite3.connect('Data/ADMIN-EVENTS.db')
    c_admin = conn_admin.cursor()
    c_admin.execute("DELETE FROM admin_events")
    conn_admin.commit()
    conn_admin.close()
    print("ADMIN-EVENTS.db -> admin_events cleared.")
except Exception as e:
    print(f"Error clearing ADMIN-EVENTS.db: {e}")
