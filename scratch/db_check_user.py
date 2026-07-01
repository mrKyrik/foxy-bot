import sqlite3

db_path = "Data/USER-DB.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Checking user in databases:")

# Check bot_bans
cursor.execute("SELECT * FROM bot_bans WHERE user_id = ?", ("601344424429092864",))
print("bot_bans:", cursor.fetchall())

# Check eco_bans
cursor.execute("SELECT * FROM eco_bans WHERE user_id = ?", ("601344424429092864",))
print("eco_bans:", cursor.fetchall())

# Check roles & role_permissions assigned
cursor.execute("SELECT * FROM role_permissions WHERE role_id IN (SELECT role_id FROM saved_roles WHERE user_id = ?)", ("601344424429092864",))
print("Saved role permissions:", cursor.fetchall())

# Print list of all roles in saved_roles
cursor.execute("SELECT * FROM saved_roles WHERE user_id = ?", ("601344424429092864",))
print("Saved roles:", cursor.fetchall())

conn.close()
