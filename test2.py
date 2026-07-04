import sqlite3
import os

USER_DB_PATH = os.path.abspath(os.path.join('Data', 'USER-DB.db'))
ADMIN_DB_PATH = os.path.abspath(os.path.join('Data', 'ADMIN-EVENTS.db'))

admin_conn = sqlite3.connect(ADMIN_DB_PATH)
cursor = admin_conn.cursor()
cursor.execute(f"ATTACH DATABASE '{USER_DB_PATH}' AS userdb")
query = """
    SELECT
        e.event_id as id,
        'admin' as source,
        e.action_type as event_type,
        e.admin_id as user_id,
        e.admin_id as admin_id,
        e.reason as details,
        e.timestamp,
        e.target_id as channel_id,
        u.username,
        u.avatar_url,
        COALESCE(t_u.username, t_c.channel_name, t_r.role_name, e.target_id) as target_name,
        NULL as channel_name,
        NULL as role_name
    FROM admin_events e
    LEFT JOIN userdb.user_cache u ON e.admin_id = u.user_id
    LEFT JOIN userdb.user_cache t_u ON e.target_id = t_u.user_id
    LEFT JOIN userdb.channel_cache t_c ON e.target_id = t_c.channel_id
    LEFT JOIN userdb.roles t_r ON e.target_id = t_r.role_id
    WHERE e.guild_id = ? AND timestamp >= ? AND timestamp <= ?
    ORDER BY e.timestamp DESC LIMIT ?
"""
try:
    cursor.execute(query, ('1494456063729078294', '2020-01-01', '2030-01-01', 50000))
    print('Query succeeded')
except Exception as e:
    print('Query failed:', e)
