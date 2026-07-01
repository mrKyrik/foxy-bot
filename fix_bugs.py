import os
import glob
import re
import sqlite3

directory = r"C:\Users\kIrik\OneDrive - ABDULLAH GUL UNIVERSITESI\Masaüstü\kumiho\web\dashboard\src\pages"
files = glob.glob(os.path.join(directory, "*LogPage.jsx"))

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    changed = False

    if "zoomWindowMs" in content and "const zoomWindowMs" not in content:
        # It needs zoomWindowMs but doesn't have it.
        # Find const timeMax = ...
        pattern = r"(const timeMax = viewWindow \? viewWindow\[1\] : 0;)"
        replacement = r"\1\n  const zoomWindowMs = timeMax - timeMin;"
        content = re.sub(pattern, replacement, content)
        changed = True

    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Added zoomWindowMs to {os.path.basename(filepath)}")

# Now fix the database
try:
    conn = sqlite3.connect(r"C:\Users\kIrik\OneDrive - ABDULLAH GUL UNIVERSITESI\Masaüstü\kumiho\Data\USER-DB.db")
    c = conn.cursor()
    # Check if users table exists
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, username TEXT, avatar_url TEXT)")
    
    # Insert the user ID "601344424429092864" -> "kIrik"
    c.execute("INSERT OR IGNORE INTO users (user_id, username, avatar_url) VALUES (?, ?, ?)", ("601344424429092864", "kIrik", "https://cdn.discordapp.com/avatars/601344424429092864/avatar.png"))
    c.execute("UPDATE users SET username='kIrik', avatar_url='https://cdn.discordapp.com/avatars/601344424429092864/avatar.png' WHERE user_id='601344424429092864'")
    
    conn.commit()
    conn.close()
    print("Database users updated.")
except Exception as e:
    print("Database error:", e)

