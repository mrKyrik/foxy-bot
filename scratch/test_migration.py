import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import Database
from web.api.main import init_db

async def test_migration():
    print("Testing init_db() from web/api/main.py...")
    init_db()
    print("init_db() passed.")
    
    print("Testing Database.init() from core/database.py...")
    db = Database(
        user_db_path="Data/USER-DB.db",
        admin_db_path="Data/ADMIN-EVENTS.db"
    )
    await db.init()
    print("Database.init() passed.")
    await db.close()
    
    print("All migrations completed successfully.")

if __name__ == "__main__":
    asyncio.run(test_migration())
