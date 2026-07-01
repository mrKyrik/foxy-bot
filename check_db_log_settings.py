import sqlite3

try:
    conn = sqlite3.connect("Data/USER-DB.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(db_log_settings);")
    info = cursor.fetchall()
    print("Columns in db_log_settings:")
    for col in info:
        print(col)
except Exception as e:
    print(e)
