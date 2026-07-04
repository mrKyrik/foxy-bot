import sqlite3

conn = sqlite3.connect('c:/Users/kIrik/OneDrive - ABDULLAH GUL UNIVERSITESI/Masaüstü/kumiho/Data/ADMIN-EVENTS.db')
c = conn.cursor()
c.execute("""
    INSERT INTO admin_events (guild_id, admin_id, action_type, target_id, reason, timestamp)
    VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
""", ('1424129369541972102', '797045576218837022', 'mod_ban', '1417572340904104028', 'Test ban reason'))
conn.commit()
conn.close()
print('Inserted dummy mod_ban')
