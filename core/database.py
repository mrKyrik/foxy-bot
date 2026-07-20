import logging
import os
import re
import itertools
import oracledb

class DBRow(dict):
    def __init__(self, cols, vals):
        super().__init__(zip(cols, vals))
        self.vals = vals
        
    def __getitem__(self, key):
        if isinstance(key, int):
            return self.vals[key]
        return super().__getitem__(key)

    def __iter__(self):
        return iter(self.vals)

log = logging.getLogger(__name__)

DB_USER = "admin"
DB_PASSWORD = "$@P%5WCUgMnb"
DB_DSN = "kumihodb_high"
WALLET_DIR = os.path.join(os.path.dirname(__file__), "wallet")

class Database:
    """
    Oracle Autonomous Database için async bağlantı havuzu (connection pool) wrapper'ı.
    """

    def __init__(self) -> None:
        self.pool: oracledb.AsyncConnectionPool | None = None

    @property
    def user_db(self):
        return self
        
    @property
    def admin_db(self):
        return self

    async def init(self) -> None:
        """Oracle DB Connection Pool oluştur."""
        log.info("Oracle DB bağlantı havuzu başlatılıyor...")
        
        # Sadece thin mode ile bağlan
        try:
            self.pool = oracledb.create_pool_async(
                user=DB_USER,
                password=DB_PASSWORD,
                dsn=DB_DSN,
                min=2,
                max=20,
                increment=2,
                config_dir=WALLET_DIR,
                wallet_location=WALLET_DIR,
                wallet_password=DB_PASSWORD
            )
            log.info("Oracle Autonomous DB bağlantı havuzu başarıyla oluşturuldu!")
        except Exception as e:
            log.error(f"Oracle DB Bağlantı Hatası: {e}")
            raise

    async def close(self) -> None:
        """Bot kapanırken havuzu temizle."""
        if self.pool:
            await self.pool.close()
        log.info("Oracle DB bağlantıları kapatıldı.")

    def _translate_query(self, query: str) -> str:
        """
        SQLite '?' parametrelerini Oracle ':1, :2' formatına çevirir.
        Ayrıca bazı SQLite terimlerini (LIMIT, INSERT OR IGNORE) Oracle uyumlu hale getirir.
        """
        # LIMIT 1 -> FETCH FIRST 1 ROWS ONLY
        if "LIMIT 1" in query.upper():
            query = re.sub(r'(?i)\bLIMIT\s+1\b', 'FETCH FIRST 1 ROWS ONLY', query)
        
        # INSERT OR IGNORE -> PL/SQL blok
        if "INSERT OR IGNORE" in query.upper():
            # Regex ile yakalayıp PL/SQL'e saralım
            query = re.sub(r'(?is)INSERT\s+OR\s+IGNORE\s+INTO\s+(.*?)(?:;|\s*$)', r'BEGIN INSERT INTO \1; EXCEPTION WHEN DUP_VAL_ON_INDEX THEN NULL; END;', query)

        # ON CONFLICT DO UPDATE SET -> MERGE INTO
        if "ON CONFLICT" in query.upper():
            match = re.search(r'(?is)INSERT\s+INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)\s*ON\s+CONFLICT\s*\((.*?)\)\s*DO\s+UPDATE\s+SET\s+(.*)', query)
            if match:
                table = match.group(1)
                cols = [c.strip() for c in match.group(2).split(',')]
                vals = [v.strip() for v in match.group(3).split(',')]
                conflicts = [c.strip() for c in match.group(4).split(',')]
                updates = match.group(5)
                
                using_cols = []
                for i, (col, val) in enumerate(zip(cols, vals)):
                    using_cols.append(f"{val} as {col}")
                using_str = "SELECT " + ", ".join(using_cols) + " FROM DUAL"
                
                on_cond = " AND ".join(f"t.{c} = s.{c}" for c in conflicts)
                upd_str = updates.replace("excluded.", "s.")
                
                query = (
                    f"MERGE INTO {table} t "
                    f"USING ({using_str}) s "
                    f"ON ({on_cond}) "
                    f"WHEN MATCHED THEN UPDATE SET {upd_str} "
                    f"WHEN NOT MATCHED THEN INSERT ({', '.join(cols)}) VALUES ({', '.join('s.'+c for c in cols)})"
                )

        # Oracle'da LEVEL reserved word olduğu için sorgulardaki (tablo ismi olmayan) level kelimesini "LEVEL" yap
        # Sadece "level" sütunlarını değiştirmek için (level_id vs etkilenmez)
        query = re.sub(r'(?i)\blevel\b', '"LEVEL"', query)
        
        # ? -> :1, :2, :3
        def repl(match, c=itertools.count(1)):
            return f":{next(c)}"
            
        return re.sub(r'\?', repl, query)

    async def execute(self, query: str, *args) -> None:
        """DB'de INSERT/UPDATE/DELETE çalıştır ve commit et."""
        query = self._translate_query(query)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, args)
                await conn.commit()

    async def fetchone(self, query: str, *args) -> dict | None:
        """DB'den tek satır döndür. aiosqlite.Row gibi dict döndürür."""
        query = self._translate_query(query)
        async with self.pool.acquire() as conn:
            # Sütun isimlerini döndürmesi için rowfactory
            conn.autocommit = False
            async with conn.cursor() as cursor:
                await cursor.execute(query, args)
                
                columns = [col[0].lower() for col in cursor.description] if cursor.description else []
                cursor.rowfactory = lambda *vals: DBRow(columns, vals)
                
                return await cursor.fetchone()

    async def fetchall(self, query: str, *args) -> list[dict]:
        """DB'den tüm satırları döndür."""
        query = self._translate_query(query)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, args)
                
                columns = [col[0].lower() for col in cursor.description] if cursor.description else []
                cursor.rowfactory = lambda *vals: DBRow(columns, vals)
                
                return await cursor.fetchall()


    async def executemany(self, query: str, data: list) -> None:
        """DB'de toplu INSERT/UPDATE."""
        query = self._translate_query(query)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.executemany(query, data)
                await conn.commit()

    # ------------------------------------------------------------------
    # Spesifik Log Fonksiyonları
    # ------------------------------------------------------------------

    async def log_admin_event(
        self,
        guild_id: int,
        admin_id: int,
        action_type: str,
        target_id: int,
        reason: str = "Belirtilmedi",
    ) -> None:
        log.info(
            "ADMIN ACTION | guild=%s | %s | admin=%s | target=%s | reason=%s",
            guild_id, action_type, admin_id, target_id, reason,
        )

        await self.execute(
            """
            INSERT INTO admin_events (guild_id, admin_id, action_type, target_id, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            str(guild_id), str(admin_id), action_type, str(target_id), reason,
        )

    async def log_db_event(
        self,
        guild_id,
        event_type,
        setting_key,
        user_id,
        details,
        channel_id=None
    ) -> None:
        if setting_key:
            try:
                row = await self.fetchone(
                    "SELECT * FROM db_log_settings WHERE guild_id=?", str(guild_id)
                )
                if row:
                    if setting_key in row and row[setting_key] != 1:
                        return
                else:
                    return
            except Exception as e:
                log.error("log_db_event ayar kontrol hatası: %s", e)

        import json
        details_str = json.dumps(details, ensure_ascii=False) if isinstance(details, dict) else str(details)

        try:
            await self.execute(
                """
                INSERT INTO db_event_logs (guild_id, event_type, user_id, details, channel_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                str(guild_id),
                event_type,
                str(user_id) if user_id else None,
                details_str,
                str(channel_id) if channel_id else None,
            )
        except Exception as e:
            log.error("log_db_event hatası: %s", e)

    async def log_db_events_bulk(self, events: list) -> None:
        import json
        insert_data = []
        for ev in events:
            guild_id, event_type, user_id, details, channel_id = ev
            details_str = json.dumps(details, ensure_ascii=False) if isinstance(details, dict) else str(details)
            
            insert_data.append((
                str(guild_id),
                event_type,
                str(user_id) if user_id else None,
                details_str,
                str(channel_id) if channel_id else None
            ))
            
        try:
            await self.executemany(
                """
                INSERT INTO db_event_logs (guild_id, event_type, user_id, details, channel_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                insert_data
            )
        except Exception as e:
            log.error(f"log_db_events_bulk hatası: {e}")

    async def update_user_cache(self, user_id: str, username: str, avatar_url: str | None) -> None:
        # SQLite'daki ON CONFLICT DO UPDATE -> Oracle'da MERGE INTO'dur.
        # Bu fonksiyonu MERGE INTO olarak yeniden yazdık:
        try:
            query = """
            MERGE INTO user_cache t
            USING (SELECT :1 as user_id, :2 as username, :3 as avatar_url FROM DUAL) s
            ON (t.user_id = s.user_id)
            WHEN MATCHED THEN 
                UPDATE SET t.username = s.username, t.avatar_url = s.avatar_url, t.updated_at = SYSTIMESTAMP
            WHEN NOT MATCHED THEN 
                INSERT (user_id, username, avatar_url) VALUES (s.user_id, s.username, s.avatar_url)
            """
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, (str(user_id), username, avatar_url))
                    await conn.commit()
        except Exception as e:
            log.error(f"update_user_cache hatası: {e}")

    async def update_channel_cache(self, guild_id: str, channel_id: str, channel_name: str) -> None:
        try:
            query = """
            MERGE INTO channel_cache t
            USING (SELECT :1 as channel_id, :2 as guild_id, :3 as channel_name FROM DUAL) s
            ON (t.channel_id = s.channel_id)
            WHEN MATCHED THEN 
                UPDATE SET t.guild_id = s.guild_id, t.channel_name = s.channel_name, t.updated_at = SYSTIMESTAMP
            WHEN NOT MATCHED THEN 
                INSERT (channel_id, guild_id, channel_name) VALUES (s.channel_id, s.guild_id, s.channel_name)
            """
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, (str(channel_id), str(guild_id), channel_name))
                    await conn.commit()
        except Exception as e:
            log.error(f"update_channel_cache hatası: {e}")

    async def bulk_sync_channel_cache(self, guild_id: str, channels: list[tuple[str, str]]) -> None:
        try:
            await self.execute("DELETE FROM channel_cache WHERE guild_id=?", str(guild_id))
            data = [(c[0], guild_id, c[1]) for c in channels]
            await self.executemany(
                "INSERT INTO channel_cache (channel_id, guild_id, channel_name) VALUES (?, ?, ?)",
                data
            )
        except Exception as e:
            log.error(f"bulk_sync_channel_cache hatası: {e}")

    async def update_role_cache(self, guild_id: str, role_id: str, role_name: str) -> None:
        try:
            await self.execute(
                "INSERT OR IGNORE INTO roles (guild_id, role_id, role_name) VALUES (?, ?, ?)",
                str(guild_id), str(role_id), role_name
            )
        except Exception as e:
            log.error(f"update_role_cache hatası: {e}")
