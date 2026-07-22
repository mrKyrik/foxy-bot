import asyncio
import oracledb

async def update_form():
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
            # Update action_target for tyom-itiraf
            await cursor.execute("""
                UPDATE custom_forms 
                SET action_target = '1528033302773239868' 
                WHERE form_id = 'tyom-itiraf' AND guild_id = '1507723513182818544'
            """)
            await conn.commit()
            print("UPDATE SUCCESSFUL")
    await pool.close()

asyncio.run(update_form())
