import sqlite3
import json

try:
    conn = sqlite3.connect("Data/USER-DB.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
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
        c.channel_name
    FROM db_event_logs e
    LEFT JOIN user_cache u ON e.user_id = u.user_id
    LEFT JOIN channel_cache c ON e.channel_id = c.channel_id
    WHERE e.guild_id = ? 
    ORDER BY e.timestamp DESC LIMIT 5
    """
    cursor.execute(query, ("1424129369541972102",))
    rows = cursor.fetchall()
    print("----- Web API db_event_logs Query -----")
    for row in rows:
        print(dict(row))
        
except sqlite3.Error as e:
    print("SQLite Error:", e)
except Exception as e:
    print("Error:", e)
