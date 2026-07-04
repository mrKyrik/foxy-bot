import logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

class Forums(commands.Cog):
    category = "Yönetim"
    """
    Forum yönetimi için prefix komutları.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="forum_olustur", aliases=["forumkur", "createforum"])
    @commands.has_permissions(manage_channels=True)
    async def forum_olustur(self, ctx, *, isim: str):
        """Yeni bir forum kanalı oluşturur. Kullanım: `!forum_olustur <isim>`"""
        try:
            forum_channel = await ctx.guild.create_forum_channel(name=isim)
            embed = discord.Embed(
                title="✅ Forum Oluşturuldu",
                description=f"Başarıyla {forum_channel.mention} adlı forum kanalı oluşturuldu.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ Bu işlemi gerçekleştirmek için yetkim yok.")
        except Exception as e:
            log.error(f"Forum oluşturma hatası: {e}")
            await ctx.send(f"❌ Bir hata oluştu: {e}")

    @commands.command(name="forum_mesaj", aliases=["forum_post", "forumpost"])
    @commands.has_permissions(manage_messages=True)
    async def forum_mesaj(self, ctx, forum: discord.ForumChannel, baslik: str, *, icerik: str):
        """Bir forum kanalına yeni bir post (başlık) açar. Kullanım: `!forum_mesaj #forum-kanalı "Başlık" İçerik`"""
        try:
            thread_with_message = await forum.create_thread(name=baslik, content=icerik)
            
            embed = discord.Embed(
                title="✅ Mesaj Gönderildi",
                description=f"Başarıyla {thread_with_message.thread.mention} adlı post oluşturuldu.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ Bu foruma mesaj göndermek için yetkim yok.")
        except Exception as e:
            log.error(f"Forum mesaj gönderme hatası: {e}")
            await ctx.send(f"❌ Bir hata oluştu: {e}")

    @commands.command(name="forum_sil", aliases=["forumkapat", "deleteforum"])
    @commands.has_permissions(manage_channels=True)
    async def forum_sil(self, ctx, forum: discord.ForumChannel):
        """Mevcut bir forum kanalını siler. Kullanım: `!forum_sil #forum-kanalı`"""
        try:
            await forum.delete()
            embed = discord.Embed(
                title="✅ Forum Silindi",
                description=f"Başarıyla `{forum.name}` adlı forum kanalı silindi.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ Bu forumu silmek için yetkim yok.")
        except Exception as e:
            log.error(f"Forum silme hatası: {e}")
            await ctx.send(f"❌ Bir hata oluştu: {e}")

async def setup(bot):
    await bot.add_cog(Forums(bot))
