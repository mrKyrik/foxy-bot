import sqlite3

conn = sqlite3.connect('c:/Users/kIrik/OneDrive - ABDULLAH GUL UNIVERSITESI/Masaüstü/kumiho/Data/USER-DB.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT event_type, COUNT(*) as c FROM db_event_logs GROUP BY event_type')
print("--- USER-DB db_event_logs ---")
for r in c.fetchall():
    print(r['event_type'], r['c'])
    
print("--- ADMIN-EVENTS admin_events ---")
try:
    conn2 = sqlite3.connect('c:/Users/kIrik/OneDrive - ABDULLAH GUL UNIVERSITESI/Masaüstü/kumiho/Data/ADMIN-EVENTS.db')
    conn2.row_factory = sqlite3.Row
    c2 = conn2.cursor()
    c2.execute('SELECT action_type, COUNT(*) as c FROM admin_events GROUP BY action_type')
    for r in c2.fetchall():
        print(r['action_type'], r['c'])
except Exception as e:
    print('Error:', e)
