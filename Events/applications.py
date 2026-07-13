from __future__ import annotations
import logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

class ApplicationEvents(commands.Cog):
    """Forum kanallarındaki başvuru sonuçlarını (Tag değişimlerini) yakalayıp basvuru_log kanalına aktarır."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        row = await self.bot.db.fetchone("SELECT basvuru_channel FROM log_settings WHERE guild_id=?", str(guild.id))
        if not row or not row["basvuru_channel"]: return None
        try: return guild.get_channel(int(row["basvuru_channel"])) or await guild.fetch_channel(int(row["basvuru_channel"]))
        except: return None

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        # Sadece forum içindeki thread'leri dikkate al
        if not isinstance(after.parent, discord.ForumChannel):
            return

        # Tag değişimi kontrolü
        before_tags = set(before.applied_tags)
        after_tags = set(after.applied_tags)
        added_tags = after_tags - before_tags

        if not added_tags:
            return

        log_channel = await self.get_log_channel(after.guild)
        discord_on = bool(log_channel)

        for tag in added_tags:
            tag_name = tag.name.lower()
            if "kabul" in tag_name or "onay" in tag_name:
                if hasattr(self.bot, "db"):
                    await self.bot.db.log_db_event(
                        guild_id=after.guild.id, 
                        event_type="app_accept", 
                        setting_key="app_accept_on", 
                        user_id=str(after.owner_id), 
                        details={
                            "username": str(after.owner_id), # Sadece ID var elimizde, owner_id kullanıyoruz. UI'da isim resolve edilebilir.
                            "avatar_url": None,
                            "text": f"Başvuru Onaylandı\nBaşlık: {after.name}\nForum: {after.parent.name}"
                        }
                    )
                
                if discord_on:
                    embed = discord.Embed(
                        title="✅ Başvuru Onaylandı",
                        description=f"**Başvuru Başlığı:** {after.name}\n**Bağlantı:** {after.mention}\n**Forum:** {after.parent.mention}\n**Sahibi:** <@{after.owner_id}>",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    try: await log_channel.send(embed=embed)
                    except discord.Forbidden: pass
            
            elif "red" in tag_name or "iptal" in tag_name:
                if hasattr(self.bot, "db"):
                    await self.bot.db.log_db_event(
                        guild_id=after.guild.id, 
                        event_type="app_reject", 
                        setting_key="app_reject_on", 
                        user_id=str(after.owner_id), 
                        details={
                            "username": str(after.owner_id),
                            "avatar_url": None,
                            "text": f"Başvuru Reddedildi\nBaşlık: {after.name}\nForum: {after.parent.name}"
                        }
                    )

                if discord_on:
                    embed = discord.Embed(
                        title="❌ Başvuru Reddedildi",
                        description=f"**Başvuru Başlığı:** {after.name}\n**Bağlantı:** {after.mention}\n**Forum:** {after.parent.mention}\n**Sahibi:** <@{after.owner_id}>",
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )
                    try: await log_channel.send(embed=embed)
                    except discord.Forbidden: pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ApplicationEvents(bot))
