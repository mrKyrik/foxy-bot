"""
channel_cache migration test scripti.
Temel ve executescript+migration senaryolarini test eder.
"""
import asyncio
import aiosqlite
import os

TEST_DB = "Data/test_migration.db"
os.makedirs("Data", exist_ok=True)


async def main():
    # ----------------------------------------------------------------
    # TEST 1: Temel try/except ALTER TABLE migration
    # ----------------------------------------------------------------
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    async with aiosqlite.connect(TEST_DB) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL;")

        # Eski sema: guild_id YOK
        await conn.execute(
            "CREATE TABLE channel_cache "
            "(channel_id TEXT PRIMARY KEY, channel_name TEXT)"
        )
        await conn.execute("INSERT INTO channel_cache VALUES ('123', 'test')")
        await conn.commit()

        print("[TEST1] Eski sema olusturuldu.")

        # Migration dene
        try:
            await conn.execute(
                "ALTER TABLE channel_cache ADD COLUMN guild_id TEXT"
            )
            print("[TEST1] ALTER TABLE OK")
        except Exception as e:
            print(f"[TEST1] ALTER TABLE FAILED: {e}")

        await conn.commit()

        cur = await conn.execute("PRAGMA table_info(channel_cache)")
        cols = [r[1] for r in await cur.fetchall()]
        print(f"[TEST1] Sutunlar: {cols}")

        # INSERT dene
        try:
            await conn.execute(
                "INSERT OR REPLACE INTO channel_cache "
                "(channel_id, guild_id, channel_name) VALUES (?, ?, ?)",
                ("456", "GUILD_001", "general"),
            )
            await conn.commit()
            print("[TEST1] INSERT OK")
        except Exception as e:
            print(f"[TEST1] INSERT FAILED: {e}")

    # ----------------------------------------------------------------
    # TEST 2: executescript sonrasi migration (bot init senaryosu)
    # ----------------------------------------------------------------
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    async with aiosqlite.connect(TEST_DB) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL;")

        # Eski sema
        await conn.execute(
            "CREATE TABLE channel_cache "
            "(channel_id TEXT PRIMARY KEY, channel_name TEXT)"
        )
        await conn.commit()
        print("\n[TEST2] Eski sema olusturuldu.")

        # executescript calistir (bot init'te olan)
        try:
            await conn.executescript(
                "CREATE TABLE IF NOT EXISTS dummy_tbl (id INTEGER PRIMARY KEY);"
            )
            print("[TEST2] executescript calistirildi.")
        except Exception as e:
            print(f"[TEST2] executescript hatasi: {e}")

        # Migration
        try:
            await conn.execute(
                "ALTER TABLE channel_cache ADD COLUMN guild_id TEXT"
            )
            print("[TEST2] ALTER TABLE OK")
        except Exception as e:
            print(f"[TEST2] ALTER TABLE FAILED: {e}")

        await conn.commit()

        cur = await conn.execute("PRAGMA table_info(channel_cache)")
        cols = [r[1] for r in await cur.fetchall()]
        print(f"[TEST2] Sutunlar: {cols}")

        if "guild_id" not in cols:
            print("[TEST2] SORUN TESPIT EDILDI: guild_id eklenmedi!")
            print("[TEST2] Alternatif fix: RECREATE yontemi deneniyor...")

            # Alternatif: tablo yeniden olustur
            await conn.executescript("""
                CREATE TABLE channel_cache_new (
                    channel_id   TEXT PRIMARY KEY,
                    guild_id     TEXT,
                    channel_name TEXT,
                    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                INSERT OR IGNORE INTO channel_cache_new
                    (channel_id, channel_name)
                    SELECT channel_id, channel_name FROM channel_cache;
                DROP TABLE channel_cache;
            """)
            await conn.execute(
                "ALTER TABLE channel_cache_new RENAME TO channel_cache"
            )
            await conn.commit()

            cur = await conn.execute("PRAGMA table_info(channel_cache)")
            cols = [r[1] for r in await cur.fetchall()]
            print(f"[TEST2] RECREATE sonrasi sutunlar: {cols}")

        # INSERT dene
        try:
            await conn.execute(
                "INSERT OR REPLACE INTO channel_cache "
                "(channel_id, guild_id, channel_name) VALUES (?, ?, ?)",
                ("789", "GUILD_002", "ops"),
            )
            await conn.commit()
            print("[TEST2] INSERT OK")
        except Exception as e:
            print(f"[TEST2] INSERT FAILED: {e}")

    # ----------------------------------------------------------------
    # TEST 3: Gercek DB'de guild_id var mi kontrol et
    # ----------------------------------------------------------------
    real_db = "Data/USER-DB.db"
    if os.path.exists(real_db):
        async with aiosqlite.connect(real_db) as conn:
            conn.row_factory = aiosqlite.Row
            try:
                cur = await conn.execute("PRAGMA table_info(channel_cache)")
                cols = [r[1] for r in await cur.fetchall()]
                print(f"\n[TEST3] Gercek DB channel_cache sutunlari: {cols}")
                if "guild_id" in cols:
                    print("[TEST3] guild_id MEVCUT - sorun migration oncesinde!")
                else:
                    print("[TEST3] guild_id YOK - migration calismamis!")
            except Exception as e:
                print(f"[TEST3] Gercek DB okunamadi: {e}")
    else:
        print("\n[TEST3] Gercek DB bulunamadi, atlanıyor.")

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    print("\n=== Testler tamamlandi ===")


asyncio.run(main())
