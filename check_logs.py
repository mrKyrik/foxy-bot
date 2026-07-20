import asyncio
import oracledb

async def check():
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
            # Revert tyom-itiraf back
            await cursor.execute("""
                UPDATE custom_forms 
                SET action_target = '1527368264865415280' 
                WHERE form_id = 'tyom-itiraf' AND guild_id = '1507723513182818544'
            """)
            await conn.commit()
            print("REVERTED tyom-itiraf to original channel")
            
            # Check log_channels
            await cursor.execute("SELECT guild_id, log_type, log_channel_id FROM log_channels WHERE guild_id = '1507723513182818544'")
            rows = await cursor.fetchall()
            print("LOG CHANNELS IN TYOM:")
            for r in rows:
                print(r)
    await pool.close()

asyncio.run(check())
