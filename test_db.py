import asyncio
from dotenv import load_dotenv
load_dotenv()
from core.database import Database

async def main():
    db = Database()
    await db.init()
    
    rows = await db.fetchall("SELECT * FROM global_profiles")
    print("GLOBAL_PROFILES (ORACLE):", rows)
    
    # Try querying levels
    try:
        l_rows = await db.fetchall("SELECT * FROM levels WHERE rownum <= 5")
        print("LEVELS (ORACLE):", l_rows)
    except Exception as e:
        print("LEVELS error:", e)

if __name__ == "__main__":
    asyncio.run(main())
