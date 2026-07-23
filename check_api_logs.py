import os
import oracledb
from dotenv import load_dotenv

load_dotenv('.env')

try:
    conn = oracledb.connect(
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        dsn=os.getenv('DB_DSN'),
        config_dir=os.path.join(os.getcwd(), 'core', 'wallet'),
        wallet_location=os.path.join(os.getcwd(), 'core', 'wallet'),
        wallet_password=os.getenv('DB_PASSWORD')
    )
    cursor = conn.cursor()
    
    query = """
    SELECT
        e.log_id as id,
        'general' as source,
        e.event_type,
        e.user_id,
        e.details,
        TO_CHAR(e.timestamp, 'YYYY-MM-DD HH24:MI:SS') || 'Z' as timestamp,
        e.channel_id,
        u.username,
        u.avatar_url,
        c.channel_name,
        r.role_name
    FROM db_event_logs e
    LEFT JOIN user_cache u ON e.user_id = u.user_id
    LEFT JOIN channel_cache c ON e.channel_id = c.channel_id
    LEFT JOIN roles r ON e.channel_id = r.role_id AND e.guild_id = r.guild_id
    WHERE e.guild_id = :1
    ORDER BY e.timestamp DESC FETCH FIRST :2 ROWS ONLY
    """
    cursor.execute(query, ('1329583489816526848', 20))
    rows = cursor.fetchall()
    print("Rows:", rows)
except Exception as e:
    print("Error:", e)
