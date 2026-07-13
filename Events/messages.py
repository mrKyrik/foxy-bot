from __future__ import annotations
import logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

class Messages(commands.Cog):
    """Mesaj silinme ve düzenlenme olaylarını yakalayıp loglar."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._audit_cache = {}
        self._audit_cache_time = {}

    async def get_log_settings(self, guild: discord.Guild):
        """Sunucunun log ayarlarını veritabanından çeker."""
        row = await self.bot.db.fetchone(
            "SELECT msg_channel, msg_delete_on, msg_edit_on, mod_channel, mod_msg_on FROM log_settings WHERE guild_id=?", 
            str(guild.id)
        )
        return dict(row) if row else None

    async def get_log_channel(self, guild: discord.Guild, channel_id: int) -> discord.TextChannel | None:
        try:
            return guild.get_channel(channel_id) or await guild.fetch_channel(channel_id)
        except (ValueError, discord.NotFound, discord.Forbidden):
            return None

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if not message.guild or message.author.bot:
            return

        # İçeriği olmayan mesajları yoksay
        if not message.content:
            return

        settings = await self.get_log_settings(message.guild)
        discord_on = bool(settings and settings.get("msg_delete_on") == 1 and settings.get("msg_channel"))
        mod_discord_on = bool(settings and settings.get("mod_msg_on") == 1 and settings.get("mod_channel"))

        # Discord Audit Log kontrolü (Rate Limit korumalı)
        mod_user = None
        now = discord.utils.utcnow().timestamp()
        cache_key = (message.guild.id, message.author.id, message.channel.id)

        if now - self._audit_cache_time.get(message.guild.id, 0) < 2:
            mod_user = self._audit_cache.get(cache_key)
        else:
            if message.guild.me.guild_permissions.view_audit_log:
                try:
                    # Belleği temizle ve son logları çek
                    self._audit_cache = {k: v for k, v in self._audit_cache.items() if k[0] != message.guild.id}
                    async for entry in message.guild.audit_logs(action=discord.AuditLogAction.message_delete, limit=10):
                        self._audit_cache[(message.guild.id, entry.target.id, entry.extra.channel.id)] = entry.user
                    self._audit_cache_time[message.guild.id] = now
                    mod_user = self._audit_cache.get(cache_key)
                except Exception: pass

        # Veritabanına logla (DB logları discord kanalı olup olmamasından bağımsızdır)
        db_details = {
            "username": str(message.author.name),
            "avatar_url": message.author.display_avatar.url if message.author.display_avatar else None,
            "content": message.content,
            "mod_user_id": str(mod_user.id) if mod_user else None,
            "mod_username": str(mod_user.name) if mod_user else None
        }
        await self.bot.db.log_db_event(
            guild_id=message.guild.id,
            event_type="mod_msg_delete" if mod_user else "msg_delete",
            setting_key="msg_delete_on",
            user_id=str(message.author.id),
            details=db_details,
            channel_id=str(message.channel.id)
        )

        # Discord Log Gönderimi
        if mod_user and mod_discord_on:
            # Yetkili silmiş -> mod_channel
            target_channel_id = settings["mod_channel"]
            title = "🗑️ Üyenin Mesajı Silindi"
            color = discord.Color.brand_red()
            desc = f"{mod_user.mention} (`{mod_user.id}`) adlı yetkili, {message.author.mention} adlı kullanıcının {message.channel.mention} kanalındaki mesajını sildi."
        elif not mod_user and discord_on:
            # Kendi silmiş veya bulunamadı -> msg_channel
            target_channel_id = settings["msg_channel"]
            title = "🗑️ Mesaj Silindi"
            color = discord.Color.red()
            desc = f"{message.author.mention} kullanıcısının mesajı {message.channel.mention} kanalında silindi."
        else:
            # Discord embed logu kapalı
            target_channel_id = None

        if target_channel_id:
            log_channel = await self.get_log_channel(message.guild, int(target_channel_id))
            if log_channel:
                embed = discord.Embed(
                    title=title,
                    description=desc,
                    color=color,
                    timestamp=discord.utils.utcnow()
                )
                embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
                content = message.content[:1020] + "..." if len(message.content) > 1024 else message.content
                embed.add_field(name="İçerik", value=content, inline=False)
                embed.set_footer(text=f"Kullanıcı ID: {message.author.id} | Mesaj ID: {message.id}")
                
                try:
                    await log_channel.send(embed=embed)
                except discord.Forbidden:
                    log.warning(f"Log kanalına mesaj atılamadı: {log_channel.id} (Yetki yok)")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if not before.guild or before.author.bot:
            return

        if before.content == after.content:
            return

        settings = await self.get_log_settings(before.guild)
        discord_on = bool(settings and settings.get("msg_edit_on") == 1 and settings.get("msg_channel"))

        old_c = before.content[:1020] + "..." if len(before.content) > 1024 else (before.content or "*(İçerik Yok)*")
        new_c = after.content[:1020] + "..." if len(after.content) > 1024 else (after.content or "*(İçerik Yok)*")

        # Veritabanına logla
        db_details = {
            "username": str(before.author.name),
            "avatar_url": before.author.display_avatar.url if before.author.display_avatar else None,
            "old_content": before.content,
            "new_content": after.content,
            "message_url": after.jump_url
        }
        await self.bot.db.log_db_event(
            guild_id=before.guild.id,
            event_type="msg_edit",
            setting_key="msg_edit_on",
            user_id=str(before.author.id),
            details=db_details,
            channel_id=str(before.channel.id)
        )

        # Discord Log Gönderimi
        if discord_on:
            log_channel = await self.get_log_channel(before.guild, int(settings["msg_channel"]))
            if log_channel:
                embed = discord.Embed(
                    title="✏️ Mesaj Düzenlendi",
                    description=f"{before.author.mention} kullanıcısı {before.channel.mention} kanalındaki mesajını düzenledi. [Mesaja Git]({after.jump_url})",
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow()
                )
                embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
                embed.add_field(name="Eski Mesaj", value=old_c, inline=False)
                embed.add_field(name="Yeni Mesaj", value=new_c, inline=False)
                embed.set_footer(text=f"Kullanıcı ID: {before.author.id} | Mesaj ID: {before.id}")
                
                try:
                    await log_channel.send(embed=embed)
                except discord.Forbidden:
                    log.warning(f"Log kanalına mesaj atılamadı: {log_channel.id} (Yetki yok)")

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]) -> None:
        if not messages: return
        guild = messages[0].guild
        if not guild: return
        
        settings = await self.get_log_settings(guild)
        discord_on = bool(settings and settings.get("msg_delete_on") == 1 and settings.get("msg_channel"))

        if discord_on:
            log_channel = await self.get_log_channel(guild, int(settings["msg_channel"]))
            if log_channel:
                embed = discord.Embed(
                    title="🗑️ Toplu Mesaj Silindi",
                    description=f"{messages[0].channel.mention} kanalında {len(messages)} mesaj silindi.",
                    color=discord.Color.brand_red(),
                    timestamp=discord.utils.utcnow()
                )
                try:
                    await log_channel.send(embed=embed)
                except discord.Forbidden:
                    pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Messages(bot))
