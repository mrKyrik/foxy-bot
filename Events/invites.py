from __future__ import annotations
import logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

class InviteEvents(commands.Cog):
    """Davet takiplerini (Invite Tracker) yönetir ve davet loglarını (davet_channel) tutar."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.invites = {} # {guild_id: {invite_code: uses}}

    async def get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        row = await self.bot.db.fetchone("SELECT davet_channel FROM log_settings WHERE guild_id=?", str(guild.id))
        if not row or not row["davet_channel"]: return None
        try: return guild.get_channel(int(row["davet_channel"])) or await guild.fetch_channel(int(row["davet_channel"]))
        except: return None

    async def update_invites_cache(self, guild: discord.Guild):
        try:
            guild_invites = await guild.invites()
            self.invites[guild.id] = {invite.code: invite.uses for invite in guild_invites}
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self.update_invites_cache(guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.update_invites_cache(guild)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if invite.guild:
            await self.update_invites_cache(invite.guild)
            if hasattr(self.bot, "db"):
                await self.bot.db.log_db_event(invite.guild.id, "invite_create", "invite_create_on", str(invite.inviter.id) if invite.inviter else None, f"Davet Oluşturuldu: {invite.code}", None, invite.inviter)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        if invite.guild:
            await self.update_invites_cache(invite.guild)
            if hasattr(self.bot, "db"):
                await self.bot.db.log_db_event(invite.guild.id, "invite_create", "invite_create_on", str(invite.inviter.id) if invite.inviter else None, f"Davet Oluşturuldu: {invite.code}", None, invite.inviter)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        log_channel = await self.get_log_channel(member.guild)
        discord_on = bool(log_channel)

        # Eski davet cache'i ile yeni davetleri karşılaştır
        old_invites = self.invites.get(member.guild.id, {})
        try:
            new_invites = await member.guild.invites()
        except discord.Forbidden:
            new_invites = []

        used_invite = None
        for invite in new_invites:
            old_uses = old_invites.get(invite.code, 0)
            if invite.uses > old_uses:
                used_invite = invite
                break

        # Cache'i güncelle
        self.invites[member.guild.id] = {invite.code: invite.uses for invite in new_invites}

        embed = discord.Embed(
            title="📥 Yeni Üye Katıldı",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.description = f"**Katılan Üye:** {member.mention} (`{member.id}`)\nHoşgeldin!"

        if used_invite:
            inviter = used_invite.inviter
            inviter_str = f"{inviter.mention} (`{inviter.id}`)" if inviter else "Bilinmiyor"
            embed.add_field(name="Davet Eden", value=inviter_str, inline=False)
            embed.add_field(name="Davet Kodu", value=f"`{used_invite.code}`", inline=True)
            embed.add_field(name="Kullanım Sayısı", value=str(used_invite.uses), inline=True)
            if hasattr(self.bot, "db"):
                await self.bot.db.log_db_event(
                    guild_id=member.guild.id, 
                    event_type="invite_use", 
                    setting_key="invite_use_on", 
                    user_id=str(member.id), 
                    details={
                        "username": member.name,
                        "avatar_url": member.display_avatar.url if member.display_avatar else None,
                        "text": f"Davetle Katıldı\nDavet Eden: {inviter_str}\nKod: {used_invite.code}"
                    }
                )
        else:
            embed.add_field(name="Davet Eden", value="Bulunamadı (Vanity URL, Bot Daveti veya Widget olabilir)", inline=False)
            if hasattr(self.bot, "db"):
                await self.bot.db.log_db_event(
                    guild_id=member.guild.id, 
                    event_type="invite_use", 
                    setting_key="invite_use_on", 
                    user_id=str(member.id), 
                    details={
                        "username": member.name,
                        "avatar_url": member.display_avatar.url if member.display_avatar else None,
                        "text": "Kanala Katıldı (Davet Bulunamadı)"
                    }
                )

        if discord_on:
            try: await log_channel.send(embed=embed)
            except discord.Forbidden: pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(InviteEvents(bot))
