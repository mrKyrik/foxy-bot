import sqlite3

def test():
    admin_conn = sqlite3.connect('Data/ADMIN-EVENTS.db')
    cursor = admin_conn.cursor()
    cursor.execute("ATTACH DATABASE 'Data/USER-DB.db' AS userdb")
    try:
        cursor.execute('''
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
            LIMIT 1
        ''')
        print("ADMIN-EVENTS Query: SUCCESS")
    except Exception as e:
        print("ADMIN-EVENTS Query: FAILED", e)
    
    user_conn = sqlite3.connect('Data/USER-DB.db')
    cursor = user_conn.cursor()
    try:
        cursor.execute('''
            SELECT
                e.log_id as id,
                'general' as source,
                e.event_type,
                e.user_id,
                e.details,
                e.timestamp,
                e.channel_id,
                u.username,
                u.avatar_url,
                c.channel_name,
                r.role_name
            FROM db_event_logs e
            LEFT JOIN user_cache u ON e.user_id = u.user_id
            LEFT JOIN channel_cache c ON e.channel_id = c.channel_id
            LEFT JOIN roles r ON e.channel_id = r.role_id AND e.guild_id = r.guild_id
            LIMIT 1
        ''')
        print("USER-DB Query: SUCCESS")
    except Exception as e:
        print("USER-DB Query: FAILED", e)

if __name__ == '__main__':
    test()
