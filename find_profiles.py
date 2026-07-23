import sqlite3
import glob

for db_file in glob.glob("*.db"):
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM global_profiles")
        count = c.fetchone()[0]
        print(f"{db_file}: {count}")
    except Exception as e:
        pass
