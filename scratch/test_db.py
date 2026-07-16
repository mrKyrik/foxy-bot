import asyncio
from core.database import Database

async def test():
    db = Database()
    await db.init()
    print("DB Init finished.")
    
    # Check if table exists
    cursor = await db.user_db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='web_actions'")
    row = await cursor.fetchone()
    if row:
        print("Table web_actions exists!")
    else:
        print("Table web_actions MISSING!")

asyncio.run(test())
