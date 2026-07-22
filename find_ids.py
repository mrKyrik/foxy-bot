import asyncio
import oracledb

async def run():
    pool = oracledb.create_pool_async(
        user="admin",
        password="$@P%5WCUgMnb",
        dsn="kumihodb_high",
        min=1,
        max=2,
        config_dir=r"C:\Users\kIrik\OneDrive - ABDULLAH GUL UNIVERSITESI\Masaüstü\kumiho\core\wallet",
        wallet_location=r"C:\Users\kIrik\OneDrive - ABDULLAH GUL UNIVERSITESI\Masaüstü\kumiho\core\wallet",
        wallet_password="$@P%5WCUgMnb"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT channel_id, guild_id, channel_name FROM channel_cache WHERE LOWER(channel_name) LIKE '%tyom%' OR LOWER(channel_name) LIKE '%log%'")
            rows = await cursor.fetchall()
            for r in rows:
                print(r)
            
            print("--- GUILDS ---")
            await cursor.execute("SELECT form_id, guild_id, title, channel_id, action_target FROM custom_forms WHERE form_id='tyom-itiraf'")
            rows = await cursor.fetchall()
            for r in rows:
                print(r)
    await pool.close()

asyncio.run(run())
