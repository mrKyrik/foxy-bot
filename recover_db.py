import sqlite3
import traceback

def recover_db(corrupt_path, new_path, schema_path):
    print("Connecting to schema DB...")
    schema_conn = sqlite3.connect(schema_path)
    schema_cursor = schema_conn.cursor()
    
    # Get all tables
    schema_cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
    tables = schema_cursor.fetchall()
    
    print("Creating new DB...")
    new_conn = sqlite3.connect(new_path)
    new_cursor = new_conn.cursor()
    
    for table_name, table_sql in tables:
        if table_sql:
            try:
                new_cursor.execute(table_sql)
            except sqlite3.OperationalError:
                pass # Already exists
                
    new_conn.commit()
    
    print("Connecting to corrupt DB...")
    corrupt_conn = sqlite3.connect(corrupt_path)
    corrupt_cursor = corrupt_conn.cursor()
    
    for table_name, _ in tables:
        print(f"Recovering table {table_name}...")
        try:
            corrupt_cursor.execute(f"SELECT * FROM {table_name}")
            rows = corrupt_cursor.fetchall()
            if rows:
                placeholders = ",".join(["?"] * len(rows[0]))
                new_cursor.executemany(f"INSERT OR IGNORE INTO {table_name} VALUES ({placeholders})", rows)
                new_conn.commit()
                print(f"  -> Recovered {len(rows)} rows.")
        except Exception as e:
            print(f"  -> Error recovering table {table_name}: {e}")
            # Try row by row if fetchall fails
            try:
                corrupt_cursor.execute(f"SELECT * FROM {table_name}")
                count = 0
                while True:
                    try:
                        row = corrupt_cursor.fetchone()
                        if row is None:
                            break
                        placeholders = ",".join(["?"] * len(row))
                        new_cursor.execute(f"INSERT OR IGNORE INTO {table_name} VALUES ({placeholders})", row)
                        count += 1
                    except Exception as row_e:
                        print(f"    Row error: {row_e}")
                        break
                new_conn.commit()
                print(f"  -> Recovered {count} rows row-by-row.")
            except Exception as outer_e:
                 print(f"  -> Could not even query {table_name}: {outer_e}")
                 
    new_conn.close()
    corrupt_conn.close()
    schema_conn.close()
    print("Recovery complete.")

if __name__ == "__main__":
    recover_db("kumiho_corrupt.db", "kumiho_recovered.db", "kumiho.db")
