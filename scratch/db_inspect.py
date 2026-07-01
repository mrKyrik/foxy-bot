import sqlite3

for db_path in ["Data/USER-DB.db", "Data/ADMIN-EVENTS.db"]:
    print(f"=== {db_path} ===")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    for t in cursor.fetchall():
        table_name = t[0]
        print(f"Table: {table_name}")
        cursor.execute(f"PRAGMA table_info({table_name});")
        for col in cursor.fetchall():
            print(f"  {col[1]} ({col[2]})")
    conn.close()
