import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Kumiho Log Dashboard API")

# İzin verilen originler
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # CRA / alternatif
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Veritabanı yolları
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
USER_DB_PATH = os.path.join(BASE_DIR, "Data", "USER-DB.db")
ADMIN_DB_PATH = os.path.join(BASE_DIR, "Data", "ADMIN-EVENTS.db")
MAIN_DB_PATH = os.path.join(BASE_DIR, "kumiho.db")

# Kanal kolonu whitelist — güvenlik için sabit liste
CHANNEL_COLUMNS = [
    "msg_channel", "ses_channel", "mod_channel", "uyari_channel",
    "ticket_channel", "basvuru_channel", "davet_channel", "sunucu_channel", "rol_channel"
]

TOGGLE_COLUMNS = [
    "msg_delete_on", "msg_edit_on", "ses_join_on", "ses_switch_on", "ses_stream_on", "ses_camera_on",
    "mod_role_on", "mod_channel_on", "mod_msg_on",
    "srv_update_on", "srv_emoji_on", "srv_role_on", "srv_perm_on",
    "warn_add_on", "warn_remove_on", "ticket_create_on", "ticket_close_on",
    "app_create_on", "app_accept_on", "app_reject_on", "invite_create_on", "invite_use_on",
    "role_add_on", "role_remove_on"
]


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db_connection(db_path):
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    return conn

def init_db():
    conn = sqlite3.connect(MAIN_DB_PATH)
    c = conn.cursor()
    # admin_notes tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS admin_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        note TEXT NOT NULL,
        added_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # command_permissions tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS command_permissions (
        guild_id TEXT NOT NULL,
        command_name TEXT NOT NULL,
        is_enabled INTEGER DEFAULT 1,
        allowed_roles TEXT DEFAULT '[]',
        PRIMARY KEY (guild_id, command_name)
    )''')
    # pending_actions tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS pending_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT NOT NULL,
        target_user_id TEXT NOT NULL,
        action_type TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

# Uygulama başlarken db'yi init edelim
init_db()


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

@app.get("/api/logs/{guild_id}")
def get_guild_logs(guild_id: str, limit: int = 2000, start_time: int = None, end_time: int = None):
    """
    Belirli bir sunucunun tüm loglarını db_event_logs ve admin_events
    tablolarından çeker ve zaman damgasına göre sıralı olarak birleştirir.
    """
    logs = []

    # Tarih filtresi
    date_filter_user = ""
    date_filter_admin = ""
    params_user = [guild_id]
    params_admin = [guild_id]

    if start_time and end_time:
        import datetime
        start_dt = datetime.datetime.fromtimestamp(start_time / 1000.0, tz=datetime.timezone.utc)
        end_dt = datetime.datetime.fromtimestamp(end_time / 1000.0, tz=datetime.timezone.utc)

        start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_dt.strftime('%Y-%m-%d %H:%M:%S')

        date_filter_user = "AND e.timestamp >= ? AND e.timestamp <= ?"
        date_filter_admin = "AND timestamp >= ? AND timestamp <= ?"

        params_user.extend([start_str, end_str])
        params_admin.extend([start_str, end_str])
        limit = 50000

    params_user.append(limit)
    params_admin.append(limit)

    # 1. USER-DB.db → db_event_logs
    user_conn = get_db_connection(USER_DB_PATH)
    if user_conn:
        try:
            cursor = user_conn.cursor()
            query = f"""
            SELECT
                e.log_id as id,
                'general' as source,
                e.event_type,
                e.user_id,
                e.details,
                e.timestamp,
                e.channel_id,
                u.username,
                u.avatar_url,
                c.channel_name,
                r.role_name
            FROM db_event_logs e
            LEFT JOIN user_cache u ON e.user_id = u.user_id
            LEFT JOIN channel_cache c ON e.channel_id = c.channel_id
            LEFT JOIN roles r ON e.channel_id = r.role_id AND e.guild_id = r.guild_id
            WHERE e.guild_id = ? {date_filter_user}
            ORDER BY e.timestamp DESC LIMIT ?
        """
            cursor.execute(query, tuple(params_user))
            rows = cursor.fetchall()
            import json
            for r in rows:
                r_dict = dict(r)
                try:
                    details_obj = json.loads(r_dict["details"])
                    r_dict["details_obj"] = details_obj
                    if "text" in details_obj:
                        r_dict["details"] = details_obj["text"]
                except Exception:
                    r_dict["details_obj"] = None
                logs.append(r_dict)
        except Exception as e:
            print("USER-DB okuma hatası:", e)
        finally:
            user_conn.close()

    # 2. ADMIN-EVENTS.db → admin_events
    admin_conn = get_db_connection(ADMIN_DB_PATH)
    if admin_conn:
        try:
            cursor = admin_conn.cursor()
            cursor.execute(f"ATTACH DATABASE '{USER_DB_PATH}' AS userdb")
            query = f"""
                SELECT
                    e.event_id as id,
                    'admin' as source,
                    e.action_type as event_type,
                    e.admin_id as user_id,
                    e.admin_id as admin_id,
                    e.reason as details,
                    e.timestamp,
                    e.target_id as channel_id,
                    u.username,
                    u.avatar_url,
                    COALESCE(t_u.username, t_c.channel_name, t_r.role_name, e.target_id) as target_name,
                    NULL as channel_name,
                    NULL as role_name
                FROM admin_events e
                LEFT JOIN userdb.user_cache u ON e.admin_id = u.user_id
                LEFT JOIN userdb.user_cache t_u ON e.target_id = t_u.user_id
                LEFT JOIN userdb.channel_cache t_c ON e.target_id = t_c.channel_id
                LEFT JOIN userdb.roles t_r ON e.target_id = t_r.role_id
                WHERE e.guild_id = ? {date_filter_admin}
                ORDER BY e.timestamp DESC LIMIT ?
            """
            cursor.execute(query, tuple(params_admin))

            admin_logs = cursor.fetchall()
            for al in admin_logs:
                al_dict = dict(al)
                target = al_dict.pop('target_name')
                reason = al_dict['details']
                al_dict["details"] = f"Hedef: {target} | Sebep: {reason}"
                al_dict["details_obj"] = None
                logs.append(al_dict)
        except Exception as e:
            print("ADMIN-EVENTS okuma hatası:", e)
        finally:
            admin_conn.close()

    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"guild_id": guild_id, "logs": logs[:limit]}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@app.get("/api/stats/{guild_id}")
def get_guild_stats(guild_id: str):
    """Dashboard için temel istatistikleri döndürür."""
    stats = {
        "total_events": 0,
        "admin_actions": 0,
        "voice_events": 0
    }

    user_conn = get_db_connection(USER_DB_PATH)
    if user_conn:
        try:
            c = user_conn.cursor()
            c.execute("SELECT COUNT(*) as c FROM db_event_logs WHERE guild_id = ?", (guild_id,))
            stats["total_events"] = c.fetchone()["c"]

            c.execute(
                "SELECT COUNT(*) as c FROM db_event_logs WHERE guild_id = ? AND (event_type LIKE 'voice_%' OR event_type LIKE 'ses_%')",
                (guild_id,)
            )
            stats["voice_events"] = c.fetchone()["c"]
        except Exception:
            pass
        finally:
            user_conn.close()

    admin_conn = get_db_connection(ADMIN_DB_PATH)
    if admin_conn:
        try:
            c = admin_conn.cursor()
            c.execute("SELECT COUNT(*) as c FROM admin_events WHERE guild_id = ?", (guild_id,))
            stats["admin_actions"] = c.fetchone()["c"]
        except Exception:
            pass
        finally:
            admin_conn.close()

    stats["total_events"] += stats["admin_actions"]
    return stats


# ---------------------------------------------------------------------------
# Channels  [YENİ]
# ---------------------------------------------------------------------------

@app.get("/api/channels/{guild_id}")
def get_channels(guild_id: str):
    """
    channel_cache tablosundan sunucudaki tüm kanalları döndürür.
    DiscordSettings dropdown'ı bu listeyi kullanır.
    Bot çevrimiçi değilse veya henüz kanal cache'lenmemişse boş liste döner.
    """
    channels = []
    user_conn = get_db_connection(USER_DB_PATH)
    if user_conn:
        try:
            c = user_conn.cursor()
            c.execute(
                "SELECT channel_id, channel_name FROM channel_cache ORDER BY channel_name ASC"
            )
            channels = c.fetchall()
        except Exception as e:
            print("Kanallar okunamadı:", e)
        finally:
            user_conn.close()
    return {"guild_id": guild_id, "channels": channels}


# ---------------------------------------------------------------------------
# Settings — Toggles + Channels
# ---------------------------------------------------------------------------

class LogSettingsUpdate(BaseModel):
    setting_name: str
    state: str  # 'on' or 'off'


class ChannelSettingUpdate(BaseModel):
    column: str          # örn. "msg_channel"
    channel_id: Optional[str] = None  # None → kanalı temizle


@app.get("/api/settings/{guild_id}")
def get_log_settings(guild_id: str):
    """
    Belirli bir sunucunun şalter (db_log_settings) ve
    Discord kanal (log_settings) ayarlarını birlikte döndürür.
    """
    settings = {}
    channels = {}

    user_conn = get_db_connection(USER_DB_PATH)
    if user_conn:
        try:
            c = user_conn.cursor()

            # 1) ON/OFF şalterleri — db_log_settings
            c.execute("SELECT * FROM db_log_settings WHERE guild_id = ?", (guild_id,))
            row_db = c.fetchone() or {}
            for tk in TOGGLE_COLUMNS:
                val = row_db.get(tk)
                settings[tk] = "on" if val == 1 else "off"

            # 2) Discord kanal seçimleri — log_settings
            c.execute("SELECT * FROM log_settings WHERE guild_id = ?", (guild_id,))
            row_ls = c.fetchone() or {}
            for ck in CHANNEL_COLUMNS:
                channels[ck] = row_ls.get(ck)  # None ise kanal seçilmemiş

        except Exception as e:
            print("Settings okuma hatası:", e)
        finally:
            user_conn.close()

    return {"guild_id": guild_id, "settings": settings, "channels": channels}


@app.post("/api/settings/{guild_id}")
def update_log_setting(guild_id: str, update: LogSettingsUpdate):
    """ON/OFF şalteri günceller — db_log_settings tablosuna yazar."""
    if update.setting_name not in TOGGLE_COLUMNS:
        raise HTTPException(status_code=400, detail="Geçersiz ayar sütunu")

    user_conn = get_db_connection(USER_DB_PATH)
    if not user_conn:
        raise HTTPException(status_code=500, detail="Veritabanına bağlanılamadı")

    try:
        c = user_conn.cursor()
        val = 1 if update.state.lower() == "on" else 0
        c.execute("INSERT OR IGNORE INTO db_log_settings (guild_id) VALUES (?)", (guild_id,))
        c.execute(
            f"UPDATE db_log_settings SET {update.setting_name} = ? WHERE guild_id = ?",
            (val, guild_id)
        )
        user_conn.commit()
        return {"status": "success", "setting": update.setting_name, "state": update.state}
    except Exception as e:
        print("Settings yazma hatası:", e)
        raise HTTPException(status_code=500, detail="Ayar kaydedilemedi")
    finally:
        user_conn.close()


@app.post("/api/channel-setting/{guild_id}")
def update_channel_setting(guild_id: str, update: ChannelSettingUpdate):
    """
    Discord log kanalını günceller — log_settings tablosuna yazar.
    channel_id = None ise kanal seçimi temizlenir.
    """
    if update.column not in CHANNEL_COLUMNS:
        raise HTTPException(status_code=400, detail="Geçersiz kanal kolonu")

    user_conn = get_db_connection(USER_DB_PATH)
    if not user_conn:
        raise HTTPException(status_code=500, detail="Veritabanına bağlanılamadı")

    try:
        c = user_conn.cursor()
        # Satır yoksa oluştur
        c.execute("INSERT OR IGNORE INTO log_settings (guild_id) VALUES (?)", (guild_id,))
        c.execute(
            f"UPDATE log_settings SET {update.column} = ? WHERE guild_id = ?",
            (update.channel_id, guild_id)
        )
        user_conn.commit()
        return {"status": "success", "column": update.column, "channel_id": update.channel_id}
    except Exception as e:
        print("Kanal yazma hatası:", e)
        raise HTTPException(status_code=500, detail="Kanal kaydedilemedi")
    finally:
        user_conn.close()


# ---------------------------------------------------------------------------
# Auth (V2)
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    password: str

@app.post("/api/auth/login")
def login(req: LoginRequest):
    # Basit "Süper Admin Şifresi"
    # İleride .env dosyasına alınabilir
    if req.password == "kumiho2026":
        # Basit bir JWT yerine sabit bir bearer token veriyoruz.
        # Güvenlik için token gerçek bir JWT ile değiştirilebilir.
        return {"status": "success", "token": "kumiho-admin-token-777"}
    raise HTTPException(status_code=401, detail="Hatalı şifre!")

# ---------------------------------------------------------------------------
# Admin Notes (V2)
# ---------------------------------------------------------------------------
class NoteCreate(BaseModel):
    user_id: str
    note: str
    added_by: str

@app.get("/api/notes/{user_id}")
def get_user_notes(user_id: str):
    conn = sqlite3.connect(MAIN_DB_PATH)
    conn.row_factory = dict_factory
    c = conn.cursor()
    c.execute("SELECT * FROM admin_notes WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    notes = c.fetchall()
    conn.close()
    return {"notes": notes}

@app.post("/api/notes")
def add_admin_note(req: NoteCreate):
    conn = sqlite3.connect(MAIN_DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO admin_notes (user_id, note, added_by) VALUES (?, ?, ?)", 
              (req.user_id, req.note, req.added_by))
    conn.commit()
    conn.close()
    return {"status": "success"}

# ---------------------------------------------------------------------------
# Command Permissions (V2)
# ---------------------------------------------------------------------------
class CommandPermUpdate(BaseModel):
    command_name: str
    is_enabled: int
    allowed_roles: str # JSON array formatında virgülle ayrılmış liste veya json string

@app.get("/api/commands/{guild_id}")
def get_commands(guild_id: str):
    conn = sqlite3.connect(MAIN_DB_PATH)
    conn.row_factory = dict_factory
    c = conn.cursor()
    c.execute("SELECT * FROM command_permissions WHERE guild_id = ?", (guild_id,))
    perms = c.fetchall()
    conn.close()

    # Read generated command list
    try:
        import json
        import os
        json_path = os.path.join(os.path.dirname(__file__), "commands_list.json")
        with open(json_path, "r", encoding="utf-8") as f:
            categories = json.load(f)
    except Exception as e:
        categories = {}
        
    return {"permissions": perms, "categories": categories}

@app.post("/api/commands/{guild_id}")
def update_command(guild_id: str, req: CommandPermUpdate):
    conn = sqlite3.connect(MAIN_DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO command_permissions (guild_id, command_name, is_enabled, allowed_roles)
                 VALUES (?, ?, ?, ?)
                 ON CONFLICT(guild_id, command_name) 
                 DO UPDATE SET is_enabled=excluded.is_enabled, allowed_roles=excluded.allowed_roles''',
              (guild_id, req.command_name, req.is_enabled, req.allowed_roles))
    conn.commit()
    conn.close()
    return {"status": "success"}

class CategoryPermUpdate(BaseModel):
    commands: list[str]
    is_enabled: int

@app.post("/api/commands/category/{guild_id}")
def update_category_commands(guild_id: str, req: CategoryPermUpdate):
    conn = sqlite3.connect(MAIN_DB_PATH)
    c = conn.cursor()
    for cmd_name in req.commands:
        c.execute('''INSERT INTO command_permissions (guild_id, command_name, is_enabled, allowed_roles)
                     VALUES (?, ?, ?, '[]')
                     ON CONFLICT(guild_id, command_name) 
                     DO UPDATE SET is_enabled=excluded.is_enabled''',
                  (guild_id, cmd_name, req.is_enabled))
    conn.commit()
    conn.close()
    return {"status": "success"}

# ---------------------------------------------------------------------------
# Pending Actions (V2) - Moderasyon
# ---------------------------------------------------------------------------
class ActionCreate(BaseModel):
    target_user_id: str
    action_type: str # 'mute', 'ban', 'kick' vb.
    reason: str

@app.post("/api/actions/{guild_id}")
def create_action(guild_id: str, req: ActionCreate):
    conn = sqlite3.connect(MAIN_DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO pending_actions (guild_id, target_user_id, action_type, reason)
                 VALUES (?, ?, ?, ?)''', 
              (guild_id, req.target_user_id, req.action_type, req.reason))
    conn.commit()
    conn.close()
    return {"status": "success"}
