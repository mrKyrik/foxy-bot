import sqlite3
import glob
import os

for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".db") or file.endswith(".sqlite"):
            db_file = os.path.join(root, file)
            try:
                conn = sqlite3.connect(db_file)
                c = conn.cursor()
                c.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in c.fetchall()]
                if "global_profiles" in tables:
                    c.execute("SELECT COUNT(*) FROM global_profiles")
                    count = c.fetchone()[0]
                    print(f"{db_file}: {count}")
            except Exception as e:
                pass
