import re
import os

FILE_PATH = "web/api/main.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update allow_origins logic for CORS
cors_old = """app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # CRA / alternatif
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://kyrik.duckdns.org",
    ],"""
cors_new = """origins = ["https://kyrik.duckdns.org"]
if os.getenv("ENVIRONMENT") == "development":
    origins.extend([
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,"""
content = content.replace(cors_old, cors_new)


# 2. Replace Sync wrappers with Async wrappers
sync_wrappers_regex = r"class SyncOracleCursor:.*?def get_db_connection\(db_path=None\):\n\s*return SyncOracleConnection\(\)\n"
async_wrappers = """
from core.database import Database
shared_db = Database()

class AsyncOracleCursor:
    def __init__(self, cursor):
        self.cursor = cursor
        
    @property
    def description(self):
        return self.cursor.description

    @property
    def rowcount(self):
        return self.cursor.rowcount

    async def execute(self, query, params=()):
        if isinstance(params, list):
            params = tuple(params)
        
        query = shared_db._translate_query(query)
        try:
            await self.cursor.execute(query, params)
        except Exception as e:
            print(f"Oracle Execution Error: {e} - Query: {query} - Params: {params}")
        return self

    async def fetchone(self):
        try:
            row = await self.cursor.fetchone()
            if not row: return None
            return dict(zip([d[0].lower() for d in self.cursor.description], row))
        except Exception as e:
            print(f"Fetchone error: {e}")
            return None

    async def fetchall(self):
        try:
            rows = await self.cursor.fetchall()
            if not rows: return []
            cols = [d[0].lower() for d in self.cursor.description]
            return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            print(f"Fetchall error: {e}")
            return []

class AsyncOracleConnection:
    def __init__(self, conn):
        self.conn = conn
            
    def cursor(self):
        if not self.conn:
            return None
        return AsyncOracleCursor(self.conn.cursor())
        
    async def commit(self):
        if self.conn:
            await self.conn.commit()
            
    async def close(self):
        if self.conn and oracle_pool:
            await oracle_pool.release(self.conn)
            self.conn = None

async def get_db_connection(db_path=None):
    try:
        conn = await oracle_pool.acquire() if oracle_pool else None
        return AsyncOracleConnection(conn)
    except Exception as e:
        print(f"Oracle Connection Acquire Error: {e}")
        return AsyncOracleConnection(None)
"""
content = re.sub(sync_wrappers_regex, async_wrappers, content, flags=re.DOTALL)


# 3. Fix startup/shutdown events
content = content.replace("def startup_event():", "async def startup_event():")
content = content.replace("def shutdown_event():", "async def shutdown_event():")
content = content.replace("oracle_pool = oracledb.create_pool(", "oracle_pool = oracledb.create_pool_async(")
content = content.replace("oracle_pool.close()", "await oracle_pool.close()")


# 4. Make all routes and dependencies async
def make_async(match):
    indent = match.group(1)
    func_def = match.group(2)
    if "async def" not in func_def:
        return f"{indent}async {func_def}"
    return match.group(0)

content = re.sub(r'(?m)^([ \t]*)(def (?:verify_guild_access|verify_write_access|verify_owner_access|verify_token|fetch_kumiho_db_data)\b.*?:)', make_async, content)
content = re.sub(r'(?m)^([ \t]*)(def (?:get_global_stats|get_guilds|get_guild_stats|get_user_current_roles|get_guild_logs|get_guild_channels|get_discord_channels|get_voice_rooms|get_voice_settings|update_voice_settings|delete_voice_room|kick_user_from_room|setup_private_voice|delete_private_voice|setup_private_voice_manual|get_settings|update_settings|update_channel_setting|get_notes|add_note|delete_note|get_commands|update_commands|get_forms|create_form|update_form|delete_form|summon_form|get_roles|create_command_category|update_category_roles|remove_category_roles|admin_action|check_panel_auth|update_panel_auth|remove_panel_auth|upload_banner|update_ticket_settings)\b.*?:)', make_async, content)


# 5. Add await to DB calls
content = re.sub(r'(?<!await )\bget_db_connection\(', 'await get_db_connection(', content)
content = re.sub(r'(?<!await )([a-zA-Z0-9_]+)\.execute\(', r'await \1.execute(', content)
content = re.sub(r'(?<!await )([a-zA-Z0-9_]+)\.fetchone\(', r'await \1.fetchone(', content)
content = re.sub(r'(?<!await )([a-zA-Z0-9_]+)\.fetchall\(', r'await \1.fetchall(', content)
content = re.sub(r'(?<!await )([a-zA-Z0-9_]+)\.commit\(', r'await \1.commit(', content)
content = re.sub(r'(?<!await )([a-zA-Z0-9_]+)\.close\(', r'await \1.close(', content)

# 6. Fix `fetch_kumiho_db_data` call inside `discord_callback`
content = content.replace("await run_in_threadpool(fetch_kumiho_db_data)", "await fetch_kumiho_db_data()")

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("Refactor script executed successfully.")
