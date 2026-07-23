import asyncio
import sqlite3
import os
from dotenv import load_dotenv
load_dotenv()
from core.database import Database

async def main():
    # SQLite
    sl_conn = sqlite3.connect("rescued_kumiho.db")
    sl_conn.row_factory = sqlite3.Row
    sl_cur = sl_conn.cursor()
    try:
        sl_cur.execute("SELECT * FROM global_profiles")
        rows = sl_cur.fetchall()
        print(f"Found {len(rows)} profiles in SQLite.")
    except Exception as e:
        print("Could not query SQLite global_profiles:", e)
        rows = []
    
    # Oracle
    db = Database()
    await db.init()
    
    for row in rows:
        user_id = row["user_id"]
        color_hex = row["color_hex"]
        
        # Check if columns exist
        keys = row.keys()
        bar_color = row["bar_color"] if "bar_color" in keys else None
        border_color = row["border_color"] if "border_color" in keys else None
        border_width = row["border_width"] if "border_width" in keys else None
        overlay_opacity = row["overlay_opacity"] if "overlay_opacity" in keys else None
        name_color = row["name_color"] if "name_color" in keys else None
        blur_amount = row["blur_amount"] if "blur_amount" in keys else 0
            
        print(f"Migrating user {user_id}")
        await db.execute(
            """
            MERGE INTO global_profiles p
            USING (SELECT :1 as user_id FROM dual) d
            ON (p.user_id = d.user_id)
            WHEN MATCHED THEN
                UPDATE SET color_hex = :2, bar_color = :3, border_color = :4, border_width = :5, overlay_opacity = :6, name_color = :7, blur_amount = :8
            WHEN NOT MATCHED THEN
                INSERT (user_id, color_hex, bar_color, border_color, border_width, overlay_opacity, name_color, blur_amount)
                VALUES (:1, :2, :3, :4, :5, :6, :7, :8)
            """,
            user_id, color_hex, bar_color, border_color, border_width, overlay_opacity, name_color, blur_amount
        )
        
    print("Done migrating profiles.")

if __name__ == "__main__":
    asyncio.run(main())
