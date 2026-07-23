import asyncio
from core.database import DatabaseManager

async def r():
    db = DatabaseManager()
    await db.connect()
    try:
        await db.execute('ALTER TABLE global_profiles ADD blur_amount NUMBER DEFAULT 0')
        print('Added blur_amount')
    except Exception as e:
        print('blur_amount err:', e)
        
    try:
        await db.execute('CREATE TABLE upload_tokens (token VARCHAR2(255) PRIMARY KEY, user_id VARCHAR2(255), expires_at NUMBER)')
        print('Created upload_tokens')
    except Exception as e:
        print('upload_tokens err:', e)
        
    await db.close()

asyncio.run(r())
