import sqlite3
import os

def migrate():
    print("Starting DB migration to kumiho.db...")
    conn = sqlite3.connect('kumiho.db')
    c = conn.cursor()
    
    if os.path.exists('Data/USER-DB.db'):
        print("Attaching USER-DB.db...")
        c.execute("ATTACH DATABASE 'Data/USER-DB.db' AS userdb")
        c.execute("SELECT name FROM userdb.sqlite_master WHERE type='table'")
        tables = c.fetchall()
        for t in tables:
            table_name = t[0]
            if table_name.startswith('sqlite_'): continue
            
            # get schema
            c.execute(f"SELECT sql FROM userdb.sqlite_master WHERE type='table' AND name='{table_name}'")
            row = c.fetchone()
            if not row or not row[0]:
                continue
            schema = row[0]
            
            # create table in main db
            try:
                c.execute(schema)
            except Exception as e:
                print(f"  [!] Failed to create {table_name}: {e}")
            
            # insert data
            try:
                c.execute(f"INSERT OR IGNORE INTO {table_name} SELECT * FROM userdb.{table_name}")
                print(f"  [+] Migrated {table_name} from USER-DB.db")
            except Exception as e:
                print(f"  [!] Failed to migrate data for {table_name}: {e}")
                
        conn.commit()
        c.execute("DETACH DATABASE userdb")
        print("USER-DB.db migration finished.\n")
    else:
        print("Data/USER-DB.db not found.\n")
        
    if os.path.exists('Data/ADMIN-EVENTS.db'):
        print("Attaching ADMIN-EVENTS.db...")
        c.execute("ATTACH DATABASE 'Data/ADMIN-EVENTS.db' AS admindb")
        c.execute("SELECT name FROM admindb.sqlite_master WHERE type='table'")
        tables = c.fetchall()
        for t in tables:
            table_name = t[0]
            if table_name.startswith('sqlite_'): continue
            
            c.execute(f"SELECT sql FROM admindb.sqlite_master WHERE type='table' AND name='{table_name}'")
            row = c.fetchone()
            if not row or not row[0]:
                continue
            schema = row[0]
            
            try:
                c.execute(schema)
            except Exception as e:
                print(f"  [!] Failed to create {table_name}: {e}")
            
            try:
                c.execute(f"INSERT OR IGNORE INTO {table_name} SELECT * FROM admindb.{table_name}")
                print(f"  [+] Migrated {table_name} from ADMIN-EVENTS.db")
            except Exception as e:
                print(f"  [!] Failed to migrate data for {table_name}: {e}")
                
        conn.commit()
        c.execute("DETACH DATABASE admindb")
        print("ADMIN-EVENTS.db migration finished.\n")
    else:
        print("Data/ADMIN-EVENTS.db not found.\n")

    conn.close()
    print("Migration process complete!")

if __name__ == '__main__':
    migrate()
