import logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

class ServerEvents(commands.Cog):
    """Sunucu ve Moderatör olaylarını yakalayıp ilgili log kanallarına iletir."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def get_log_settings(self, guild: discord.Guild) -> tuple[discord.TextChannel | None, discord.TextChannel | None, dict | None]:
        row = await self.bot.db.fetchone(
            "SELECT mod_channel, sunucu_channel, mod_channel_on, srv_role_on, srv_update_on, srv_emoji_on, srv_perm_on FROM log_settings WHERE guild_id=?", 
            str(guild.id)
        )
        if not row:
            return None, None, None
            
        mod_channel = None
        sunucu_channel = None
        
        if row["mod_channel"]:
            try:
                mod_channel = guild.get_channel(int(row["mod_channel"])) or await guild.fetch_channel(int(row["mod_channel"]))
            except: pass
            
        if row["sunucu_channel"]:
            try:
                sunucu_channel = guild.get_channel(int(row["sunucu_channel"])) or await guild.fetch_channel(int(row["sunucu_channel"]))
            except: pass

        return mod_channel, sunucu_channel, dict(row) if row else {}

    async def _get_audit_user(self, guild, action, target_id):
        if not guild.me.guild_permissions.view_audit_log:
            return "Bilinmiyor"
        try:
            async for entry in guild.audit_logs(action=action, limit=5):
                if entry.target.id == target_id:
                    return f"{entry.user.mention} (`{entry.user.id}`)"
        except: pass
        return "Bilinmiyor"

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        mod_channel, _, settings = await self.get_log_settings(channel.guild)
        db_row = await self.bot.db.fetchone("SELECT mod_channel_on FROM db_log_settings WHERE guild_id=?", str(channel.guild.id))
        db_on = bool(db_row and db_row[0] == 1)
        discord_on = bool(mod_channel and settings.get("mod_channel_on", 1))
        
        if not db_on and not discord_on: return
        
        mod_user = await self._get_audit_user(channel.guild, discord.AuditLogAction.channel_create, channel.id)

        if db_on:
            await self.bot.db.log_db_event(channel.guild.id, "mod_channel", "mod_channel_on", None, f"Kanal Oluşturuldu: <#{channel.id}>\nYetkili: {mod_user}")

        if discord_on:
            embed = discord.Embed(
                title="➕ Kanal Oluşturuldu",
                description=f"**Kanal:** {channel.mention}\n**Kanal Tipi:** {type(channel).__name__}\n**Oluşturan Yetkili:** {mod_user}",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Kanal ID: {channel.id}")
            await self._send_log(mod_channel, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        mod_channel, _, settings = await self.get_log_settings(channel.guild)
        db_row = await self.bot.db.fetchone("SELECT mod_channel_on FROM db_log_settings WHERE guild_id=?", str(channel.guild.id))
        db_on = bool(db_row and db_row[0] == 1)
        discord_on = bool(mod_channel and settings.get("mod_channel_on", 1))
        
        if not db_on and not discord_on: return
        
        mod_user = await self._get_audit_user(channel.guild, discord.AuditLogAction.channel_delete, channel.id)

        if db_on:
            await self.bot.db.log_db_event(channel.guild.id, "mod_channel", "mod_channel_on", None, f"Kanal Silindi: {channel.name}\nYetkili: {mod_user}")

        if discord_on:
            embed = discord.Embed(
                title="➖ Kanal Silindi",
                description=f"**Kanal Adı:** {channel.name}\n**Kanal Tipi:** {type(channel).__name__}\n**Silen Yetkili:** {mod_user}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Kanal ID: {channel.id}")
            await self._send_log(mod_channel, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel) -> None:
        mod_channel, sunucu_channel, settings = await self.get_log_settings(before.guild)
        
        # İsmi Değişti -> mod_channel
        if before.name != after.name:
            mod_user = await self._get_audit_user(before.guild, discord.AuditLogAction.channel_update, after.id)
            await self.bot.db.log_db_event(before.guild.id, "mod_channel", "mod_channel_on", None, f"Kanal İsmi Güncellendi: <#{after.id}>\nEski: {before.name}\nYeni: {after.name}\nYetkili: {mod_user}")
            if mod_channel and settings.get("mod_channel_on", 1):
                embed = discord.Embed(
                    title="✏️ Kanal İsmi Güncellendi",
                    description=f"**Kanal:** {after.mention}\n**Eski İsim:** {before.name}\n**Yeni İsim:** {after.name}\n**Düzenleyen Yetkili:** {mod_user}",
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text=f"Kanal ID: {after.id}")
                await self._send_log(mod_channel, embed)

        # İzinleri Değişti -> sunucu_channel
        if before.overwrites != after.overwrites:
            mod_user = "Bilinmiyor"
            if before.guild.me.guild_permissions.view_audit_log:
                try:
                    async for entry in before.guild.audit_logs(limit=5):
                        if entry.action in [discord.AuditLogAction.overwrite_create, discord.AuditLogAction.overwrite_update, discord.AuditLogAction.overwrite_delete]:
                            if entry.target.id == after.id:
                                mod_user = f"{entry.user.mention} (`{entry.user.id}`)"
                                break
                except: pass
            
            await self.bot.db.log_db_event(before.guild.id, "srv_perm", "srv_perm_on", None, f"Kanal İzinleri Güncellendi: <#{after.id}>\nYetkili: {mod_user}")

            if sunucu_channel and settings.get("srv_perm_on", 1):
                embed = discord.Embed(
                    title="🔐 Kanal İzinleri Güncellendi",
                    description=f"**Kanal:** {after.mention}\n**Düzenleyen Yetkili:** {mod_user}",
                    color=discord.Color.dark_theme(),
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text=f"Kanal ID: {after.id}")
                await self._send_log(sunucu_channel, embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        _, sunucu_channel, settings = await self.get_log_settings(role.guild)
        mod_user = await self._get_audit_user(role.guild, discord.AuditLogAction.role_create, role.id)
        
        await self.bot.db.update_role_cache(str(role.guild.id), str(role.id), role.name)
        await self.bot.db.log_db_event(role.guild.id, "srv_role", "srv_role_on", None, f"Rol Oluşturuldu: {role.name}\nYetkili: {mod_user}")
        
        if sunucu_channel and settings.get("srv_role_on", 1):
            embed = discord.Embed(
                title="➕ Yeni Rol Oluşturuldu",
                description=f"**Rol:** {role.mention}\n**Rol Rengi:** {role.color}\n**Oluşturan Yetkili:** {mod_user}",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Rol ID: {role.id}")
            await self._send_log(sunucu_channel, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        _, sunucu_channel, settings = await self.get_log_settings(role.guild)
        mod_user = await self._get_audit_user(role.guild, discord.AuditLogAction.role_delete, role.id)
        
        await self.bot.db.log_db_event(role.guild.id, "srv_role", "srv_role_on", None, f"Rol Silindi: {role.name}\nYetkili: {mod_user}")

        if sunucu_channel and settings.get("srv_role_on", 1):
            embed = discord.Embed(
                title="➖ Rol Silindi",
                description=f"**Rol Adı:** {role.name}\n**Silen Yetkili:** {mod_user}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Rol ID: {role.id}")
            await self._send_log(sunucu_channel, embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        _, sunucu_channel, settings = await self.get_log_settings(before)

        if before.name != after.name:
            mod_user = await self._get_audit_user(before, discord.AuditLogAction.guild_update, before.id)
            await self.bot.db.log_db_event(before.id, "srv_update", "srv_update_on", None, f"Sunucu İsmi Güncellendi\nEski: {before.name}\nYeni: {after.name}\nYetkili: {mod_user}")
            if sunucu_channel and settings.get("srv_update_on", 1):
                embed = discord.Embed(
                    title="⚙️ Sunucu İsmi Güncellendi",
                    description=f"**Eski İsim:** {before.name}\n**Yeni İsim:** {after.name}\n**Düzenleyen Yetkili:** {mod_user}",
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow()
                )
                await self._send_log(sunucu_channel, embed)
            
        if before.icon != after.icon:
            mod_user = await self._get_audit_user(before, discord.AuditLogAction.guild_update, before.id)
            await self.bot.db.log_db_event(before.id, "srv_update", "srv_update_on", None, f"Sunucu İkonu Güncellendi\nYetkili: {mod_user}")
            if sunucu_channel and settings.get("srv_update_on", 1):
                embed = discord.Embed(
                    title="🖼️ Sunucu İkonu Güncellendi",
                    description=f"**Düzenleyen Yetkili:** {mod_user}",
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow()
                )
                if after.icon: embed.set_thumbnail(url=after.icon.url)
                await self._send_log(sunucu_channel, embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before, after) -> None:
        _, sunucu_channel, settings = await self.get_log_settings(guild)

        added_emojis = [e for e in after if e not in before]
        removed_emojis = [e for e in before if e not in after]

        if added_emojis:
            mod_user = await self._get_audit_user(guild, discord.AuditLogAction.emoji_create, added_emojis[0].id)
            for emoji in added_emojis:
                await self.bot.db.log_db_event(guild.id, "srv_emoji", "srv_emoji_on", None, f"Emoji Eklendi: {emoji.name}\nYetkili: {mod_user}")
                if sunucu_channel and settings.get("srv_emoji_on", 1):
                    embed = discord.Embed(
                        title="😀 Emoji Eklendi",
                        description=f"**Emoji:** {emoji} (`{emoji.name}`)\n**Ekleyen Yetkili:** {mod_user}",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    if emoji.url: embed.set_thumbnail(url=emoji.url)
                    await self._send_log(sunucu_channel, embed)

        if removed_emojis:
            mod_user = await self._get_audit_user(guild, discord.AuditLogAction.emoji_delete, removed_emojis[0].id)
            for emoji in removed_emojis:
                await self.bot.db.log_db_event(guild.id, "srv_emoji", "srv_emoji_on", None, f"Emoji Silindi: {emoji.name}\nYetkili: {mod_user}")
                if sunucu_channel and settings.get("srv_emoji_on", 1):
                    embed = discord.Embed(
                        title="😢 Emoji Silindi",
                        description=f"**Emoji Adı:** `{emoji.name}`\n**Silen Yetkili:** {mod_user}",
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )
                    if emoji.url: embed.set_thumbnail(url=emoji.url)
                    await self._send_log(sunucu_channel, embed)

    async def _send_log(self, channel: discord.TextChannel, embed: discord.Embed):
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            log.warning(f"Sunucu log kanalına mesaj atılamadı: {channel.id}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ServerEvents(bot))
