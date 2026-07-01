import sqlite3

try:
    conn = sqlite3.connect("Data/USER-DB.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in USER-DB.db:")
    for t in tables:
        print("-", t[0])
except Exception as e:
    print(e)
