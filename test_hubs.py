import asyncio
import oracledb

async def main():
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
            await cursor.execute("SELECT table_name, column_name, data_type FROM user_tab_columns WHERE table_name IN ('PRIVATE_VOICE_HUBS', 'BOT_COMMANDS_REGISTRY')")
            rows = await cursor.fetchall()
            print("Columns in Oracle:")
            for row in rows:
                print(row)
    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
