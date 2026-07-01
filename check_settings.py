import sqlite3

try:
    conn = sqlite3.connect("Data/USER-DB.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM log_settings WHERE guild_id='1424129369541972102';")
    row = cursor.fetchone()
    if row:
        print("log_settings:", dict(row))
    else:
        print("No log_settings found!")
        
    cursor.execute("SELECT * FROM db_log_settings WHERE guild_id='1424129369541972102';")
    row = cursor.fetchone()
    if row:
        print("db_log_settings:", dict(row))
    else:
        print("No db_log_settings found!")
except Exception as e:
    print(e)
