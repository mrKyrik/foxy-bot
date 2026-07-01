"""
core/database.py
----------------
İki ayrı SQLite veritabanı için async wrapper.

  • USER-DB.db   → Kullanıcı/sunucu verileri (roller, izinler, ekonomi, XP, ...)
  • ADMIN-EVENTS.db → Moderasyon eylem logu

Her iki DB de aiosqlite üzerinden async çalışır; bot event loop'unu bloklamamak
için tüm sorgu metodları `await` ile çağrılmalıdır.

Kullanım:
    # main.py'de:
    bot.db = Database()
    await bot.db.init()

    # Bir cog içinde:
    row = await ctx.bot.db.fetchone("SELECT wallet FROM economy WHERE user_id=? AND guild_id=?", user_id, guild_id)
"""

import logging
import os
import aiosqlite

log = logging.getLogger(__name__)

USER_DB_PATH = "Data/USER-DB.db"
ADMIN_DB_PATH = "Data/ADMIN-EVENTS.db"

# ---------------------------------------------------------------------------
# Schema — USER-DB.db
# ---------------------------------------------------------------------------
USER_DB_SCHEMA = """
-- Sunucu bazlı bot ayarları
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id        TEXT PRIMARY KEY,
    prefix          TEXT    DEFAULT 'f.',
    log_channel     TEXT,
    welcome_channel TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Bot içi rol kaydı (izin sistemi için)
CREATE TABLE IF NOT EXISTS roles (
    guild_id  TEXT,
    role_id   TEXT,
    role_name TEXT,
    PRIMARY KEY (guild_id, role_id)
);

-- Rol bazlı komut izinleri
CREATE TABLE IF NOT EXISTS role_permissions (
    guild_id        TEXT,
    role_id         TEXT,
    permission_name TEXT,
    PRIMARY KEY (guild_id, role_id, permission_name)
);

-- Kullanıcı uyarı kayıtları
CREATE TABLE IF NOT EXISTS warns (
    warn_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id  TEXT    NOT NULL,
    user_id   TEXT    NOT NULL,
    mod_id    TEXT    NOT NULL,
    reason    TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Ekonomi cüzdan/banka
CREATE TABLE IF NOT EXISTS economy (
    user_id         TEXT,
    guild_id        TEXT,
    wallet          INTEGER DEFAULT 200,
    bank            INTEGER DEFAULT 0,
    daily_cooldown  REAL    DEFAULT 0.0,
    work_cooldown   REAL    DEFAULT 0.0,
    fish_cooldown   REAL    DEFAULT 0.0,
    hunt_cooldown   REAL    DEFAULT 0.0,
    mine_cooldown   REAL    DEFAULT 0.0,
    rob_cooldown    REAL    DEFAULT 0.0,
    padlock_active  INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

-- Economy extras: evlilik, çiftçilik, özel başlık
CREATE TABLE IF NOT EXISTS economy_extras (
    user_id            TEXT,
    guild_id           TEXT,
    married_to         TEXT,
    farm_crop          TEXT,
    farm_time          REAL    DEFAULT 0.0,
    farm_watered       INTEGER DEFAULT 0,
    custom_title_text  TEXT,
    last_message_time  REAL    DEFAULT 0.0,
    PRIMARY KEY (user_id, guild_id)
);

-- Kullanıcı envanteri
CREATE TABLE IF NOT EXISTS inventory (
    user_id  TEXT,
    guild_id TEXT,
    item_id  TEXT,
    quantity INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, guild_id, item_id)
);

-- XP / Seviye sistemi
CREATE TABLE IF NOT EXISTS levels (
    user_id       TEXT,
    guild_id      TEXT,
    xp            INTEGER DEFAULT 0,
    level         INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

-- Sunucu terk eden üyelerin rollerini sakla
CREATE TABLE IF NOT EXISTS saved_roles (
    user_id  TEXT,
    guild_id TEXT,
    role_id  TEXT,
    PRIMARY KEY (user_id, guild_id, role_id)
);

-- Global bot yasakları (bot genelinde)
CREATE TABLE IF NOT EXISTS bot_bans (
    user_id    TEXT PRIMARY KEY,
    reason     TEXT,
    banned_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Ekonomi yasakları (sunucu bazlı)
CREATE TABLE IF NOT EXISTS eco_bans (
    user_id   TEXT,
    guild_id  TEXT,
    reason    TEXT,
    banned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, guild_id)
);

-- Seviye ödül rolleri
CREATE TABLE IF NOT EXISTS level_rewards (
    guild_id TEXT,
    level    INTEGER,
    role_id  TEXT,
    PRIMARY KEY (guild_id, level)
);

-- XP kazanılmayan (ignore) kanallar
CREATE TABLE IF NOT EXISTS level_ignores (
    guild_id   TEXT,
    channel_id TEXT,
    PRIMARY KEY (guild_id, channel_id)
);

-- Özel Formlar
CREATE TABLE IF NOT EXISTS custom_forms (
    form_id     TEXT PRIMARY KEY,
    guild_id    TEXT NOT NULL,
    title       TEXT NOT NULL,
    channel_id  TEXT NOT NULL,
    form_type   INTEGER DEFAULT 1,
    action_target TEXT
);

CREATE TABLE IF NOT EXISTS form_questions (
    question_id INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id     TEXT NOT NULL,
    question_text TEXT NOT NULL,
    FOREIGN KEY (form_id) REFERENCES custom_forms(form_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS form_roles (
    action_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id     TEXT NOT NULL,
    role_id     TEXT NOT NULL,
    FOREIGN KEY (form_id) REFERENCES custom_forms(form_id) ON DELETE CASCADE
);

-- Geçiçi Yasaklamalar
CREATE TABLE IF NOT EXISTS temp_bans (
    guild_id        TEXT,
    user_id         TEXT,
    unban_timestamp REAL,
    PRIMARY KEY (guild_id, user_id)
);

-- Öneriler
CREATE TABLE IF NOT EXISTS suggestions (
    suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id      TEXT,
    author_id     TEXT,
    text          TEXT,
    status        TEXT DEFAULT 'pending',
    message_id    TEXT,
    reason        TEXT
);

-- Öneri Panosu Ayarları
CREATE TABLE IF NOT EXISTS suggestion_config (
    guild_id   TEXT PRIMARY KEY,
    channel_id TEXT
);

-- Ragebait Puanları
CREATE TABLE IF NOT EXISTS ragepoints (
    guild_id TEXT,
    user_id  TEXT,
    points   INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

-- Master Log Ayarları (Discord'a gönderilen logların kanal ayarları)
CREATE TABLE IF NOT EXISTS log_settings (
    guild_id        TEXT PRIMARY KEY,
    msg_channel     TEXT,
    msg_delete_on   INTEGER DEFAULT 1,
    msg_edit_on     INTEGER DEFAULT 1,
    ses_channel     TEXT,
    ses_join_on     INTEGER DEFAULT 1,
    ses_switch_on   INTEGER DEFAULT 1,
    ses_stream_on   INTEGER DEFAULT 1,
    uyari_channel   TEXT,
    ticket_channel  TEXT,
    mod_channel     TEXT,
    mod_role_on     INTEGER DEFAULT 1,
    mod_channel_on  INTEGER DEFAULT 1,
    mod_msg_on      INTEGER DEFAULT 1,
    basvuru_channel TEXT,
    davet_channel   TEXT,
    sunucu_channel  TEXT,
    srv_update_on   INTEGER DEFAULT 1,
    srv_emoji_on    INTEGER DEFAULT 1,
    srv_role_on     INTEGER DEFAULT 1,
    srv_perm_on     INTEGER DEFAULT 1,
    rol_channel     TEXT
);

-- Veritabanı / Dashboard loglama şalterleri (Web UI üzerinden yönetilir)
CREATE TABLE IF NOT EXISTS db_log_settings (
    guild_id         TEXT PRIMARY KEY,
    msg_delete_on    INTEGER DEFAULT 1,
    msg_edit_on      INTEGER DEFAULT 1,
    ses_join_on      INTEGER DEFAULT 1,
    ses_switch_on    INTEGER DEFAULT 1,
    ses_stream_on    INTEGER DEFAULT 1,
    ses_camera_on    INTEGER DEFAULT 1,
    mod_role_on      INTEGER DEFAULT 1,
    mod_channel_on   INTEGER DEFAULT 1,
    mod_msg_on       INTEGER DEFAULT 1,
    srv_update_on    INTEGER DEFAULT 1,
    srv_emoji_on     INTEGER DEFAULT 1,
    srv_role_on      INTEGER DEFAULT 1,
    srv_perm_on      INTEGER DEFAULT 1,
    warn_add_on      INTEGER DEFAULT 1,
    warn_remove_on   INTEGER DEFAULT 1,
    ticket_create_on INTEGER DEFAULT 1,
    ticket_close_on  INTEGER DEFAULT 1,
    app_create_on    INTEGER DEFAULT 1,
    app_accept_on    INTEGER DEFAULT 1,
    app_reject_on    INTEGER DEFAULT 1,
    invite_create_on INTEGER DEFAULT 1,
    invite_use_on    INTEGER DEFAULT 1,
    role_add_on      INTEGER DEFAULT 1,
    role_remove_on   INTEGER DEFAULT 1
);

-- Genel Olay Logları (JSON Formatlı)
CREATE TABLE IF NOT EXISTS db_event_logs (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    TEXT    NOT NULL,
    event_type  TEXT    NOT NULL,
    user_id     TEXT,
    details     TEXT,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
    channel_id  TEXT
);

-- Önbellek Tabloları (Web UI için)
CREATE TABLE IF NOT EXISTS user_cache (
    user_id     TEXT PRIMARY KEY,
    username    TEXT,
    avatar_url  TEXT,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Kanal önbelleği (Web UI için)
CREATE TABLE IF NOT EXISTS channel_cache (
    channel_id   TEXT PRIMARY KEY,
    channel_name TEXT,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index Optimizasyonları
CREATE INDEX IF NOT EXISTS idx_warns_guild_user ON warns(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_economy_guild ON economy(guild_id);
CREATE INDEX IF NOT EXISTS idx_levels_guild ON levels(guild_id);
"""

# ---------------------------------------------------------------------------
# Schema — ADMIN-EVENTS.db
# ---------------------------------------------------------------------------
ADMIN_DB_SCHEMA = """
-- Moderasyon eylem logu
CREATE TABLE IF NOT EXISTS admin_events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    TEXT    NOT NULL,
    admin_id    TEXT    NOT NULL,
    action_type TEXT    NOT NULL,
    target_id   TEXT    NOT NULL,
    reason      TEXT,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index Optimizasyonları
CREATE INDEX IF NOT EXISTS idx_admin_events_guild_target ON admin_events(guild_id, target_id);
"""


class Database:
    """
    İki SQLite veritabanını yöneten async bağlantı wrapper'ı.

    Attributes:
        user_db:  USER-DB.db için aiosqlite.Connection
        admin_db: ADMIN-EVENTS.db için aiosqlite.Connection
    """

    def __init__(
        self,
        user_db_path: str = USER_DB_PATH,
        admin_db_path: str = ADMIN_DB_PATH,
    ) -> None:
        self._user_db_path = user_db_path
        self._admin_db_path = admin_db_path
        self.user_db: aiosqlite.Connection | None = None
        self.admin_db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        """Bağlantıları aç ve tabloları oluştur."""
        os.makedirs("Data", exist_ok=True)

        self.user_db = await aiosqlite.connect(self._user_db_path)
        self.user_db.row_factory = aiosqlite.Row  # sütun isimleriyle erişim
        
        # WAL ve Foreign Key modunu aktif et
        await self.user_db.execute("PRAGMA journal_mode=WAL;")
        await self.user_db.execute("PRAGMA synchronous=NORMAL;")
        await self.user_db.execute("PRAGMA foreign_keys=ON;")
        
        # Migration: saved_roles
        cursor = await self.user_db.execute("PRAGMA table_info(saved_roles)")
        columns = [row["name"] for row in await cursor.fetchall()]
        if "role_ids" in columns:
            log.info("Migrating saved_roles JSON to relational...")
            old_roles = await self.user_db.execute("SELECT user_id, guild_id, role_ids FROM saved_roles")
            old_data = await old_roles.fetchall()
            await self.user_db.execute("DROP TABLE saved_roles")
            await self.user_db.executescript(USER_DB_SCHEMA)
            
            import json
            for r in old_data:
                try:
                    r_ids = json.loads(r["role_ids"])
                    for rid in r_ids:
                        await self.user_db.execute("INSERT OR IGNORE INTO saved_roles (user_id, guild_id, role_id) VALUES (?, ?, ?)", (r["user_id"], r["guild_id"], str(rid)))
                except Exception: pass
        
        # Migration: custom_forms
        cursor = await self.user_db.execute("PRAGMA table_info(custom_forms)")
        columns = [row["name"] for row in await cursor.fetchall()]
        if "questions" in columns:
            log.info("Migrating custom_forms JSON to relational...")
            old_forms = await self.user_db.execute("SELECT * FROM custom_forms")
            old_form_data = await old_forms.fetchall()
            await self.user_db.execute("DROP TABLE custom_forms")
            await self.user_db.executescript(USER_DB_SCHEMA)
            
            import json
            for row in old_form_data:
                f = dict(row)
                a_data = {}
                try: a_data = json.loads(f.get("action_data", "{}"))
                except Exception: pass
                
                action_tgt = a_data.get("publish_channel_id", None)
                
                await self.user_db.execute(
                    "INSERT INTO custom_forms (form_id, guild_id, title, channel_id, form_type, action_target) VALUES (?, ?, ?, ?, ?, ?)", 
                    (f["form_id"], f["guild_id"], f["title"], f["channel_id"], f.get("form_type", 1), action_tgt)
                )
                try:
                    q_list = json.loads(f["questions"])
                    for q in q_list:
                        await self.user_db.execute("INSERT INTO form_questions (form_id, question_text) VALUES (?, ?)", (f["form_id"], q["label"]))
                except Exception: pass
                try:
                    for rid in a_data.get("role_ids", []):
                        await self.user_db.execute("INSERT INTO form_roles (form_id, role_id) VALUES (?, ?)", (f["form_id"], str(rid)))
                except Exception: pass
        else:
            await self.user_db.executescript(USER_DB_SCHEMA)

        await self.user_db.commit()

        self.admin_db = await aiosqlite.connect(self._admin_db_path)
        self.admin_db.row_factory = aiosqlite.Row
        
        # WAL modunu aktif et
        await self.admin_db.execute("PRAGMA journal_mode=WAL;")
        await self.admin_db.execute("PRAGMA synchronous=NORMAL;")
        
        await self.admin_db.executescript(ADMIN_DB_SCHEMA)
        await self.admin_db.commit()

        log.info("Veritabanları başlatıldı: %s, %s", self._user_db_path, self._admin_db_path)

    async def close(self) -> None:
        """Bot kapanırken bağlantıları temizle."""
        if self.user_db:
            await self.user_db.close()
        if self.admin_db:
            await self.admin_db.close()
        log.info("Veritabanı bağlantıları kapatıldı.")

    # ------------------------------------------------------------------
    # USER-DB helpers
    # ------------------------------------------------------------------

    async def execute(self, query: str, *args) -> None:
        """USER-DB'de INSERT/UPDATE/DELETE çalıştır ve commit et."""
        async with self.user_db.execute(query, args) as _:
            pass
        await self.user_db.commit()

    async def fetchone(self, query: str, *args) -> aiosqlite.Row | None:
        """USER-DB'den tek satır döndür."""
        async with self.user_db.execute(query, args) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, query: str, *args) -> list[aiosqlite.Row]:
        """USER-DB'den tüm satırları döndür."""
        async with self.user_db.execute(query, args) as cursor:
            return await cursor.fetchall()

    async def executemany(self, query: str, data: list) -> None:
        """USER-DB'de toplu INSERT/UPDATE."""
        await self.user_db.executemany(query, data)
        await self.user_db.commit()

    # ------------------------------------------------------------------
    # ADMIN-DB helpers
    # ------------------------------------------------------------------

    async def log_admin_event(
        self,
        guild_id: int,
        admin_id: int,
        action_type: str,
        target_id: int,
        reason: str = "Belirtilmedi",
    ) -> None:
        """
        Moderasyon eylemini hem Python logging'e hem ADMIN-EVENTS.db'ye yaz.

        Args:
            guild_id:    Sunucu ID'si
            admin_id:    Komutu kullanan moderatör/admin ID'si
            action_type: Eylem türü (örn. "KICK", "BAN", "TIMEOUT")
            target_id:   Hedef kullanıcı/kanal ID'si
            reason:      Eylem gerekçesi
        """
        # 1) Python logging (discord.log dosyasına gider)
        log.info(
            "ADMIN ACTION | guild=%s | %s | admin=%s | target=%s | reason=%s",
            guild_id,
            action_type,
            admin_id,
            target_id,
            reason,
        )

        # 2) ADMIN-EVENTS.db
        await self.admin_db.execute(
            """
            INSERT INTO admin_events (guild_id, admin_id, action_type, target_id, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(guild_id), str(admin_id), action_type, str(target_id), reason),
        )
        await self.admin_db.commit()

    async def log_db_event(
        self,
        guild_id,
        event_type,
        setting_key,
        user_id,
        details,
        channel_id=None
    ) -> None:
        """
        USER-DB.db içerisindeki db_event_logs tablosuna genel log atar.
        details argümanı dict ise otomatik JSON'a çevrilir.

        Args:
            guild_id:    Sunucu ID'si
            event_type:  Olay türü (örn. 'msg_delete', 'ses_join')
            setting_key: db_log_settings tablosundaki ilgili şalter kolonu (None ise her zaman yaz)
            user_id:     Olayı tetikleyen kullanıcı ID'si
            details:     Detay bilgisi (dict ise JSON'a çevrilir)
            channel_id:  İlgili kanal ID'si
        """
        # Şalter kontrolü: yalnızca db_log_settings tablosuna bak
        if setting_key:
            try:
                row = await self.fetchone(
                    "SELECT * FROM db_log_settings WHERE guild_id=?", str(guild_id)
                )
                if row:
                    row_dict = dict(row)
                    # Şalter kolonu tabloda var ve 0 ise loglama
                    if setting_key in row_dict and row_dict[setting_key] == 0:
                        return
                # Kayıt yoksa → tablo henüz oluşturulmamış → varsayılan açık (logla)
            except Exception as e:
                log.error("log_db_event ayar kontrol hatası: %s", e)

        import json
        details_str = json.dumps(details, ensure_ascii=False) if isinstance(details, dict) else str(details)

        try:
            await self.user_db.execute(
                """
                INSERT INTO db_event_logs (guild_id, event_type, user_id, details, channel_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(guild_id),
                    event_type,
                    str(user_id) if user_id else None,
                    details_str,
                    str(channel_id) if channel_id else None,
                )
            )
            await self.user_db.commit()
        except Exception as e:
            log.error("log_db_event hatası: %s", e)

    async def log_db_events_bulk(self, events: list) -> None:
        """
        USER-DB.db içerisindeki db_event_logs tablosuna TOPLU (bulk) log atar.
        Performans için executemany kullanır.
        
        events formatı: [(guild_id, event_type, user_id, details, channel_id), ...]
        Not: setting_key'i optimize etmek için fonksiyon dışında kontrol ettiğinizi varsayar. 
        Eğer setting_key kontrolü lazımsa fonksiyon dışında yapıp sadece loglanacak olanları buraya gönderin.
        """
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
            await self.user_db.executemany(
                """
                INSERT INTO db_event_logs (guild_id, event_type, user_id, details, channel_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                insert_data
            )
            await self.user_db.commit()
        except Exception as e:
            log.error(f"log_db_events_bulk hatası: {e}")

    async def update_user_cache(self, user_id: str, username: str, avatar_url: str | None) -> None:
        """Kullanıcı adını ve avatarını önbelleğe alır."""
        try:
            await self.user_db.execute(
                """
                INSERT INTO user_cache (user_id, username, avatar_url)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    avatar_url=excluded.avatar_url
                """,
                (str(user_id), username, avatar_url)
            )
            await self.user_db.commit()
        except Exception as e:
            log.error(f"update_user_cache hatası: {e}")

    async def update_channel_cache(self, channel_id: str, channel_name: str) -> None:
        """Kanal adını önbelleğe alır."""
        try:
            await self.user_db.execute(
                """
                INSERT INTO channel_cache (channel_id, channel_name)
                VALUES (?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    channel_name=excluded.channel_name
                """,
                (str(channel_id), channel_name)
            )
            await self.user_db.commit()
        except Exception as e:
            log.error(f"update_channel_cache hatası: {e}")

    async def update_role_cache(self, guild_id: str, role_id: str, role_name: str) -> None:
        """Rol adını önbelleğe alır."""
        try:
            await self.user_db.execute(
                """
                INSERT INTO roles (guild_id, role_id, role_name)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, role_id) DO UPDATE SET
                    role_name=excluded.role_name
                """,
                (str(guild_id), str(role_id), role_name)
            )
            await self.user_db.commit()
        except Exception as e:
            log.error(f"update_role_cache hatası: {e}")

    async def fetch_admin_events(
        self, guild_id: int, target_id: int | None = None, limit: int = 10
    ) -> list[aiosqlite.Row]:
        """Bir sunucunun mod eylem geçmişini döndür, isteğe bağlı hedef filtresi ile."""
        if target_id:
            async with self.admin_db.execute(
                """
                SELECT * FROM admin_events
                WHERE guild_id=? AND target_id=?
                ORDER BY timestamp DESC LIMIT ?
                """,
                (str(guild_id), str(target_id), limit),
            ) as cursor:
                return await cursor.fetchall()
        else:
            async with self.admin_db.execute(
                """
                SELECT * FROM admin_events
                WHERE guild_id=?
                ORDER BY timestamp DESC LIMIT ?
                """,
                (str(guild_id), limit),
            ) as cursor:
                return await cursor.fetchall()
