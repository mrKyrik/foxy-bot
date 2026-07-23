import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from core.database import Database

async def main():
    db = Database()
    await db.init()
    
    cols = [
        ("bar_color", "VARCHAR2(20) DEFAULT '#10B981'"),
        ("border_color", "VARCHAR2(20) DEFAULT '#00C8FF'"),
        ("border_width", "NUMBER DEFAULT 6"),
        ("overlay_opacity", "NUMBER DEFAULT 60"),
        ("name_color", "VARCHAR2(20) DEFAULT '#FFFFFF'")
    ]
    
    for col_name, col_type in cols:
        try:
            await db.execute(f"ALTER TABLE global_profiles ADD {col_name} {col_type}")
            print(f"Added {col_name}")
        except Exception as e:
            print(f"Error adding {col_name}: {e}")
            
    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
