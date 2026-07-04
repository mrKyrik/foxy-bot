import os
import sqlite3
import json
import urllib.request
import urllib.error
import urllib.parse
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

load_dotenv(os.path.join(BASE_DIR, ".env"))
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
JWT_SECRET = os.getenv("JWT_SECRET", "default_secret_key_change_me")

security = HTTPBearer()

def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)):
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Giriş oturumu geçersiz veya süresi dolmuş.")

def verify_guild_access(guild_id: str, payload: dict = Depends(verify_token)):
    allowed_guilds = payload.get("allowed_guilds", [])
    if guild_id not in allowed_guilds:
        raise HTTPException(status_code=403, detail="Bu sunucuyu yönetme yetkiniz yok.")
    return payload

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
        guild_id TEXT DEFAULT 'GLOBAL',
        user_id TEXT NOT NULL,
        note TEXT NOT NULL,
        added_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    try:
        c.execute("ALTER TABLE admin_notes ADD COLUMN guild_id TEXT DEFAULT 'GLOBAL'")
    except sqlite3.OperationalError:
        pass

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



@app.post("/api/settings/oda-kurulum/{guild_id}")
def setup_private_voice(guild_id: str, _: dict = Depends(verify_guild_access)):
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 1. Kategori oluştur
    res_cat = requests.post(
        f"https://discord.com/api/v10/guilds/{guild_id}/channels",
        headers=headers,
        json={"name": "🎙️ Özel Odalar", "type": 4} # 4 is category
    )
    if res_cat.status_code != 201:
        raise HTTPException(status_code=400, detail="Kategori oluşturulamadı. Bot yetkilerini kontrol edin.")
    cat_data = res_cat.json()
    category_id = cat_data["id"]
    
    # 2. Hub kanalını oluştur
    res_vc = requests.post(
        f"https://discord.com/api/v10/guilds/{guild_id}/channels",
        headers=headers,
        json={"name": "➕ Oda Oluştur", "type": 2, "parent_id": category_id}
    )
    if res_vc.status_code != 201:
        raise HTTPException(status_code=400, detail="Ses kanalı oluşturulamadı.")
    vc_data = res_vc.json()
    hub_id = vc_data["id"]
    
    # 3. DB'ye kaydet
    user_conn = get_db_connection(USER_DB_PATH)
    if user_conn:
        try:
            c = user_conn.cursor()
            c.execute(
                "INSERT INTO private_voice_hubs (guild_id, hub_id, category_id) VALUES (?, ?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET hub_id=excluded.hub_id, category_id=excluded.category_id",
                (guild_id, str(hub_id), str(category_id))
            )
            user_conn.commit()
        finally:
            user_conn.close()
            
    return {"status": "success", "hub_id": hub_id, "category_id": category_id}

@app.delete("/api/settings/oda-kurulum/{guild_id}")
def delete_private_voice(guild_id: str, _: dict = Depends(verify_guild_access)):
    # 1) Veritabanından mevcut kayıtları çekelim ki Discord'dan kanalları da silelim
    user_conn = get_db_connection(USER_DB_PATH)
    hub_id = None
    category_id = None
    if user_conn:
        try:
            c = user_conn.cursor()
            c.execute("SELECT hub_id, category_id FROM private_voice_hubs WHERE guild_id = ?", (guild_id,))
            row = c.fetchone()
            if row:
                hub_id, category_id = row
            c.execute("DELETE FROM private_voice_hubs WHERE guild_id = ?", (guild_id,))
            user_conn.commit()
        finally:
            user_conn.close()
            
    # 2) Discord API üzerinden kanalları sil (Eğer varsa)
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
    if hub_id:
        requests.delete(f"https://discord.com/api/v10/channels/{hub_id}", headers=headers)
    if category_id:
        requests.delete(f"https://discord.com/api/v10/channels/{category_id}", headers=headers)
        
    return {"status": "success"}

# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Global & Multi-Guild (V2) - OAuth2
# ---------------------------------------------------------------------------

import requests

@app.post("/api/auth/discord/callback")
async def discord_callback(request: Request):
    data = await request.json()
    code = data.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Code eksik")
        
    token_url = "https://discord.com/api/oauth2/token"
    token_data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "DiscordBot (https://github.com/kumiho, 1.0)"
    }
    
    try:
        res = requests.post(token_url, data=token_data, headers=headers, timeout=10)
        if res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Discord token hatası: {res.text}")
        auth_response = res.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Discord yetkilendirme hatası (Bağlantı): {str(e)}")
        
    access_token = auth_response.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token alınamadı")
        
    headers_auth = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "DiscordBot (https://github.com/kumiho, 1.0)"
    }
    
    # Get User Info
    try:
        res_user = requests.get("https://discord.com/api/v10/users/@me", headers=headers_auth, timeout=10)
        if res_user.status_code != 200:
            raise HTTPException(status_code=400, detail="Kullanıcı bilgileri alınamadı")
        user_info = res_user.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Kullanıcı bilgileri alınamadı (Bağlantı)")
        
    # Get User Guilds
    try:
        res_guilds = requests.get("https://discord.com/api/v10/users/@me/guilds", headers=headers_auth, timeout=10)
        if res_guilds.status_code != 200:
            raise HTTPException(status_code=400, detail="Sunucu bilgileri alınamadı")
        guilds_data = res_guilds.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Sunucu bilgileri alınamadı")
        
    # Filter guilds (MANAGE_GUILD = 0x20, ADMINISTRATOR = 0x8)
    allowed_guilds = []
    formatted_guilds = []
    for g in guilds_data:
        perms = int(g.get("permissions", 0))
        if (perms & 0x20) == 0x20 or (perms & 0x8) == 0x8:
            allowed_guilds.append(g["id"])
            icon_url = f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png" if g.get("icon") else None
            formatted_guilds.append({"id": g["id"], "name": g["name"], "icon": icon_url})
            
    # Generate local JWT
    jwt_payload = {
        "user_id": user_info["id"],
        "username": user_info.get("username"),
        "allowed_guilds": allowed_guilds,
        "guilds_data": formatted_guilds,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    local_token = jwt.encode(jwt_payload, JWT_SECRET, algorithm="HS256")
    
    return {"status": "success", "token": local_token, "user": user_info}


@app.get("/api/global_stats")
def get_global_stats():
    conn = sqlite3.connect(MAIN_DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(DISTINCT guild_id) FROM guild_settings")
        guilds_in_db = c.fetchone()[0]
    except Exception:
        guilds_in_db = 0
    try:
        c.execute("SELECT COUNT(*) FROM user_cache")
        total_users = c.fetchone()[0]
    except Exception:
        total_users = 0
    conn.close()
    
    return {"total_guilds": guilds_in_db, "total_users": total_users}

@app.get("/api/guilds")
def get_guilds(payload: dict = Depends(verify_token)):
    # JWT içinden kullanıcının yetkili olduğu sunucuları direkt dön
    return {"guilds": payload.get("guilds_data", [])}

@app.get("/api/stats/{guild_id}")
def get_guild_stats(guild_id: str, _: dict = Depends(verify_guild_access)):
    conn = get_db_connection(MAIN_DB_PATH)
    if not conn:
        return {"total_logs": 0, "total_warns": 0, "total_admin_actions": 0, "recent_logs": []}
    
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) as c FROM db_event_logs WHERE guild_id = ?", (guild_id,))
        total_logs = c.fetchone()["c"]
    except Exception:
        total_logs = 0

    try:
        c.execute("SELECT COUNT(*) as c FROM warns WHERE guild_id = ?", (guild_id,))
        total_warns = c.fetchone()["c"]
    except Exception:
        total_warns = 0

    try:
        c.execute("SELECT COUNT(*) as c FROM admin_events WHERE guild_id = ?", (guild_id,))
        total_admin_actions = c.fetchone()["c"]
    except Exception:
        total_admin_actions = 0

    try:
        c.execute("SELECT * FROM db_event_logs WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 5", (guild_id,))
        recent_logs = c.fetchall()
    except Exception:
        recent_logs = []

    conn.close()
    return {
        "total_logs": total_logs,
        "total_warns": total_warns,
        "total_admin_actions": total_admin_actions,
        "recent_logs": recent_logs
    }

# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

@app.get("/api/users/{guild_id}/{user_id}/roles")
def get_user_current_roles(guild_id: str, user_id: str, _: dict = Depends(verify_guild_access)):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT role_id, role_name FROM user_current_roles WHERE guild_id=? AND user_id=?", 
            (guild_id, user_id)
        )
        roles = [dict(row) for row in cur.fetchall()]
        conn.close()
        return {"roles": roles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/{guild_id}")
def get_guild_logs(guild_id: str, limit: int = 2000, start_time: int = None, end_time: int = None, _: dict = Depends(verify_guild_access)):
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
        date_filter_admin = "AND e.timestamp >= ? AND e.timestamp <= ?"

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
                e.timestamp || 'Z' as timestamp,
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
                    if "role_id" in details_obj:
                        r_dict["role_id"] = details_obj["role_id"]
                    if "role_name" in details_obj:
                        r_dict["role_name"] = details_obj["role_name"]
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
                    e.timestamp || 'Z' as timestamp,
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
# Channels  [YENİ]
# ---------------------------------------------------------------------------

@app.get("/api/channels/{guild_id}")
def get_channels(guild_id: str, _: dict = Depends(verify_guild_access)):
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


@app.get("/api/discord-channels/{guild_id}")
def get_discord_channels_live(guild_id: str, _: dict = Depends(verify_guild_access)):
    """
    Discord REST API üzerinden anlık tüm kanalları ve kategorileri çeker.
    """
    if not DISCORD_TOKEN:
        return {"error": "DISCORD_TOKEN bulunamadı."}
    
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
    import requests
    res = requests.get(f"https://discord.com/api/v10/guilds/{guild_id}/channels", headers=headers)
    
    if res.status_code != 200:
        return {"error": f"Discord API Error: {res.status_code}"}
        
    channels = res.json()
    # Türleri ayrıştır: Type 4 = Kategori, Type 2 = Voice, Type 0 = Text vs.
    categories = [{"id": c["id"], "name": c["name"]} for c in channels if c["type"] == 4]
    voice_channels = [{"id": c["id"], "name": c["name"], "parent_id": c.get("parent_id")} for c in channels if c["type"] == 2]
    
    return {
        "guild_id": guild_id,
        "categories": categories,
        "voice_channels": voice_channels
    }

class ManualVoiceSetup(BaseModel):
    category_id: str
    hub_id: str

@app.post("/api/settings/oda-kurulum/manual/{guild_id}")
def setup_manual_private_voice(guild_id: str, data: ManualVoiceSetup, _: dict = Depends(verify_guild_access)):
    """
    Kullanıcının seçtiği mevcut bir kategori ve ses kanalını Özel Oda Sistemi olarak kaydeder.
    """
    user_conn = get_db_connection(USER_DB_PATH)
    if user_conn:
        try:
            c = user_conn.cursor()
            c.execute(
                "INSERT INTO private_voice_hubs (guild_id, hub_id, category_id) VALUES (?, ?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET hub_id=excluded.hub_id, category_id=excluded.category_id",
                (guild_id, data.hub_id, data.category_id)
            )
            user_conn.commit()
            return {"success": True, "message": "Oda sistemi başarıyla yapılandırıldı!"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            user_conn.close()
    return {"error": "DB_CONNECTION_FAILED"}

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
def get_log_settings(guild_id: str, _: dict = Depends(verify_guild_access)):
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
                
            # 3) Private Voice (Oda Sistemi) durumu
            c.execute("SELECT hub_id, category_id FROM private_voice_hubs WHERE guild_id = ?", (guild_id,))
            pv_row = c.fetchone()
            private_voice = {}
            if pv_row:
                private_voice = {"hub_id": pv_row["hub_id"], "category_id": pv_row["category_id"]}

        except Exception as e:
            print("Settings okuma hatası:", e)
        finally:
            user_conn.close()

    return {"guild_id": guild_id, "settings": settings, "channels": channels, "private_voice": private_voice}


@app.post("/api/settings/{guild_id}")
def update_log_setting(guild_id: str, update: LogSettingsUpdate, _: dict = Depends(verify_guild_access)):
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
def update_channel_setting(guild_id: str, update: ChannelSettingUpdate, _: dict = Depends(verify_guild_access)):
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
# Admin Notes (V2)
# ---------------------------------------------------------------------------
class NoteCreate(BaseModel):
    user_id: str
    note: str
    added_by: str

@app.get("/api/notes/{guild_id}/{user_id}")
def get_user_notes(guild_id: str, user_id: str, _: dict = Depends(verify_guild_access)):
    conn = sqlite3.connect(MAIN_DB_PATH)
    conn.row_factory = dict_factory
    c = conn.cursor()
    c.execute("SELECT * FROM admin_notes WHERE user_id = ? AND guild_id IN (?, 'GLOBAL') ORDER BY created_at DESC", (user_id, guild_id))
    notes = c.fetchall()
    conn.close()
    return {"notes": notes}

@app.post("/api/notes/{guild_id}")
def add_admin_note(guild_id: str, req: NoteCreate, _: dict = Depends(verify_guild_access)):
    conn = sqlite3.connect(MAIN_DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO admin_notes (guild_id, user_id, note, added_by) VALUES (?, ?, ?, ?)", 
              (guild_id, req.user_id, req.note, req.added_by))
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
def get_commands(guild_id: str, _: dict = Depends(verify_guild_access)):
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
def update_command(guild_id: str, req: CommandPermUpdate, _: dict = Depends(verify_guild_access)):
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

@app.get("/api/roles/{guild_id}")
def search_roles(guild_id: str, q: Optional[str] = "", _: dict = Depends(verify_guild_access)):
    conn = sqlite3.connect(USER_DB_PATH)
    conn.row_factory = dict_factory
    c = conn.cursor()
    query = "SELECT role_id, role_name FROM roles WHERE guild_id = ?"
    params = [guild_id]
    if q:
        query += " AND role_name LIKE ?"
        params.append(f"%{q}%")
    query += " LIMIT 20"
    try:
        c.execute(query, params)
        roles = c.fetchall()
    except:
        roles = []
    conn.close()
    return {"roles": roles}

class CategoryPermUpdate(BaseModel):
    commands: list[str]
    is_enabled: int

@app.post("/api/commands/category/{guild_id}")
def update_category_commands(guild_id: str, req: CategoryPermUpdate, _: dict = Depends(verify_guild_access)):
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

class CategoryRoleUpdate(BaseModel):
    commands: list[str]
    role_id: str

@app.post("/api/commands/category/{guild_id}/roles")
def add_role_to_category(guild_id: str, req: CategoryRoleUpdate, _: dict = Depends(verify_guild_access)):
    import json
    conn = sqlite3.connect(MAIN_DB_PATH)
    conn.row_factory = dict_factory
    c = conn.cursor()
    for cmd_name in req.commands:
        c.execute("SELECT is_enabled, allowed_roles FROM command_permissions WHERE guild_id = ? AND command_name = ?", (guild_id, cmd_name))
        row = c.fetchone()
        is_enabled = 1
        allowed_roles = []
        if row:
            is_enabled = row["is_enabled"]
            if row["allowed_roles"] and row["allowed_roles"] != "[]":
                try:
                    allowed_roles = json.loads(row["allowed_roles"])
                except:
                    pass
        if req.role_id not in allowed_roles:
            allowed_roles.append(req.role_id)
            
        c.execute('''INSERT INTO command_permissions (guild_id, command_name, is_enabled, allowed_roles)
                     VALUES (?, ?, ?, ?)
                     ON CONFLICT(guild_id, command_name) 
                     DO UPDATE SET allowed_roles=excluded.allowed_roles''',
                  (guild_id, cmd_name, is_enabled, json.dumps(allowed_roles)))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/commands/category/{guild_id}/roles/remove")
def remove_role_from_category(guild_id: str, req: CategoryRoleUpdate, _: dict = Depends(verify_guild_access)):
    import json
    conn = sqlite3.connect(MAIN_DB_PATH)
    conn.row_factory = dict_factory
    c = conn.cursor()
    for cmd_name in req.commands:
        c.execute("SELECT is_enabled, allowed_roles FROM command_permissions WHERE guild_id = ? AND command_name = ?", (guild_id, cmd_name))
        row = c.fetchone()
        
        if not row:
            continue
            
        allowed_roles = []
        if row["allowed_roles"] and row["allowed_roles"] != "[]":
            try:
                allowed_roles = json.loads(row["allowed_roles"])
            except:
                pass
                
        if req.role_id in allowed_roles:
            allowed_roles.remove(req.role_id)
            c.execute("UPDATE command_permissions SET allowed_roles = ? WHERE guild_id = ? AND command_name = ?", 
                      (json.dumps(allowed_roles), guild_id, cmd_name))
                      
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
def create_action(guild_id: str, req: ActionCreate, _: dict = Depends(verify_guild_access)):
    conn = sqlite3.connect(MAIN_DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO pending_actions (guild_id, target_user_id, action_type, reason)
                 VALUES (?, ?, ?, ?)''', 
              (guild_id, req.target_user_id, req.action_type, req.reason))
    conn.commit()
    conn.close()
    return {"status": "success"}
