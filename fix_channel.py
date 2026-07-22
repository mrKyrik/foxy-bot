import asyncio
import oracledb

async def fix():
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
            # Update the admin log channel (channel_id) to tyom-log in Çayifikasyon
            await cursor.execute("""
                UPDATE custom_forms 
                SET channel_id = '1528033302773239868' 
                WHERE form_id = 'tyom-itiraf' AND guild_id = '1507723513182818544'
            """)
            await conn.commit()
            print("FIXED: channel_id updated to Çayifikasyon tyom-log")
    await pool.close()

asyncio.run(fix())
