import os
import oracledb
from dotenv import load_dotenv

load_dotenv() # Load from default .env

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
    
    guild_id = '1329583489816526848' # test guild
    limit = 5
    
    print("Testing db_event_logs...")
    query1 = f"""
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
        ORDER BY e.timestamp DESC FETCH FIRST {limit} ROWS ONLY
    """
    cursor.execute(query1, (guild_id,))
    print(f"db_event_logs: {len(cursor.fetchall())} rows")
    
    print("Testing admin_events...")
    query2 = f"""
        SELECT
            e.event_id as id,
            'admin' as source,
            e.action_type as event_type,
            e.admin_id as user_id,
            e.admin_id as admin_id,
            e.reason as details,
            TO_CHAR(e.timestamp, 'YYYY-MM-DD HH24:MI:SS') || 'Z' as timestamp,
            e.target_id as channel_id,
            u.username,
            u.avatar_url,
            COALESCE(t_u.username, t_c.channel_name, t_r.role_name, e.target_id) as target_name,
            NULL as channel_name,
            NULL as role_name
        FROM admin_events e
        LEFT JOIN user_cache u ON e.admin_id = u.user_id
        LEFT JOIN user_cache t_u ON e.target_id = t_u.user_id
        LEFT JOIN channel_cache t_c ON e.target_id = t_c.channel_id
        LEFT JOIN roles t_r ON e.target_id = t_r.role_id
        WHERE e.guild_id = :1
        ORDER BY e.timestamp DESC FETCH FIRST {limit} ROWS ONLY
    """
    cursor.execute(query2, (guild_id,))
    print(f"admin_events: {len(cursor.fetchall())} rows")
    
except Exception as e:
    print("Error:", e)
