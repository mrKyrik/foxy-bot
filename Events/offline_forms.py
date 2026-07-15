import discord
from discord.ext import commands, tasks
import time
import json
import logging
import re

log = logging.getLogger(__name__)

class OfflineForms(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.random_publish_loop.start()

    def cog_unload(self):
        self.random_publish_loop.cancel()

    @tasks.loop(seconds=30.0)
    async def random_publish_loop(self):
        """Her 30 saniyede bir çalışır ve publish_at süresi dolmuş formları yayınlar."""
        try:
            if not getattr(self.bot, 'db', None):
                return
            
            now = time.time()
            rows = await self.bot.db.fetchall("SELECT * FROM pending_offline_forms WHERE publish_mode='random' AND publish_at <= ?", now)
            
            for row in rows:
                await self._publish_form(row)
        except Exception as e:
            log.error("random_publish_loop hatası: %s", e)

    @random_publish_loop.before_loop
    async def before_random_publish_loop(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        """Kullanıcı offline olduğunda bekleyen formlarını yayınlar."""
        if before.status == after.status:
            return
            
        if after.status == discord.Status.offline:
            try:
                if not getattr(self.bot, 'db', None):
                    return
                
                rows = await self.bot.db.fetchall("SELECT * FROM pending_offline_forms WHERE publish_mode='offline' AND submitter_id=?", str(after.id))
                
                for row in rows:
                    await self._publish_form(row)
            except Exception as e:
                log.error("on_presence_update (offline forms) hatası: %s", e)

    async def _publish_form(self, row):
        try:
            guild_id = row["guild_id"]
            channel_id = row["channel_id"]
            embed_json_str = row["embed_json"]
            form_id = row["id"]
            
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                await self.bot.db.execute("DELETE FROM pending_offline_forms WHERE id=?", form_id)
                return
                
            channel = guild.get_channel(int(channel_id))
            if not channel:
                await self.bot.db.execute("DELETE FROM pending_offline_forms WHERE id=?", form_id)
                return
                
            embed_dict = json.loads(embed_json_str)
            embed = discord.Embed.from_dict(embed_dict)
            
            # Form ID'sini embedin footer'ından almaya çalışalım
            form_db_id = None
            if embed.footer and embed.footer.text:
                form_id_match = re.search(r'Form ID: (\S+)', embed.footer.text)
                if form_id_match:
                    form_db_id = form_id_match.group(1)
            
            # RACE CONDITION FIX: Try to delete the row first. If rowcount is 0, another event already processed it.
            async with self.bot.db.user_db.execute("DELETE FROM pending_offline_forms WHERE id=?", (form_id,)) as cursor:
                if cursor.rowcount == 0:
                    return # Zaten başka bir görev tarafından paylaşıldı
            await self.bot.db.user_db.commit()
            
            if form_db_id:
                # Orijinal trigger butonunu da ekleyelim
                pub_view = discord.ui.View()
                pub_view.add_item(discord.ui.Button(
                    label="İtiraf Et",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"trigger_btn_{form_db_id}"
                ))
                await channel.send(embed=embed, view=pub_view)
            else:
                await channel.send(embed=embed)
                
            log.info("Gecikmeli form başarıyla paylaşıldı: %s", form_id)
        except Exception as e:
            log.error("Form paylaşımında hata: %s", e)

async def setup(bot):
    await bot.add_cog(OfflineForms(bot))
