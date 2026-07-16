from __future__ import annotations
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

class PrivateVoiceSettingsUpdate(BaseModel):
    room_name: Optional[str] = None
    user_limit: Optional[int] = None
    bitrate: Optional[int] = None
    is_locked: Optional[bool] = None
    is_hidden: Optional[bool] = None

app = FastAPI(title="Kumiho Log Dashboard API")

# İzin verilen originler
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # CRA / alternatif
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://kyrik.duckdns.org:5173",
        "http://152.67.86.27:5173",
        "https://kyrik.duckdns.org",
        "http://kyrik.duckdns.org",
        "https://152.67.86.27",
        "http://152.67.86.27",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Veritabanı yolları
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
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
        print(f"403 ERROR PREVENTED: requested_guild={guild_id}, allowed_guilds={allowed_guilds}")
        raise HTTPException(status_code=403, detail="Bu sunucuyu yönetme yetkiniz yok.")
    
    owned_guilds = payload.get("owned_guilds", [])
    user_id = payload.get("user_id")
    
    if guild_id in owned_guilds:
        payload["guild_permission"] = "owner"
    else:
        # Check panel_access_controls using user_id and user_current_roles
        conn = get_db_connection(MAIN_DB_PATH)
        if conn:
            c = conn.cursor()
            
            # 1. Check user_id explicitly
            c.execute("SELECT permission_level FROM panel_access_controls WHERE guild_id = ? AND target_id = ? AND target_type = 'user'", (guild_id, user_id))
            user_perm = c.fetchone()
            
            # 2. Check roles
            c.execute("SELECT role_id FROM user_current_roles WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            user_roles = [r["role_id"] for r in c.fetchall()]
            
            role_perm_level = None
            if user_roles:
                placeholders = ",".join("?" * len(user_roles))
                query = f"SELECT permission_level FROM panel_access_controls WHERE guild_id = ? AND target_type = 'role' AND target_id IN ({placeholders})"
                c.execute(query, [guild_id] + user_roles)
                role_perms = [row["permission_level"] for row in c.fetchall()]
                if "write" in role_perms:
                    role_perm_level = "write"
                elif "read" in role_perms:
                    role_perm_level = "read"
            
            conn.close()
            
            # Resolve highest permission: write > read
            final_perm = "read" # Default to read if they have basic access from allowed_guilds but no specific panel_access_controls (legacy support)
            
            if user_perm:
                final_perm = user_perm["permission_level"]
            elif role_perm_level:
                final_perm = role_perm_level
                
            payload["guild_permission"] = final_perm
        else:
            payload["guild_permission"] = "read" # Fallback
            
    return payload

def verify_write_access(payload: dict = Depends(verify_guild_access)):
    if payload.get("guild_permission") not in ["write", "owner"]:
        raise HTTPException(status_code=403, detail="Bu işlemi yapmak için düzenleme (yazma) yetkiniz yok.")
    return payload

def verify_owner_access(payload: dict = Depends(verify_guild_access)):
    if payload.get("guild_permission") != "owner":
        raise HTTPException(status_code=403, detail="Bu işlem için Sunucu Sahibi (Owner) yetkisi gereklidir.")
    return payload

# Kanal kolonu whitelist — güvenlik için sabit liste
CHANNEL_COLUMNS = [
    "msg_channel", "ses_channel", "mod_channel", "uyari_channel",
    "ticket_channel", "basvuru_channel", "davet_channel", "sunucu_channel", "rol_channel", "oda_channel"
]

TOGGLE_COLUMNS = [
    "msg_delete_on", "msg_edit_on", "ses_join_on", "ses_switch_on", "ses_stream_on", "ses_camera_on",
    "mod_role_on", "mod_channel_on", "mod_msg_on",
    "srv_update_on", "srv_emoji_on", "srv_role_on", "srv_perm_on",
    "warn_add_on", "warn_remove_on", "ticket_create_on", "ticket_close_on",
    "app_create_on", "app_accept_on", "app_reject_on", "invite_create_on", "invite_use_on",
    "role_add_on", "role_remove_on", "oda_create_on", "oda_delete_on", "oda_update_on"
]


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db_connection(db_path=MAIN_DB_PATH):
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
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
    try:
        c.execute("ALTER TABLE admin_notes ADD COLUMN admin_id TEXT")
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
    # panel_access_controls tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS panel_access_controls (
        guild_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        target_type TEXT NOT NULL,
        permission_level TEXT NOT NULL,
        PRIMARY KEY (guild_id, target_id)
    )''')
    conn.commit()
    conn.close()

# Uygulama başlarken db'yi init edelim
init_db()



@app.post("/api/settings/oda-kurulum/{guild_id}")
def setup_private_voice(guild_id: str, _: dict = Depends(verify_write_access)):
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
    user_conn = get_db_connection(MAIN_DB_PATH)
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
def delete_private_voice(guild_id: str, _: dict = Depends(verify_write_access)):
    # 1) Veritabanından mevcut kayıtları çekelim ki Discord'dan kanalları da silelim
    user_conn = get_db_connection(MAIN_DB_PATH)
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
    try:
        if hub_id:
            requests.delete(f"https://discord.com/api/v10/channels/{hub_id}", headers=headers)
        if category_id:
            requests.delete(f"https://discord.com/api/v10/channels/{category_id}", headers=headers)
    except Exception as e:
        print(f"Kanallar Discord üzerinden silinirken hata oluştu: {e}")
        
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
    redirect_uri = data.get("redirect_uri") or DISCORD_REDIRECT_URI
    if not code:
        raise HTTPException(status_code=400, detail="Code eksik")
        
    token_url = "https://discord.com/api/oauth2/token"
    token_data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
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
    owned_guilds = []
    formatted_guilds = []
    
    OWNER_ID = os.getenv("OWNER_ID")
    is_bot_owner = str(user_info["id"]) == str(OWNER_ID)
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    
    # Eğer giriş yapan kişi bot sahibi ise, botun tüm sunucularını listeye ez.
    if is_bot_owner and DISCORD_TOKEN:
        try:
            headers_bot = {"Authorization": f"Bot {DISCORD_TOKEN}"}
            res_bot_guilds = requests.get("https://discord.com/api/v10/users/@me/guilds", headers=headers_bot, timeout=10)
            if res_bot_guilds.status_code == 200:
                guilds_data = res_bot_guilds.json()
        except Exception as e:
            print(f"Bot guilds fetch error: {e}")
    
    # 1. Fetch Bot Presence & Role Permissions from SQLite
    try:
        import sqlite3
        conn = sqlite3.connect(MAIN_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT guild_id FROM log_settings")
        kumiho_guilds = {str(row[0]) for row in cur.fetchall()}
        
        cur.execute("SELECT guild_id, role_id FROM role_permissions")
        mod_roles = {}
        for row in cur.fetchall():
            g_id = str(row[0])
            r_id = str(row[1])
            if g_id not in mod_roles:
                mod_roles[g_id] = set()
            mod_roles[g_id].add(r_id)
        conn.close()
    except Exception as e:
        print(f"DB Error fetching permissions: {e}")
        kumiho_guilds = set()
        mod_roles = {}
    
    print(f"DEBUG CALLBACK: user={user_info.get('username')}, is_bot_owner={is_bot_owner}, total_guilds={len(guilds_data)}")
    
    for g in guilds_data:
        g_id = str(g["id"])
        
        # Sadece botun ekli olduğu sunucuları listele (Bot sahibi değilse)
        if not is_bot_owner and g_id not in kumiho_guilds:
            continue
            
        perms = int(g.get("permissions", 0))
        is_owner = g.get("owner", False)
        has_access = False
        
        # Temel Discord yetki kontrolü
        if is_bot_owner or is_owner or (perms & 0x20) == 0x20 or (perms & 0x8) == 0x8:
            has_access = True
        
        # Derin Yetki Doğrulaması (Kumiho özel rolleri)
        elif g_id in mod_roles and DISCORD_TOKEN:
            try:
                member_url = f"https://discord.com/api/v10/guilds/{g_id}/members/{user_info['id']}"
                headers_bot = {"Authorization": f"Bot {DISCORD_TOKEN}"}
                m_res = requests.get(member_url, headers_bot, timeout=5)
                if m_res.status_code == 200:
                    member_data = m_res.json()
                    user_roles = set(member_data.get("roles", []))
                    if user_roles.intersection(mod_roles[g_id]):
                        has_access = True
            except Exception as e:
                print(f"Error fetching member roles for {g_id}: {e}")
        if has_access:
            allowed_guilds.append(g_id)
            if is_owner or is_bot_owner:
                owned_guilds.append(g_id)
            icon_url = f"https://cdn.discordapp.com/icons/{g_id}/{g['icon']}.png" if g.get("icon") else None
            formatted_guilds.append({"id": g_id, "name": g["name"], "icon": icon_url})
    
    print(f"DEBUG CALLBACK: user={user_info.get('username')}, allowed_guilds={allowed_guilds}, owned_guilds={owned_guilds}")
            
    # Generate local JWT
    jwt_payload = {
        "user_id": user_info["id"],
        "username": user_info.get("username"),
        "allowed_guilds": allowed_guilds,
        "owned_guilds": owned_guilds,
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
def get_guild_stats(guild_id: str, payload: dict = Depends(verify_guild_access)):
    conn = get_db_connection(MAIN_DB_PATH)
    guild_permission = payload.get("guild_permission", "read")
    if not conn:
        return {"total_logs": 0, "total_warns": 0, "total_admin_actions": 0, "recent_logs": [], "guild_permission": guild_permission}
    
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
        "recent_logs": recent_logs,
        "guild_permission": guild_permission
    }

# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

@app.get("/api/users/{guild_id}/{user_id}/roles")
def get_user_current_roles(guild_id: str, user_id: str, _: dict = Depends(verify_guild_access)):
    try:
        conn = sqlite3.connect(MAIN_DB_PATH)
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
    user_conn = get_db_connection(MAIN_DB_PATH)
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
    admin_conn = get_db_connection(MAIN_DB_PATH)
    if admin_conn:
        try:
            cursor = admin_conn.cursor()
            cursor.execute(f"ATTACH DATABASE '{MAIN_DB_PATH}' AS userdb")
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
                LEFT JOIN user_cache u ON e.admin_id = u.user_id
                LEFT JOIN user_cache t_u ON e.target_id = t_u.user_id
                LEFT JOIN channel_cache t_c ON e.target_id = t_c.channel_id
                LEFT JOIN roles t_r ON e.target_id = t_r.role_id
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
    user_conn = get_db_connection(MAIN_DB_PATH)
    if user_conn:
        try:
            c = user_conn.cursor()
            c.execute(
                "SELECT channel_id, channel_name FROM channel_cache WHERE guild_id = ? ORDER BY channel_name ASC",
                (guild_id,)
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
    text_channels = [{"channel_id": c["id"], "channel_name": c["name"], "parent_id": c.get("parent_id")} for c in channels if c["type"] == 0 or c["type"] == 5]
    
    return {
        "guild_id": guild_id,
        "categories": categories,
        "voice_channels": voice_channels,
        "text_channels": text_channels,
        "channels": text_channels # for compatibility with old get_channels
    }

@app.get("/api/voice_rooms/{channel_id}")
def get_voice_room_live(channel_id: str, _: dict = Depends(verify_token)):
    user_conn = get_db_connection(MAIN_DB_PATH)
    if user_conn:
        try:
            c = user_conn.cursor()
            c.execute("SELECT live_data FROM private_voice_rooms WHERE channel_id = ?", (channel_id,))
            row = c.fetchone()
            if row and row["live_data"]:
                return json.loads(row["live_data"])
            else:
                return {"error": "Oda aktif değil veya silinmiş."}
        except Exception as e:
            return {"error": str(e)}
        finally:
            user_conn.close()
    return {"error": "DB_CONNECTION_FAILED"}

@app.get("/api/voice_settings/{user_id}")
def get_user_voice_settings(user_id: str, _: dict = Depends(verify_token)):
    user_conn = get_db_connection(MAIN_DB_PATH)
    if user_conn:
        try:
            c = user_conn.cursor()
            c.execute("SELECT room_name, user_limit, bitrate, is_locked, is_hidden FROM private_voice_settings WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if row:
                return {
                    "room_name": row["room_name"],
                    "user_limit": row["user_limit"],
                    "bitrate": row["bitrate"],
                    "is_locked": bool(row["is_locked"]),
                    "is_hidden": bool(row["is_hidden"])
                }
            else:
                return {"error": "Ayarlar bulunamadı."}
        except Exception as e:
            return {"error": str(e)}
        finally:
            user_conn.close()
    return {"error": "DB_CONNECTION_FAILED"}

@app.patch("/api/voice_settings/{user_id}")
def update_user_voice_settings(user_id: str, settings: PrivateVoiceSettingsUpdate, guild_id: Optional[str] = None, payload: dict = Depends(verify_token)):
    user_conn = get_db_connection(MAIN_DB_PATH)
    if user_conn:
        try:
            admin_id = payload.get("user_id", "unknown") if payload else "unknown"
            c = user_conn.cursor()
            c.execute("SELECT room_name, user_limit, bitrate, is_locked, is_hidden FROM private_voice_settings WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            
            rn = settings.room_name if settings.room_name is not None else (row["room_name"] if row else None)
            ul = settings.user_limit if settings.user_limit is not None else (row["user_limit"] if row else 0)
            br = settings.bitrate if settings.bitrate is not None else (row["bitrate"] if row else 64000)
            il = settings.is_locked if settings.is_locked is not None else (bool(row["is_locked"]) if row else False)
            ih = settings.is_hidden if settings.is_hidden is not None else (bool(row["is_hidden"]) if row else False)

            c.execute("""
                INSERT INTO private_voice_settings (user_id, room_name, user_limit, bitrate, is_locked, is_hidden)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    room_name=excluded.room_name,
                    user_limit=excluded.user_limit,
                    bitrate=excluded.bitrate,
                    is_locked=excluded.is_locked,
                    is_hidden=excluded.is_hidden
            """, (user_id, rn, ul, br, 1 if il else 0, 1 if ih else 0))
            
            # LOGLAMA (Sürdürülebilirlik)
            if guild_id and admin_id:
                details = f"Admin Panelinden Güncelleme - Odanın yeni ayarları: {rn}, Limit: {ul}, Bitrate: {br}, Kilitli: {il}, Gizli: {ih}"
                
                # Admin Loglarına yaz
                c.execute("""
                    INSERT INTO admin_events (guild_id, admin_id, action_type, target_id, reason)
                    VALUES (?, ?, ?, ?, ?)
                """, (guild_id, admin_id, "UPDATE_VOICE_SETTINGS", user_id, details))
                
                # Sistem Loglarına yaz (Oda timeline'ında görünmesi için)
                c.execute("""
                    INSERT INTO db_event_logs (guild_id, event_type, user_id, details)
                    VALUES (?, ?, ?, ?)
                """, (guild_id, "oda_update", user_id, details))
                
            user_conn.commit()
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}
        finally:
            user_conn.close()
    return {"error": "DB_CONNECTION_FAILED"}

@app.delete("/api/voice_rooms/{channel_id}")
def delete_voice_room_force(channel_id: str, payload: dict = Depends(verify_token)):
    # Sunucu doğrulama yapılamıyor çünkü channel_id sadece odaya ait. 
    # Güvenlik açısından burada guild_id istenebilir ama şimdilik doğrudan discord API'ye DELETE atıyoruz.
    if not DISCORD_TOKEN:
        return {"error": "DISCORD_TOKEN bulunamadı."}
    
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
    import requests
    res = requests.delete(f"https://discord.com/api/v10/channels/{channel_id}", headers=headers)
    
    if res.status_code == 200 or res.status_code == 204:
        # DB'den temizle
        user_conn = get_db_connection(MAIN_DB_PATH)
        if user_conn:
            try:
                c = user_conn.cursor()
                c.execute("DELETE FROM private_voice_rooms WHERE channel_id = ?", (channel_id,))
                user_conn.commit()
            except:
                pass
            finally:
                user_conn.close()
        return {"success": True, "message": "Oda başarıyla silindi."}
    else:
        return {"error": f"Discord API Error: {res.status_code}"}

@app.post("/api/voice_rooms/{channel_id}/kick/{user_id}")
def kick_voice_room_user(channel_id: str, user_id: str, payload: dict = Depends(verify_token)):
    if not DISCORD_TOKEN:
        return {"error": "DISCORD_TOKEN bulunamadı."}
    
    # Bir kullanıcıyı sesten atmak için guild bilgisi lazım, ancak discordda user'ın ses state'ini PATCH yaparak
    # channel_id = null yapabiliriz, ki bunun için endpoint: PATCH /guilds/{guild.id}/members/{user.id}
    # channel_id almamız guild'i gerektirir. 
    # Ancak odayı bildiğimize göre channel_id'den guild'i çekebiliriz:
    import requests
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}", "Content-Type": "application/json"}
    res = requests.get(f"https://discord.com/api/v10/channels/{channel_id}", headers=headers)
    if res.status_code != 200:
        return {"error": "Kanal bulunamadı."}
    
    guild_id = res.json().get("guild_id")
    if not guild_id:
        return {"error": "Guild id bulunamadı."}
        
    kick_res = requests.patch(f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}", 
                              json={"channel_id": None}, headers=headers)
    
    if kick_res.status_code == 200 or kick_res.status_code == 204:
        return {"success": True, "message": "Kullanıcı başarıyla odadan atıldı."}
    else:
        return {"error": f"Discord API Error: {kick_res.status_code} - {kick_res.text}"}

class ManualVoiceSetup(BaseModel):
    category_id: str
    hub_id: str

@app.post("/api/settings/oda-kurulum/manual/{guild_id}")
def setup_manual_private_voice(guild_id: str, data: ManualVoiceSetup, _: dict = Depends(verify_write_access)):
    """
    Kullanıcının seçtiği mevcut bir kategori ve ses kanalını Özel Oda Sistemi olarak kaydeder.
    """
    user_conn = get_db_connection(MAIN_DB_PATH)
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

    user_conn = get_db_connection(MAIN_DB_PATH)
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
            
        try:
            # 4) Ticket Settings
            c.execute("SELECT * FROM ticket_settings WHERE guild_id = ?", (guild_id,))
            ticket_row = c.fetchone()
            ticket_settings = {}
            if ticket_row:
                ticket_settings = dict(ticket_row)
        except Exception as e:
            print("Ticket Settings okuma hatası:", e)
            ticket_settings = {}
            
        finally:
            user_conn.close()

    return {"guild_id": guild_id, "settings": settings, "channels": channels, "private_voice": private_voice, "ticket_settings": ticket_settings}

class TicketSettingsUpdate(BaseModel):
    category_id: Optional[str] = None
    support_role_id: Optional[str] = None
    support_user_ids: Optional[str] = None
    admin_role_id: Optional[str] = None
    log_channel_id: Optional[str] = None
    panel_title: Optional[str] = None
    panel_desc: Optional[str] = None
    panel_channel_id: Optional[str] = None

@app.post("/api/settings/tickets/{guild_id}")
def update_ticket_settings(guild_id: str, update: TicketSettingsUpdate, _: dict = Depends(verify_write_access)):
    user_conn = get_db_connection(MAIN_DB_PATH)
    if not user_conn:
        raise HTTPException(status_code=500, detail="Veritabanına bağlanılamadı")
    try:
        c = user_conn.cursor()
        
        # Ensure support_user_ids column exists
        try:
            c.execute("ALTER TABLE ticket_settings ADD COLUMN support_user_ids TEXT DEFAULT '[]'")
        except Exception:
            pass  # Column might already exist
            
        c.execute("SELECT * FROM ticket_settings WHERE guild_id = ?", (guild_id,))
        if c.fetchone() is None:
            c.execute("INSERT INTO ticket_settings (guild_id) VALUES (?)", (guild_id,))
            
        if update.category_id is not None:
            c.execute("UPDATE ticket_settings SET category_id = ? WHERE guild_id = ?", (update.category_id, guild_id))
        if update.support_role_id is not None:
            c.execute("UPDATE ticket_settings SET support_role_id = ? WHERE guild_id = ?", (update.support_role_id, guild_id))
        if update.support_user_ids is not None:
            c.execute("UPDATE ticket_settings SET support_user_ids = ? WHERE guild_id = ?", (update.support_user_ids, guild_id))
        if update.admin_role_id is not None:
            c.execute("UPDATE ticket_settings SET admin_role_id = ? WHERE guild_id = ?", (update.admin_role_id, guild_id))
        if update.log_channel_id is not None:
            c.execute("UPDATE ticket_settings SET log_channel_id = ? WHERE guild_id = ?", (update.log_channel_id, guild_id))
        if update.panel_title is not None:
            c.execute("UPDATE ticket_settings SET panel_title = ? WHERE guild_id = ?", (update.panel_title, guild_id))
        if update.panel_desc is not None:
            c.execute("UPDATE ticket_settings SET panel_desc = ? WHERE guild_id = ?", (update.panel_desc, guild_id))
        if update.panel_channel_id is not None:
            c.execute("UPDATE ticket_settings SET panel_channel_id = ? WHERE guild_id = ?", (update.panel_channel_id, guild_id))
            
        user_conn.commit()
    except Exception as e:
        print("Ticket settings update error:", e)
        raise HTTPException(status_code=500, detail="Ticket ayarları güncellenemedi")
    finally:
        user_conn.close()
    return {"status": "ok"}

@app.get("/api/discord-roles/{guild_id}")
def get_discord_roles(guild_id: str, _: dict = Depends(verify_guild_access)):
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        return {"roles": []}
    try:
        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        res = requests.get(f"https://discord.com/api/v10/guilds/{guild_id}/roles", headers=headers, timeout=5)
        if res.status_code == 200:
            roles = res.json()
            return {"roles": [{"id": str(r["id"]), "name": r["name"], "color": r.get("color", 0)} for r in roles if r["name"] != "@everyone"]}
    except Exception as e:
        print("Roles fetch error:", e)
    return {"roles": []}

@app.get("/api/discord-members/{guild_id}")
def get_discord_members(guild_id: str, _: dict = Depends(verify_guild_access)):
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        return []
    try:
        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        # max 1000 limit, requires GUILD_MEMBERS intent (which is True)
        res = requests.get(f"https://discord.com/api/v10/guilds/{guild_id}/members?limit=1000", headers=headers, timeout=5)
        if res.status_code == 200:
            members = res.json()
            # return simplified list
            return [{
                "id": str(m["user"]["id"]), 
                "username": m["user"]["username"], 
                "avatar": m["user"].get("avatar")
            } for m in members]
    except Exception as e:
        print("Members fetch error:", e)
    return []


@app.post("/api/settings/{guild_id}")
def update_log_setting(guild_id: str, update: LogSettingsUpdate, _: dict = Depends(verify_write_access)):
    """ON/OFF şalteri günceller — db_log_settings tablosuna yazar."""
    if update.setting_name not in TOGGLE_COLUMNS:
        raise HTTPException(status_code=400, detail="Geçersiz ayar sütunu")

    user_conn = get_db_connection(MAIN_DB_PATH)
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
def update_channel_setting(guild_id: str, update: ChannelSettingUpdate, _: dict = Depends(verify_write_access)):
    """
    Discord log kanalını günceller — log_settings tablosuna yazar.
    channel_id = None ise kanal seçimi temizlenir.
    """
    if update.column not in CHANNEL_COLUMNS:
        raise HTTPException(status_code=400, detail="Geçersiz kanal kolonu")

    user_conn = get_db_connection(MAIN_DB_PATH)
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
def get_user_notes(guild_id: str, user_id: str, payload: dict = Depends(verify_guild_access)):
    user_conn = get_db_connection(MAIN_DB_PATH)
    if user_conn:
        c = user_conn.cursor()
        c.execute("SELECT * FROM admin_notes WHERE user_id = ? AND guild_id IN (?, 'GLOBAL') ORDER BY created_at DESC", (user_id, guild_id))
        notes = c.fetchall()
        user_conn.close()
        is_owner = guild_id in payload.get("owned_guilds", [])
        return {"notes": notes, "current_admin_id": payload.get("user_id"), "is_owner": is_owner}
    return {"error": "DB_CONNECTION_FAILED"}

@app.post("/api/notes/{guild_id}")
def add_admin_note(guild_id: str, note_data: dict, payload: dict = Depends(verify_write_access)):
    user_conn = get_db_connection(MAIN_DB_PATH)
    if user_conn:
        c = user_conn.cursor()
        admin_id = payload.get("user_id", "unknown")
        admin_name = payload.get("username", "Admin")
        
        c.execute("INSERT INTO admin_notes (guild_id, user_id, note, added_by, admin_id) VALUES (?, ?, ?, ?, ?)", 
                  (guild_id, note_data['user_id'], note_data['note'], admin_name, admin_id))
        user_conn.commit()
        user_conn.close()
        return {"success": True}
    return {"error": "DB_CONNECTION_FAILED"}

@app.delete("/api/notes/{guild_id}/{note_id}")
def delete_admin_note(guild_id: str, note_id: int, payload: dict = Depends(verify_write_access)):
    user_conn = get_db_connection(MAIN_DB_PATH)
    if user_conn:
        try:
            c = user_conn.cursor()
            admin_id = payload.get("user_id")
            
            c.execute("SELECT admin_id FROM admin_notes WHERE id = ? AND guild_id = ?", (note_id, guild_id))
            row = c.fetchone()
            if not row:
                return {"error": "Not bulunamadı."}
                
            is_owner = guild_id in payload.get("owned_guilds", [])
            if row["admin_id"] != admin_id and not is_owner:
                return {"error": "Bu notu sadece ekleyen veya sunucu sahibi silebilir."}
            
            c.execute("DELETE FROM admin_notes WHERE id = ? AND guild_id = ?", (note_id, guild_id))
            user_conn.commit()
            return {"success": True}
        finally:
            user_conn.close()
    return {"error": "DB_CONNECTION_FAILED"}

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

    # Veritabanından (bot_commands_registry) komut listesini oku
    categories = {}
    try:
        c.execute("SELECT command_name, category, description, default_access FROM bot_commands_registry")
        registry_rows = c.fetchall()
        for row in registry_rows:
            cat = row['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "name": row['command_name'],
                "desc": row['description'],
                "default_access": row.get('default_access', 'public')
            })
    except Exception as e:
        # Tablo henüz oluşmamışsa veya hata varsa boş döner
        categories = {}
    finally:
        conn.close()
        
    return {"permissions": perms, "categories": categories}

@app.post("/api/commands/{guild_id}")
def update_command(guild_id: str, req: CommandPermUpdate, _: dict = Depends(verify_write_access)):
    conn = sqlite3.connect(MAIN_DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO command_permissions (guild_id, command_name, is_enabled, allowed_roles)
                 VALUES (?, ?, ?, ?)
                 ON CONFLICT(guild_id, command_name) 
                 DO UPDATE SET is_enabled=excluded.is_enabled, allowed_roles=excluded.allowed_roles''',
              (guild_id, req.command_name, req.is_enabled, req.allowed_roles))
    conn.commit()
    conn.close()
# ---------------------------------------------------------------------------
# Form Yönetimi (Başvuru Şalterleri / Form UI)
# ---------------------------------------------------------------------------
from typing import List

class FormQuestion(BaseModel):
    question_text: str

class CustomFormCreate(BaseModel):
    form_id: str
    title: str
    channel_id: str
    form_type: int
    action_target: str = None
    auto_approve: int = 1
    questions: List[str] = []
    roles: List[str] = []

class SummonFormReq(BaseModel):
    target_channel_id: str

@app.get("/api/forms/{guild_id}")
def get_forms(guild_id: str, _: dict = Depends(verify_guild_access)):
    conn = get_db_connection(MAIN_DB_PATH)
    if not conn:
        return []
    c = conn.cursor()
    c.execute("SELECT * FROM custom_forms WHERE guild_id = ?", (guild_id,))
    forms = c.fetchall()
    
    for form in forms:
        c.execute("SELECT question_text FROM form_questions WHERE guild_id = ? AND form_id = ?", (guild_id, form['form_id']))
        form['questions'] = [row['question_text'] for row in c.fetchall()]
        
        if form['form_type'] == 2:
            c.execute("SELECT role_id FROM form_roles WHERE guild_id = ? AND form_id = ?", (guild_id, form['form_id']))
            form['roles'] = [row['role_id'] for row in c.fetchall()]
            
    conn.close()
    return forms

@app.post("/api/forms/{guild_id}")
def create_form(guild_id: str, form_data: CustomFormCreate, _: dict = Depends(verify_write_access)):
    conn = get_db_connection(MAIN_DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT form_id FROM custom_forms WHERE guild_id = ? AND form_id = ?", (guild_id, form_data.form_id))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Bu Form ID zaten kullanımda.")
        
    c.execute('''INSERT INTO custom_forms (form_id, guild_id, title, channel_id, form_type, action_target, auto_approve)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
              (form_data.form_id, guild_id, form_data.title, form_data.channel_id, form_data.form_type, form_data.action_target, form_data.auto_approve))
              
    for q in form_data.questions:
        c.execute("INSERT INTO form_questions (form_id, guild_id, question_text) VALUES (?, ?, ?)", (form_data.form_id, guild_id, q))
        
    if form_data.form_type == 2 and form_data.roles:
        for r in form_data.roles:
            c.execute("INSERT INTO form_roles (form_id, guild_id, role_id) VALUES (?, ?, ?)", (form_data.form_id, guild_id, r))
            
    conn.commit()
    conn.close()
    return {"status": "success", "form_id": form_data.form_id}

@app.put("/api/forms/{guild_id}/{form_id}")
def update_form(guild_id: str, form_id: str, form_data: CustomFormCreate, _: dict = Depends(verify_write_access)):
    conn = get_db_connection(MAIN_DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT form_id FROM custom_forms WHERE guild_id = ? AND form_id = ?", (guild_id, form_id))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Form bulunamadı.")
        
    c.execute('''UPDATE custom_forms SET title = ?, channel_id = ?, form_type = ?, action_target = ?, auto_approve = ?
                 WHERE guild_id = ? AND form_id = ?''', 
              (form_data.title, form_data.channel_id, form_data.form_type, form_data.action_target, form_data.auto_approve, guild_id, form_id))
              
    c.execute("DELETE FROM form_questions WHERE guild_id = ? AND form_id = ?", (guild_id, form_id))
    c.execute("DELETE FROM form_roles WHERE guild_id = ? AND form_id = ?", (guild_id, form_id))
    
    for q in form_data.questions:
        c.execute("INSERT INTO form_questions (form_id, guild_id, question_text) VALUES (?, ?, ?)", (form_id, guild_id, q))
        
    if form_data.form_type == 2 and form_data.roles:
        for r in form_data.roles:
            c.execute("INSERT INTO form_roles (form_id, guild_id, role_id) VALUES (?, ?, ?)", (form_id, guild_id, r))
            
    conn.commit()
    conn.close()
    return {"status": "success", "form_id": form_id}

@app.delete("/api/forms/{guild_id}/{form_id}")
def delete_form(guild_id: str, form_id: str, _: dict = Depends(verify_write_access)):
    conn = get_db_connection(MAIN_DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM custom_forms WHERE guild_id = ? AND form_id = ?", (guild_id, form_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/forms/{guild_id}/{form_id}/summon")
def summon_form(guild_id: str, form_id: str, req: SummonFormReq, _: dict = Depends(verify_write_access)):
    conn = get_db_connection(MAIN_DB_PATH)
    c = conn.cursor()
    
    import json
    payload = json.dumps({"form_id": form_id, "target_channel_id": req.target_channel_id})
    c.execute("INSERT INTO web_actions (guild_id, action_type, payload) VALUES (?, ?, ?)", 
              (guild_id, "summon_form", payload))
              
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Form tetiklendi"}

@app.get("/api/roles/{guild_id}")
def search_roles(guild_id: str, q: Optional[str] = "", _: dict = Depends(verify_guild_access)):
    conn = sqlite3.connect(MAIN_DB_PATH)
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
    commands: List[str]
    is_enabled: int

@app.post("/api/commands/category/{guild_id}")
def update_category_commands(guild_id: str, req: CategoryPermUpdate, _: dict = Depends(verify_write_access)):
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
    commands: List[str]
    role_id: str

@app.post("/api/commands/category/{guild_id}/roles")
def add_role_to_category(guild_id: str, req: CategoryRoleUpdate, _: dict = Depends(verify_write_access)):
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
def remove_role_from_category(guild_id: str, req: CategoryRoleUpdate, _: dict = Depends(verify_write_access)):
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
def create_action(guild_id: str, req: ActionCreate, _: dict = Depends(verify_write_access)):
    conn = sqlite3.connect(MAIN_DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO pending_actions (guild_id, target_user_id, action_type, reason)
                 VALUES (?, ?, ?, ?)''', 
              (guild_id, req.target_user_id, req.action_type, req.reason))
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- PANEL AUTHENTICATION / RBAC ---

class PanelAuthUpdate(BaseModel):
    target_id: str
    target_type: str # 'user' or 'role'
    permission_level: str # 'read' or 'write'

@app.get("/api/panel_auth/{guild_id}")
def get_panel_auth(guild_id: str, _: dict = Depends(verify_owner_access)):
    conn = get_db_connection(MAIN_DB_PATH)
    if not conn:
        return {"error": "DB error"}
    c = conn.cursor()
    c.execute("SELECT target_id, target_type, permission_level FROM panel_access_controls WHERE guild_id = ?", (guild_id,))
    rows = c.fetchall()
    conn.close()
    return {"permissions": rows}

@app.post("/api/panel_auth/{guild_id}")
def update_panel_auth(guild_id: str, req: PanelAuthUpdate, _: dict = Depends(verify_owner_access)):
    if req.permission_level not in ["read", "write"]:
        raise HTTPException(status_code=400, detail="Invalid permission level")
    if req.target_type not in ["user", "role"]:
        raise HTTPException(status_code=400, detail="Invalid target type")
        
    conn = get_db_connection(MAIN_DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO panel_access_controls (guild_id, target_id, target_type, permission_level)
                 VALUES (?, ?, ?, ?)
                 ON CONFLICT(guild_id, target_id)
                 DO UPDATE SET permission_level = excluded.permission_level, target_type = excluded.target_type''',
              (guild_id, req.target_id, req.target_type, req.permission_level))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/api/panel_auth/{guild_id}/{target_id}")
def delete_panel_auth(guild_id: str, target_id: str, _: dict = Depends(verify_owner_access)):
    conn = get_db_connection(MAIN_DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM panel_access_controls WHERE guild_id = ? AND target_id = ?", (guild_id, target_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3001)
