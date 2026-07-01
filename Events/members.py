"""
Events/members.py
-----------------
Üye giriş/çıkış olaylarını yönetir ve rol loglarını (rol_channel) tutar.
"""

import json
import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class Members(commands.Cog):
    """Üye giriş/çıkış olayları ve rol yönetimi."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        row = await self.bot.db.fetchone(
            "SELECT rol_channel FROM log_settings WHERE guild_id=?", str(guild.id)
        )
        if not row or not row["rol_channel"]: return None
        try:
            return guild.get_channel(int(row["rol_channel"])) or await guild.fetch_channel(int(row["rol_channel"]))
        except (ValueError, discord.NotFound, discord.Forbidden):
            return None

    async def get_mod_settings(self, guild: discord.Guild) -> tuple[discord.TextChannel | None, dict | None]:
        row = await self.bot.db.fetchone(
            "SELECT mod_channel, mod_role_on FROM log_settings WHERE guild_id=?", str(guild.id)
        )
        if not row or not row["mod_channel"]: return None, None
        try:
            channel = guild.get_channel(int(row["mod_channel"])) or await guild.fetch_channel(int(row["mod_channel"]))
            return channel, dict(row)
        except (ValueError, discord.NotFound, discord.Forbidden):
            return None, None

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        roles = [
            role.id
            for role in member.roles
            if role.name != "@everyone" and not role.managed
        ]

        if not roles:
            return

        db = self.bot.db
        guild_id = str(member.guild.id)
        user_id = str(member.id)

        await db.execute("DELETE FROM saved_roles WHERE user_id=? AND guild_id=?", user_id, guild_id)
        
        insert_data = [(user_id, guild_id, str(r)) for r in roles]
        await db.executemany(
            "INSERT INTO saved_roles (user_id, guild_id, role_id) VALUES (?, ?, ?)",
            insert_data
        )
        
        log_channel = await self.get_log_channel(member.guild)
        if log_channel:
            role_mentions = ", ".join([f"<@&{r_id}>" for r_id in roles])
            embed = discord.Embed(
                title="💾 Roller Hafızaya Kaydedildi",
                color=discord.Color.dark_grey(),
                timestamp=discord.utils.utcnow()
            )
            embed.description = f"**Kullanıcı:** {member.mention} ({member.id})\n**Ayrılma Sebebi:** Sunucudan ayrıldı."
            embed.add_field(name="Kaydedilen Roller", value=role_mentions[:1024], inline=False)
            embed.add_field(name="Kaydedilen Rol Sayısı", value=str(len(roles)), inline=True)
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        db = self.bot.db
        guild_id = str(member.guild.id)
        user_id = str(member.id)

        rows = await db.fetchall(
            "SELECT role_id FROM saved_roles WHERE user_id=? AND guild_id=?",
            user_id, guild_id,
        )

        if not rows:
            return

        role_ids = []
        for row in rows:
            if str(row["role_id"]).isdigit():
                role_ids.append(int(row["role_id"]))

        restored_mentions = []
        for role_id in role_ids:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Kaydedilmiş roller geri yüklendi")
                    restored_mentions.append(role.mention)
                except discord.HTTPException:
                    pass

        await db.execute("DELETE FROM saved_roles WHERE user_id=? AND guild_id=?", user_id, guild_id)

        log_channel = await self.get_log_channel(member.guild)
        if log_channel and restored_mentions:
            mentions_str = ", ".join(restored_mentions)
            embed = discord.Embed(
                title="💾 Roller Hafızadan Geri Yüklendi",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.description = f"**Kullanıcı:** {member.mention} ({member.id}) sunucuya geri döndü. Rol hafızası durumu:\n\n✅ **Geri Yüklenen Roller**\n{mentions_str[:1000]}"
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if len(before.roles) == len(after.roles):
            return

        log_channel, settings = await self.get_mod_settings(before.guild)
        discord_on = bool(settings and settings.get("mod_role_on") == 1 and log_channel)

        added_roles = [r for r in after.roles if r not in before.roles]
        removed_roles = [r for r in before.roles if r not in after.roles]

        if not added_roles and not removed_roles:
            return

        # Denetim kaydını (Audit Log) kontrol et
        mod_user = "Bilinmiyor / Kendi Seçimi"
        if before.guild.me.guild_permissions.view_audit_log:
            try:
                async for entry in before.guild.audit_logs(action=discord.AuditLogAction.member_role_update, limit=5):
                    if entry.target.id == after.id:
                        mod_user = f"{entry.user.mention} (`{entry.user.id}`)"
                        break
            except Exception:
                pass

        for role in added_roles:
            # DB logu (Şalter kontrolünü log_db_event yapıyor)
            await self.bot.db.log_db_event(
                guild_id=before.guild.id,
                event_type="role_add",
                setting_key="role_add_on",
                user_id=str(after.id),
                details={
                    "username": after.name,
                    "avatar_url": after.display_avatar.url if after.display_avatar else None,
                    "role_id": str(role.id),
                    "role_name": role.name,
                    "text": f"Rol Eklendi: {role.name}"
                },
            )

            # Discord embed logu
            if discord_on:
                embed = discord.Embed(
                    title="➕ Rol Eklendi",
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Üye", value=f"{after.mention} ({after.id})", inline=True)
                embed.add_field(name="Yetkili", value=mod_user, inline=True)
                embed.add_field(name="Eklenen Rol", value=role.mention, inline=False)
                try: await log_channel.send(embed=embed)
                except discord.Forbidden: pass

        for role in removed_roles:
            # DB logu
            await self.bot.db.log_db_event(
                guild_id=before.guild.id,
                event_type="role_remove",
                setting_key="role_remove_on",
                user_id=str(after.id),
                details={
                    "username": after.name,
                    "avatar_url": after.display_avatar.url if after.display_avatar else None,
                    "role_id": str(role.id),
                    "role_name": role.name,
                    "text": f"Rol Alındı: {role.name}"
                },
            )

            # Discord embed logu
            if discord_on:
                embed = discord.Embed(
                    title="➖ Rol Alındı",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Üye", value=f"{after.mention} ({after.id})", inline=True)
                embed.add_field(name="Yetkili", value=mod_user, inline=True)
                embed.add_field(name="Alınan Rol", value=role.mention, inline=False)
                try: await log_channel.send(embed=embed)
                except discord.Forbidden: pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Members(bot))
