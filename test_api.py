import sqlite3
import os

user_db = os.path.abspath('Data/USER-DB.db')
conn = sqlite3.connect(user_db)
c = conn.cursor()
c.execute("PRAGMA table_info(user_cache)")
print(c.fetchall())
conn.close()
