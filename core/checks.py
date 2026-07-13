import os
import json
import logging
import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

log = logging.getLogger(__name__)

class CommandDisabled(app_commands.CheckFailure, commands.CheckFailure):
    pass

class CommandNotAllowed(app_commands.CheckFailure, commands.CheckFailure):
    pass

OWNER_IDS_RAW = os.getenv("OWNER_ID", "")

async def evaluate_kumiho_permissions(interaction_or_ctx, cmd_name: str, default_access: str) -> bool:
    """
    Kumiho Bot'un temel yetki kontrol mantığı.
    Önce veritabanına (kumiho.db) bakar. Eğer veritabanında özel bir ayar (rol veya kapatma) yoksa,
    default_access değerine ("public" veya "owner") göre fallback yapar.
    """
    if isinstance(interaction_or_ctx, discord.Interaction):
        user = interaction_or_ctx.user
        guild = interaction_or_ctx.guild
        bot = interaction_or_ctx.client
    else:
        user = interaction_or_ctx.author
        guild = interaction_or_ctx.guild
        bot = interaction_or_ctx.bot

    # DM üzerinden kullanım her zaman public komutlar için serbesttir
    if not guild:
        if default_access == "owner":
            bot_owners = [o.strip() for o in OWNER_IDS_RAW.split(",") if o.strip()]
            if str(user.id) not in bot_owners:
                raise CommandNotAllowed("Bu komut sadece bot sahibi tarafından kullanılabilir.")
        return True

    # Bot sahibi (Süper admin) her zaman bypass eder
    bot_owners = [o.strip() for o in OWNER_IDS_RAW.split(",") if o.strip()]
    if str(user.id) in bot_owners:
        return True
        
    # Sunucu sahibi her zaman bypass eder
    if user.id == guild.owner_id:
        return True

    is_admin = user.guild_permissions.administrator

    # 1) Veritabanı Kontrolü (Web UI / Discord Senkronizasyonu)
    try:
        row = await bot.db.fetchone("SELECT is_enabled, allowed_roles FROM command_permissions WHERE guild_id = ? AND command_name = ?", str(guild.id), cmd_name)

        if row:
            is_enabled = row[0]
            allowed_roles_str = row[1]
            
            if is_enabled == 0:
                raise CommandDisabled("Bu komut bu sunucuda tamamen devre dışı bırakılmış.")
                
            if allowed_roles_str and allowed_roles_str != '[]' and allowed_roles_str != '':
                try:
                    allowed_roles = json.loads(allowed_roles_str)
                    if not isinstance(allowed_roles, list):
                        allowed_roles = []
                except json.JSONDecodeError:
                    log.error(f"Geçersiz JSON formatı: {allowed_roles_str} (Komut: {cmd_name}, Sunucu: {guild.id})")
                    raise CommandNotAllowed("Komut yetkileri okunurken hata oluştu.")

                if allowed_roles:
                    user_role_ids = [str(r.id) for r in user.roles]
                    has_role = any(r in user_role_ids for r in allowed_roles)
                    if not has_role:
                        raise CommandNotAllowed("Bu komutu kullanmak için Web Panel üzerinden atanan özel role sahip değilsiniz.")
                    return True # Role sahipse kesin izin ver
    except Exception as e:
        if isinstance(e, (CommandDisabled, CommandNotAllowed)):
            raise e
        log.error(f"Veritabanı okuma hatası [checks.py]: {e}")

    # Özel rol kısıtlaması yoksa veya DB'de kayıt yoksa, default_access mantığına düşer.
    
    # Yönetici ise her türlü default yetkiyi geçer (özel role takılmadıysa ve is_enabled=0 değilse buraya ulaşır)
    if is_admin:
        return True

    # 2) Fallback (Varsayılan yetki durumu)
    if default_access == "owner":
        # Buraya düştüysek: Bot sahibi değil, Sunucu sahibi değil, Admin değil ve DB'de özel yetki rolüne sahip değil.
        raise CommandNotAllowed("Bu komut sadece yöneticiler veya panelden atanmış özel yetkili roller tarafından kullanılabilir.")
    
    # public ise herkese açık
    return True

def kumiho_check(default_access="public"):
    """
    Prefix (Geleneksel) komutlar için merkezi yetki kontrol dekoratörü.
    """
    def decorator(func):
        func.__kumiho_default_access__ = default_access
        async def predicate(ctx):
            cmd_name = ctx.command.qualified_name
            return await evaluate_kumiho_permissions(ctx, cmd_name, default_access)
        return commands.check(predicate)(func)
    return decorator

def kumiho_app_check(default_access="public"):
    """
    Slash (App) komutları için merkezi yetki kontrol dekoratörü.
    """
    def decorator(func):
        func.__kumiho_default_access__ = default_access
        async def predicate(interaction: discord.Interaction):
            cmd_name = interaction.command.name if interaction.command else "unknown"
            return await evaluate_kumiho_permissions(interaction, cmd_name, default_access)
        return app_commands.check(predicate)(func)
    return decorator
