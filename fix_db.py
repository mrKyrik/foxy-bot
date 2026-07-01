import sqlite3

conn = sqlite3.connect('Data/USER-DB.db')
c = conn.cursor()

try:
    c.execute("ALTER TABLE db_log_settings ADD COLUMN ses_camera_on INTEGER DEFAULT 1")
except:
    pass # Column might already exist

# Update all settings to 1 so the logs definitely work
c.execute("UPDATE db_log_settings SET ses_camera_on=1, ses_stream_on=1, ses_join_on=1, ses_switch_on=1")
conn.commit()
conn.close()
print("DB settings updated for cameras and streams.")
