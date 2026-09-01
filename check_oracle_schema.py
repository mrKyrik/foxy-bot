import os
import oracledb
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
WALLET_DIR = os.path.join(PROJECT_ROOT, "core", "wallet")

conn = oracledb.connect(
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    dsn=os.getenv("DB_DSN"),
    config_dir=WALLET_DIR,
    wallet_location=WALLET_DIR,
    wallet_password=os.getenv("DB_PASSWORD")
)

cursor = conn.cursor()

print("=== USER TABLES ===")
cursor.execute("SELECT table_name FROM user_tables ORDER BY table_name")
tables = [row[0] for row in cursor.fetchall()]
print(f"Total tables: {len(tables)}")
for t in tables:
    print(f" - {t}")

print("\n=== IDENTITY COLUMNS & CONSTRAINTS ===")
for t in tables:
    cursor.execute("""
        SELECT column_name, data_type, data_default, identity_column 
        FROM user_tab_cols 
        WHERE table_name = :1 
        ORDER BY column_id
    """, (t,))
    cols = cursor.fetchall()
    
    cursor.execute("""
        SELECT constraint_name, constraint_type, search_condition
        FROM user_constraints
        WHERE table_name = :1
    """, (t,))
    constraints = cursor.fetchall()
    
    print(f"\n--- TABLE: {t} ---")
    print("  Columns:")
    for c in cols:
        print(f"    {c[0]} ({c[1]}) default={c[2]} identity={c[3]}")
    print("  Constraints:")
    for con in constraints:
        print(f"    {con[0]} type={con[1]} condition={con[2]}")

print("\n=== SEQUENCES ===")
cursor.execute("SELECT sequence_name, last_number FROM user_sequences")
for seq in cursor.fetchall():
    print(f"  {seq[0]} -> {seq[1]}")

conn.close()
