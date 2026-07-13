from __future__ import annotations
import logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

class ModerationEvents(commands.Cog):
    """Denetim kaydından manuel (sağ tık) moderasyon işlemlerini yakalayıp loglar."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def get_mod_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        row = await self.bot.db.fetchone(
            "SELECT mod_channel FROM log_settings WHERE guild_id=?", 
            str(guild.id)
        )
        if not row or not row["mod_channel"]: return None
        try:
            return guild.get_channel(int(row["mod_channel"])) or await guild.fetch_channel(int(row["mod_channel"]))
        except (ValueError, discord.NotFound, discord.Forbidden):
            return None

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        # Sadece botun yapmadığı işlemleri logla (Bot zaten _log fonksiyonuyla atıyor)
        if entry.user and entry.user.id == self.bot.user.id:
            return

        actions = {
            discord.AuditLogAction.kick: "Sağ Tık Kick",
            discord.AuditLogAction.ban: "Sağ Tık Ban",
            discord.AuditLogAction.unban: "Sağ Tık Unban",
            discord.AuditLogAction.member_update: "Manuel Timeout / Üye Güncelleme",
            discord.AuditLogAction.member_role_update: "Manuel Rol Yönetimi"
        }

        if entry.action not in actions:
            return
            
        # member_update içinden timeout izole et
        if entry.action == discord.AuditLogAction.member_update:
            if not hasattr(entry.after, 'communication_disabled_until'):
                return

        target = entry.target
        target_str = getattr(target, 'mention', str(target))
        target_id = getattr(target, 'id', None)
        if target_id:
            target_str += f" ({target_id})"
            
        admin_id = entry.user.id if entry.user else 0
        user_str = f"{entry.user.mention} ({admin_id})" if entry.user else "Bilinmiyor"
        reason = entry.reason or "Sebep belirtilmedi."

        # DB Logu (Web UI için Admin/Mod olayı olarak kaydet)
        db_action_map = {
            discord.AuditLogAction.kick: "mod_kick",
            discord.AuditLogAction.ban: "mod_ban",
            discord.AuditLogAction.unban: "mod_unban",
            discord.AuditLogAction.member_update: "mod_timeout",
            discord.AuditLogAction.member_role_update: "mod_role"
        }
        
        await self.bot.db.log_admin_event(
            guild_id=entry.guild.id,
            admin_id=admin_id,
            action_type=db_action_map[entry.action],
            target_id=target_id or 0,
            reason=f"(Manuel: {actions[entry.action]}) {reason}"
        )

        log_channel = await self.get_mod_log_channel(entry.guild)
        if log_channel:
            embed = discord.Embed(
                title="⚠️ Manuel Moderasyon İşlemi (Bot Dışı)",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="İşlem", value=actions[entry.action], inline=False)
            embed.add_field(name="Kullanıcı", value=target_str, inline=True)
            embed.add_field(name="Yetkili", value=user_str, inline=True)
            embed.add_field(name="Sebep", value=reason, inline=False)

            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationEvents(bot))
