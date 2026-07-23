import os
import oracledb
from dotenv import load_dotenv

load_dotenv('.env')

conn = oracledb.connect(
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    dsn=os.getenv('DB_DSN'),
    config_dir=os.path.join(os.getcwd(), 'core', 'wallet'),
    wallet_location=os.path.join(os.getcwd(), 'core', 'wallet'),
    wallet_password=os.getenv('DB_PASSWORD')
)
cursor = conn.cursor()

print("--- Testing DB_EVENT_LOGS ---")
try:
    cursor.execute("SELECT * FROM db_event_logs FETCH FIRST 1 ROWS ONLY")
    print(cursor.description)
    print(cursor.fetchall())
except Exception as e:
    print(e)

print("--- Testing ADMIN_EVENTS ---")
try:
    cursor.execute("SELECT * FROM admin_events FETCH FIRST 1 ROWS ONLY")
    print(cursor.description)
    print(cursor.fetchall())
except Exception as e:
    print(e)

conn.close()
