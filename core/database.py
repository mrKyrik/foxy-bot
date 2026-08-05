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
        if isinstance(key, str):
            if super().__contains__(key):
                return super().__getitem__(key)
            if super().__contains__(key.lower()):
                return super().__getitem__(key.lower())
            if super().__contains__(key.upper()):
                return super().__getitem__(key.upper())
        return super().__getitem__(key)

    def get(self, key, default=None):
        if isinstance(key, str):
            if super().__contains__(key):
                return super().get(key, default)
            if super().__contains__(key.lower()):
                return super().get(key.lower(), default)
            if super().__contains__(key.upper()):
                return super().get(key.upper(), default)
        return super().get(key, default)

    def __contains__(self, key):
        if isinstance(key, str):
            if super().__contains__(key) or super().__contains__(key.lower()) or super().__contains__(key.upper()):
                return True
        return super().__contains__(key)

    def __iter__(self):
        return iter(self.vals)

from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv()

log = logging.getLogger(__name__)

WALLET_DIR = os.path.join(os.path.dirname(__file__), "wallet")

TABLE_PRIMARY_KEYS = {
    "private_voice_hubs": ["guild_id"],
    "custom_forms": ["guild_id", "form_id"],
    "form_admin_roles": ["guild_id"],
    "ragepoints": ["guild_id", "user_id"],
    "level_rewards": ["guild_id", "level"],
    "suggestion_config": ["guild_id"],
    "private_voice_settings": ["user_id"],
    "command_permissions": ["guild_id", "command_name"],
    "roles": ["guild_id", "role_id"],
    "user_cache": ["user_id"],
    "channel_cache": ["channel_id"],
    "ticket_settings": ["guild_id"],
    "log_settings": ["guild_id"],
    "db_log_settings": ["guild_id"],
    "level_settings": ["guild_id"],
    "levels": ["user_id", "guild_id"],
    "saved_roles": ["user_id", "guild_id", "role_id"],
    "temp_bans": ["guild_id", "user_id"],
    "eco_bans": ["user_id", "guild_id"],
    "level_ignores": ["guild_id", "channel_id"],
    "user_current_roles": ["guild_id", "user_id", "role_id"],
}

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
        
        load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
        load_dotenv()
        
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        dsn = os.getenv("DB_DSN")
        
        # Sadece thin mode ile bağlan
        try:
            self.pool = oracledb.create_pool_async(
                user=user,
                password=password,
                dsn=dsn,
                min=2,
                max=20,
                increment=2,
                config_dir=WALLET_DIR,
                wallet_location=WALLET_DIR,
                wallet_password=password
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
        SQLite sorgularını Oracle uyumlu hale getirir:
        - '?' -> ':1, :2'
        - 'LIMIT 1' -> 'FETCH FIRST 1 ROWS ONLY'
        - 'INSERT OR REPLACE INTO' -> 'MERGE INTO'
        - 'INSERT OR IGNORE INTO' -> 'BEGIN INSERT ... EXCEPTION WHEN DUP_VAL_ON_INDEX THEN NULL; END;'
        - 'ON CONFLICT DO UPDATE SET' -> 'MERGE INTO'
        - 'level' sütununu "LEVEL" olarak tırnaklar.
        """
        # LIMIT 1 -> FETCH FIRST 1 ROWS ONLY
        if "LIMIT 1" in query.upper():
            query = re.sub(r'(?i)\bLIMIT\s+1\b', 'FETCH FIRST 1 ROWS ONLY', query)
        
        # INSERT OR REPLACE INTO -> MERGE INTO
        if "INSERT OR REPLACE INTO" in query.upper():
            match = re.search(r'(?is)INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)', query)
            if match:
                table = match.group(1).strip()
                cols = [c.strip() for c in match.group(2).split(',')]
                vals = [v.strip() for v in match.group(3).split(',')]
                
                pk_cols = TABLE_PRIMARY_KEYS.get(table.lower(), [cols[0]])
                upd_cols = [c for c in cols if c.lower() not in [pk.lower() for pk in pk_cols]]
                
                using_cols = [f"{v} as {c}" for c, v in zip(cols, vals)]
                using_str = "SELECT " + ", ".join(using_cols) + " FROM DUAL"
                
                on_cond = " AND ".join(f"t.{pk} = s.{pk}" for pk in pk_cols)
                matched_clause = f"WHEN MATCHED THEN UPDATE SET {', '.join(f't.{c} = s.{c}' for c in upd_cols)}" if upd_cols else ""
                
                query = f"""
                MERGE INTO {table} t
                USING ({using_str}) s
                ON ({on_cond})
                {matched_clause}
                WHEN NOT MATCHED THEN INSERT ({', '.join(cols)}) VALUES ({', '.join('s.'+c for c in cols)})
                """

        # INSERT OR IGNORE -> PL/SQL blok
        elif "INSERT OR IGNORE" in query.upper():
            query = re.sub(r'(?is)INSERT\s+OR\s+IGNORE\s+INTO\s+(.*?)(?:;|\s*$)', r'BEGIN INSERT INTO \1; EXCEPTION WHEN DUP_VAL_ON_INDEX THEN NULL; END;', query)

        # ON CONFLICT DO UPDATE SET -> MERGE INTO
        elif "ON CONFLICT" in query.upper():
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

        # Oracle'da LEVEL reserved word olduğu için sorgulardaki level kelimesini "LEVEL" yap
        query = re.sub(r'(?i)\blevel\b', '"LEVEL"', query)
        
        # ? -> :1, :2, :3
        counter = itertools.count(1)
        return re.sub(r'\?', lambda _: f":{next(counter)}", query)

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

    async def sync_user_roles_bulk(self, guild_id: str, data: list) -> None:
        """
        Kullanıcıların anlık rollerini toplu olarak günceller.
        data = [(guild_id, user_id, role_id, role_name), ...]
        """
        try:
            await self.execute("DELETE FROM user_current_roles WHERE guild_id=?", str(guild_id))
            await self.executemany(
                "INSERT INTO user_current_roles (guild_id, user_id, role_id, role_name) VALUES (?, ?, ?, ?)",
                data
            )
        except Exception as e:
            log.error(f"sync_user_roles_bulk hatası: {e}")

    async def add_user_role(self, guild_id: str, user_id: str, role_id: str, role_name: str) -> None:
        try:
            await self.execute(
                "INSERT OR IGNORE INTO user_current_roles (guild_id, user_id, role_id, role_name) VALUES (?, ?, ?, ?)",
                str(guild_id), str(user_id), str(role_id), role_name
            )
        except Exception as e:
            log.error(f"add_user_role hatası: {e}")

    async def remove_user_role(self, guild_id: str, user_id: str, role_id: str) -> None:
        try:
            await self.execute(
                "DELETE FROM user_current_roles WHERE guild_id=? AND user_id=? AND role_id=?",
                str(guild_id), str(user_id), str(role_id)
            )
        except Exception as e:
            log.error(f"remove_user_role hatası: {e}")

    async def clear_user_roles(self, guild_id: str, user_id: str) -> None:
        try:
            await self.execute(
                "DELETE FROM user_current_roles WHERE guild_id=? AND user_id=?",
                str(guild_id), str(user_id)
            )
        except Exception as e:
            log.error(f"clear_user_roles hatası: {e}")

    async def fetch_admin_events(
        self, guild_id: int, target_id: int | None = None, limit: int = 10
    ) -> list[dict]:
        """Bir sunucunun mod eylem geçmişini döndür, isteğe bağlı hedef filtresi ile."""
        if target_id:
            return await self.fetchall(
                f"""
                SELECT * FROM admin_events
                WHERE guild_id = ? AND target_id = ?
                ORDER BY timestamp DESC FETCH FIRST {limit} ROWS ONLY
                """,
                str(guild_id), str(target_id)
            )
        else:
            return await self.fetchall(
                f"""
                SELECT * FROM admin_events
                WHERE guild_id = ?
                ORDER BY timestamp DESC FETCH FIRST {limit} ROWS ONLY
                """,
                str(guild_id)
            )

