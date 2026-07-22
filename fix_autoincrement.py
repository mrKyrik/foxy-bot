import asyncio
import oracledb

tables_cols = [
    ("admin_notes", "id"),
    ("pending_actions", "id"),
    ("warns", "warn_id"),
    ("suggestions", "suggestion_id"),
    ("db_event_logs", "log_id"),
    ("form_questions", "question_id"),
    ("form_roles", "action_id"),
from core.database import Database

async def main():
    db = Database()
    await db.connect()
    
    rows = await db.fetchall("SELECT * FROM private_voice_hubs")
    print("Private Voice Hubs in Oracle:")
    for row in rows:
        print(row)
        
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
