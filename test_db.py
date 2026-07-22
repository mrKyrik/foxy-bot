import sqlite3

def check_db():
    conn = sqlite3.connect('temp_backup/foxy-bot/kumiho.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for (table_name,) in tables:
            try:
                cursor.execute(f"SELECT count(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"{table_name}: OK ({count} rows)")
            except Exception as e:
                print(f"{table_name}: FAILED - {e}")
    except Exception as e:
        print(f"Failed to read sqlite_master: {e}")

check_db()
