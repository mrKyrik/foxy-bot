from __future__ import annotations
import logging
import discord
from discord.ext import commands
from core.checks import kumiho_check

log = logging.getLogger(__name__)

class Forums(commands.Cog):
    category = "Yönetim ve Ayarlar"
    category_emoji = "⚙️"
    """
    Forum yönetimi için prefix komutları.
    """

    def __init__(self, bot):
        self.category = "Diğer"
        self.bot = bot

    @commands.group(name="forum", invoke_without_command=True)
    @kumiho_check("owner")
    async def forum_group(self, ctx: commands.Context):
        """Forum sistemi kurulum menüsünü açar.\n**Kullanım:** `{prefix}forum`"""
        from Commands.administration.setup import ForumSetupView
        embed = discord.Embed(
            title="💬 Forum Sistemi Kurulumu",
            description="Sunucunuz için Forum Kanalları oluşturabilir, otomatik onay veya oto-mesaj sistemlerini aktif edebilirsiniz.",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed, view=ForumSetupView(self.bot))

    @commands.command(name="forum_olustur", aliases=["forumkur", "createforum"])
    @kumiho_check("owner")
    async def forum_olustur(self, ctx, *, isim: str):
        """Create a new forum channel.
        
        **Usage:** `{prefix}forum_olustur <name>`
        **Required Permission:** Server Owner or Administrator
        """
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
    @kumiho_check("owner")
    async def forum_mesaj(self, ctx, forum: discord.ForumChannel, baslik: str, *, icerik: str):
        """Create a new post (thread) in a forum channel.
        
        **Usage:** `{prefix}forum_mesaj <#forum-channel> "Title" <Content>`
        **Required Permission:** Server Owner or Administrator
        """
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
    @kumiho_check("owner")
    async def forum_sil(self, ctx, forum: discord.ForumChannel):
        """Delete an existing forum channel.
        
        **Usage:** `{prefix}forum_sil <#forum-channel>`
        **Required Permission:** Server Owner or Administrator
        """
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
