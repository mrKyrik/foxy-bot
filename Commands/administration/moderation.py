from __future__ import annotations
"""
Commands/administration/moderation.py
--------------------------------------
Kapsamlı moderasyon komutları — tüm eylemler hem Python logging'e
hem ADMIN-EVENTS.db'ye kaydedilir.

Komutlar:
    Üye yönetimi: kick, ban, unban, timeout, untimeout
    Mesaj:        purge
    Uyarı:        warn, warns, clearwarn
    Ses:          vmute, vunmute, vdeafen, vundeafen, vdisconnect, vmove
    Kanal:        create_channel, delete_channel, nuke
    Geçmiş:       modlogs
"""

from core.checks import kumiho_check, kumiho_app_check
import logging
from datetime import timedelta

import discord
from discord.ext import commands

from core.embed import EmbedBuilder

log = logging.getLogger(__name__)


class Moderation(commands.Cog):
    category = "Moderasyon"
    """
    Sunucu moderasyon komutları. Tüm eylemler veritabanına loglanır.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------
    # İç yardımcı
    # ------------------------------------------------------------------
    async def _log(
        self,
        ctx: commands.Context,
        action_type: str,
        target_id: int,
        reason: str,
    ) -> None:
        """Eylemi Python log + ADMIN-EVENTS.db'ye kaydet."""
        # Master Log Architecture tetikleyici
        self.bot.dispatch("mod_action", ctx, action_type.lower(), target_id, reason)
        
        await ctx.bot.db.log_admin_event(
            guild_id=ctx.guild.id,
            admin_id=ctx.author.id,
            action_type=action_type,
            target_id=target_id,
            reason=reason,
        )

    async def can_moderate(self, ctx: commands.Context, user: discord.Member) -> bool:
        """Hiyerarşi ve bot yetkisi kontrolleri"""
        # Sunucu sahibi kontrolleri (Owner Bypass)
        if ctx.author.id == ctx.guild.owner_id:
            pass # Yapan sunucu sahibi ise her zaman geç
        elif user.id == ctx.guild.owner_id:
            await ctx.send(embed=EmbedBuilder(
                title="⚠️ Hiyerarşi Hatası",
                description="Sunucu sahibine işlem yapamazsınız.",
                color=discord.Color.orange(),
            ).build())
            return False
        elif user.top_role.position >= ctx.author.top_role.position:
            await ctx.send(embed=EmbedBuilder(
                title="⚠️ Hiyerarşi Hatası",
                description="Bu kullanıcının rolü sizinkiyle eşit ya da daha yüksek.",
                color=discord.Color.orange(),
            ).build())
            return False

        # Bot hiyerarşisi kontrolü
        if ctx.guild.me.top_role.position <= user.top_role.position and user.id != ctx.guild.owner_id:
            await ctx.send(embed=EmbedBuilder(
                title="❌ Bot Yetkisi Yetersiz",
                description="Benim rolüm bu kullanıcıdan daha düşük veya eşit olduğu için işlem yapamam.",
                color=discord.Color.red(),
            ).build())
            return False
            
        return True

    # ==================================================================
    # Üye komutları
    # ==================================================================

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(kick_members=True)
    async def kick(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """
        Kullanıcıyı sunucudan atar.
        Kullanım: `f.kick @kullanıcı [sebep]`
        """
        if user == ctx.author or user == self.bot.user:
            return await ctx.send(embed=EmbedBuilder(
                title="❌ İşlem Başarısız",
                description="Kendinizi veya botu atamazsınız.",
                color=discord.Color.red(),
            ).build())

        if not await self.can_moderate(ctx, user):
            return

        await user.kick(reason=reason)
        await self._log(ctx, "KICK", user.id, reason)

        embed = EmbedBuilder(
            title="👢 Kullanıcı Atıldı",
            description=f"{user.mention} sunucudan atıldı.\n**Sebep:** {reason}",
            color=discord.Color.green(),
        ).set_footer(f"İşlemi yapan: {ctx.author}").set_timestamp().build()
        await ctx.send(embed=embed)

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(ban_members=True)
    async def ban(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """
        Kullanıcıyı sunucudan banlar.
        Kullanım: `f.ban @kullanıcı [sebep]`
        """
        if user == ctx.author or user == self.bot.user:
            return await ctx.send(embed=EmbedBuilder(
                title="❌ İşlem Başarısız",
                description="Kendinizi veya botu banlayamazsınız.",
                color=discord.Color.red(),
            ).build())

        if not await self.can_moderate(ctx, user):
            return

        await user.ban(reason=reason)
        await self._log(ctx, "BAN", user.id, reason)

        embed = EmbedBuilder(
            title="🔨 Kullanıcı Banlandı",
            description=f"{user.mention} sunucudan banlandı.\n**Sebep:** {reason}",
            color=discord.Color.red(),
        ).set_footer(f"İşlemi yapan: {ctx.author}").set_timestamp().build()
        await ctx.send(embed=embed)

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(ban_members=True)
    async def unban(
        self, ctx: commands.Context, user_id: int, *, reason: str = "Belirtilmedi"
    ) -> None:
        """
        Kullanıcının banını kaldırır.
        Kullanım: `f.unban <kullanıcı_id> [sebep]`
        """
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=reason)
            await self._log(ctx, "UNBAN", user_id, reason)

            embed = EmbedBuilder(
                title="✅ Ban Kaldırıldı",
                description=f"**{user}** adlı kullanıcının banı kaldırıldı.\n**Sebep:** {reason}",
                color=discord.Color.green(),
            ).set_timestamp().build()
            await ctx.send(embed=embed)
        except discord.NotFound:
            await ctx.send(embed=EmbedBuilder(
                title="❌ Kullanıcı Bulunamadı",
                description=f"`{user_id}` ID'li kullanıcı banlar listesinde yok.",
                color=discord.Color.red(),
            ).build())

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: commands.Context,
        user: discord.Member,
        minutes: int,
        *,
        reason: str = "Belirtilmedi",
    ) -> None:
        """
        Kullanıcıyı belirtilen süre boyunca susturur.
        Kullanım: `f.timeout @kullanıcı <dakika> [sebep]`
        """
        if user == ctx.author or user == self.bot.user:
            return await ctx.send(embed=EmbedBuilder(title="❌ İşlem Başarısız", description="Kendinize veya bota işlem yapamazsınız.", color=discord.Color.red()).build())

        if not await self.can_moderate(ctx, user):
            return

        if minutes > 40320:
            return await ctx.send(embed=EmbedBuilder(
                title="❌ Sınır Aşıldı",
                description="Maksimum 28 gün (40320 dakika) susturabilirsiniz.",
                color=discord.Color.red()
            ).build())

        duration = timedelta(minutes=minutes)
        await user.timeout(duration, reason=reason)
        await self._log(ctx, "TIMEOUT", user.id, f"{minutes}dk | {reason}")

        embed = EmbedBuilder(
            title="⏱️ Kullanıcı Susturuldu",
            description=f"{user.mention} **{minutes} dakika** susturuldu.\n**Sebep:** {reason}",
            color=discord.Color.orange(),
        ).set_footer(f"İşlemi yapan: {ctx.author}").set_timestamp().build()
        await ctx.send(embed=embed)

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(moderate_members=True)
    async def untimeout(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """
        Kullanıcının susturmasını kaldırır.
        Kullanım: `f.untimeout @kullanıcı [sebep]`
        """
        if user == ctx.author or user == self.bot.user:
            return await ctx.send(embed=EmbedBuilder(title="❌ İşlem Başarısız", description="Kendinize veya bota işlem yapamazsınız.", color=discord.Color.red()).build())

        if not await self.can_moderate(ctx, user):
            return

        await user.timeout(None, reason=reason)
        await self._log(ctx, "UNTIMEOUT", user.id, reason)

        embed = EmbedBuilder(
            title="✅ Susturma Kaldırıldı",
            description=f"{user.mention} artık konuşabilir.\n**Sebep:** {reason}",
            color=discord.Color.green(),
        ).set_timestamp().build()
        await ctx.send(embed=embed)

    # ==================================================================
    # Mesaj komutları
    # ==================================================================

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int) -> None:
        """purge işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.purge [parametreler]`"""
        if amount < 1 or amount > 500:
            return await ctx.send("❌ Miktar 1-500 arasında olmalıdır.")

        try:
            deleted = await ctx.channel.purge(limit=amount + 1)
            await self._log(ctx, "PURGE", ctx.channel.id, f"{len(deleted)-1} mesaj silindi")

            embed = EmbedBuilder(
                title="🗑️ Mesajlar Silindi",
                description=f"`{len(deleted)-1}` mesaj başarıyla silindi.",
                color=discord.Color.green(),
            ).set_timestamp().build()
            msg = await ctx.send(embed=embed)
            await msg.delete(delay=5)
        except discord.HTTPException as e:
            await ctx.send(embed=EmbedBuilder(
                title="❌ İşlem Başarısız",
                description=f"Discord API Hatası (Muhtemelen 14 günden eski mesajları silmeye çalıştınız):\n`{e}`",
                color=discord.Color.red(),
            ).build())

    # ==================================================================
    # Uyarı sistemi
    # ==================================================================

    @commands.command()
    @kumiho_check("owner")
    async def warn(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """
        Kullanıcıya uyarı verir ve veritabanına kaydeder.
        Kullanım: `f.warn @kullanıcı [sebep]`
        """
        if user == ctx.author:
            return await ctx.send("❌ Kendinizi uyaramazsınız.")

        if not await self.can_moderate(ctx, user):
            return

        db = self.bot.db
        await db.execute(
            """
            INSERT INTO warns (guild_id, user_id, mod_id, reason)
            VALUES (?, ?, ?, ?)
            """,
            str(ctx.guild.id), str(user.id), str(ctx.author.id), reason[:1000],
        )
        await self._log(ctx, "WARN", user.id, reason[:1000])

        # Toplam uyarı sayısını al
        rows = await db.fetchall(
            "SELECT warn_id FROM warns WHERE guild_id=? AND user_id=?",
            str(ctx.guild.id), str(user.id),
        )
        total = len(rows)

        embed = EmbedBuilder(
            title="⚠️ Uyarı Verildi",
            description=f"{user.mention} uyarıldı.\n**Sebep:** {reason}\n**Toplam Uyarı:** {total}",
            color=discord.Color.yellow(),
        ).set_footer(f"İşlemi yapan: {ctx.author}").set_timestamp().build()
        await ctx.send(embed=embed)

    @commands.command(aliases=["warnlist"])
    @kumiho_check("owner")
    async def warns(self, ctx: commands.Context, user: discord.Member) -> None:
        """warns işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.warns [parametreler]`"""
        rows = await self.bot.db.fetchall(
            """
            SELECT warn_id, reason, mod_id, timestamp
            FROM warns
            WHERE guild_id=? AND user_id=?
            ORDER BY timestamp DESC
            """,
            str(ctx.guild.id), str(user.id),
        )

        if not rows:
            return await ctx.send(embed=EmbedBuilder(
                title=f"📋 {user.display_name} — Uyarılar",
                description="Bu kullanıcının uyarısı yok.",
                color=discord.Color.green(),
            ).build())

        description = ""
        for row in rows[:10]:  # En fazla 10 göster
            mod = ctx.guild.get_member(int(row["mod_id"])) or f"<@{row['mod_id']}>"
            description += (
                f"**#{row['warn_id']}** — {row['reason']}\n"
                f"› Yetkili: {mod} • {row['timestamp'][:10]}\n\n"
            )

        embed = EmbedBuilder(
            title=f"📋 {user.display_name} — Uyarılar ({len(rows)} toplam)",
            description=description.strip(),
            color=discord.Color.yellow(),
        ).build()
        await ctx.send(embed=embed)

    @commands.command()
    @kumiho_check("owner")
    async def clearwarn(self, ctx: commands.Context, warn_id: int) -> None:
        """Sistemdeki clearwarn kayıtlarını tamamen temizler. Kullanım: `f.clearwarn`"""
        row = await self.bot.db.fetchone(
            "SELECT user_id FROM warns WHERE warn_id=? AND guild_id=?",
            warn_id, str(ctx.guild.id),
        )

        if not row:
            return await ctx.send(embed=EmbedBuilder(
                title="❌ Bulunamadı",
                description=f"`#{warn_id}` numaralı uyarı bu sunucuda yok.",
                color=discord.Color.red(),
            ).build())

        await self.bot.db.execute(
            "DELETE FROM warns WHERE warn_id=?", warn_id
        )
        if hasattr(self.bot, "db"):
            await self.bot.db.log_db_event(ctx.guild.id, "warn_remove", "warn_remove_on", None, f"Uyarı Silindi (ID: {warn_id})\nYetkili: <@{ctx.author.id}>", None, ctx.author)
        await self._log(ctx, "CLEARWARN", int(row["user_id"]), f"warn#{warn_id}")

        embed = EmbedBuilder(
            title="✅ Uyarı Silindi",
            description=f"`#{warn_id}` numaralı uyarı kaldırıldı.",
            color=discord.Color.green(),
        ).set_timestamp().build()
        await ctx.send(embed=embed)

    # ==================================================================
    # Ses komutları
    # ==================================================================

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(mute_members=True)
    async def vmute(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """Kullanıcıyı ses kanalında susturur. Kullanım: `f.vmute @kullanıcı [sebep]`"""
        if user == ctx.author or user == self.bot.user:
            return await ctx.send(embed=EmbedBuilder(title="❌ İşlem Başarısız", description="Kendinize veya bota işlem yapamazsınız.", color=discord.Color.red()).build())
        if not await self.can_moderate(ctx, user):
            return
        if not user.voice:
            return await ctx.send(embed=EmbedBuilder(
                title="❌ Ses Kanalında Değil", description="Kullanıcı bir ses kanalında yok.",
                color=discord.Color.red(),
            ).build())
        await user.edit(mute=True, reason=reason)
        await self._log(ctx, "VOICE_MUTE", user.id, reason)
        await ctx.send(embed=EmbedBuilder(
            title="🔇 Ses Susturuldu",
            description=f"{user.mention} ses kanalında susturuldu.\n**Sebep:** {reason}",
            color=discord.Color.orange(),
        ).set_timestamp().build())

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(mute_members=True)
    async def vunmute(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """Kullanıcının ses susturmasını kaldırır. Kullanım: `f.vunmute @kullanıcı [sebep]`"""
        if user == ctx.author or user == self.bot.user:
            return await ctx.send(embed=EmbedBuilder(title="❌ İşlem Başarısız", description="Kendinize veya bota işlem yapamazsınız.", color=discord.Color.red()).build())
        if not await self.can_moderate(ctx, user):
            return
        if not user.voice:
            return await ctx.send(embed=EmbedBuilder(
                title="❌ Ses Kanalında Değil", description="Kullanıcı bir ses kanalında yok.",
                color=discord.Color.red(),
            ).build())
        await user.edit(mute=False, reason=reason)
        await self._log(ctx, "VOICE_UNMUTE", user.id, reason)
        await ctx.send(embed=EmbedBuilder(
            title="🔊 Ses Açıldı",
            description=f"{user.mention} ses susturması kaldırıldı.\n**Sebep:** {reason}",
            color=discord.Color.green(),
        ).set_timestamp().build())

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(deafen_members=True)
    async def vdeafen(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """Kullanıcıyı ses kanalında sağırlaştırır. Kullanım: `f.vdeafen @kullanıcı [sebep]`"""
        if user == ctx.author or user == self.bot.user:
            return await ctx.send(embed=EmbedBuilder(title="❌ İşlem Başarısız", description="Kendinize veya bota işlem yapamazsınız.", color=discord.Color.red()).build())
        if not await self.can_moderate(ctx, user):
            return
        if not user.voice:
            return await ctx.send(embed=EmbedBuilder(
                title="❌ Ses Kanalında Değil", description="Kullanıcı bir ses kanalında yok.",
                color=discord.Color.red(),
            ).build())
        await user.edit(deafen=True, reason=reason)
        await self._log(ctx, "VOICE_DEAFEN", user.id, reason)
        await ctx.send(embed=EmbedBuilder(
            title="🔕 Sağırlaştırıldı",
            description=f"{user.mention} ses kanalında sağırlaştırıldı.\n**Sebep:** {reason}",
            color=discord.Color.orange(),
        ).set_timestamp().build())

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(deafen_members=True)
    async def vundeafen(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """Kullanıcının sağırlaştırmasını kaldırır. Kullanım: `f.vundeafen @kullanıcı [sebep]`"""
        if user == ctx.author or user == self.bot.user:
            return await ctx.send(embed=EmbedBuilder(title="❌ İşlem Başarısız", description="Kendinize veya bota işlem yapamazsınız.", color=discord.Color.red()).build())
        if not await self.can_moderate(ctx, user):
            return
        if not user.voice:
            return await ctx.send(embed=EmbedBuilder(
                title="❌ Ses Kanalında Değil", description="Kullanıcı bir ses kanalında yok.",
                color=discord.Color.red(),
            ).build())
        await user.edit(deafen=False, reason=reason)
        await self._log(ctx, "VOICE_UNDEAFEN", user.id, reason)
        await ctx.send(embed=EmbedBuilder(
            title="🔔 Sağırlaştırma Kaldırıldı",
            description=f"{user.mention} artık sesi duyabilir.\n**Sebep:** {reason}",
            color=discord.Color.green(),
        ).set_timestamp().build())

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(move_members=True)
    async def vdisconnect(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """Kullanıcıyı ses kanalından atar. Kullanım: `f.vdisconnect @kullanıcı [sebep]`"""
        if user == ctx.author or user == self.bot.user:
            return await ctx.send(embed=EmbedBuilder(title="❌ İşlem Başarısız", description="Kendinize veya bota işlem yapamazsınız.", color=discord.Color.red()).build())
        if not await self.can_moderate(ctx, user):
            return
        if not user.voice or not user.voice.channel:
            return await ctx.send(embed=EmbedBuilder(
                title="❌ Ses Kanalında Değil", description="Kullanıcı bir ses kanalında yok.",
                color=discord.Color.red(),
            ).build())
        if not user.voice.channel.permissions_for(ctx.author).move_members:
            return await ctx.send(embed=EmbedBuilder(title="❌ Yetki Hatası", description="Kullanıcının bulunduğu ses kanalında üyeleri taşıma yetkiniz yok.", color=discord.Color.red()).build())
        await user.move_to(None, reason=reason)
        await self._log(ctx, "VOICE_DISCONNECT", user.id, reason)
        await ctx.send(embed=EmbedBuilder(
            title="🚪 Ses Kanalından Atıldı",
            description=f"{user.mention} ses kanalından çıkarıldı.\n**Sebep:** {reason}",
            color=discord.Color.green(),
        ).set_timestamp().build())

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(move_members=True)
    async def vmove(
        self,
        ctx: commands.Context,
        user: discord.Member,
        channel: discord.VoiceChannel,
        *,
        reason: str = "Belirtilmedi",
    ) -> None:
        """Kullanıcıyı başka bir ses kanalına taşır. Kullanım: `f.vmove @kullanıcı #kanal [sebep]`"""
        if user == ctx.author or user == self.bot.user:
            return await ctx.send(embed=EmbedBuilder(title="❌ İşlem Başarısız", description="Kendinize veya bota işlem yapamazsınız.", color=discord.Color.red()).build())
        if not await self.can_moderate(ctx, user):
            return
        if not user.voice or not user.voice.channel:
            return await ctx.send(embed=EmbedBuilder(
                title="❌ Ses Kanalında Değil", description="Kullanıcı bir ses kanalında yok.",
                color=discord.Color.red(),
            ).build())
        if not user.voice.channel.permissions_for(ctx.author).move_members:
            return await ctx.send(embed=EmbedBuilder(title="❌ Yetki Hatası", description="Kullanıcının bulunduğu ses kanalında üyeleri taşıma yetkiniz yok.", color=discord.Color.red()).build())
        if not channel.permissions_for(ctx.author).connect:
            return await ctx.send(embed=EmbedBuilder(title="❌ Yetki Hatası", description="Hedef ses kanalına bağlanma yetkiniz yok.", color=discord.Color.red()).build())
        await user.move_to(channel, reason=reason)
        await self._log(ctx, "VOICE_MOVE", user.id, f"→ #{channel.name} | {reason}")
        await ctx.send(embed=EmbedBuilder(
            title="📢 Kullanıcı Taşındı",
            description=f"{user.mention} → {channel.mention}\n**Sebep:** {reason}",
            color=discord.Color.green(),
        ).set_timestamp().build())

    # ==================================================================
    # Kanal komutları
    # ==================================================================

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(manage_channels=True)
    async def create_channel(self, ctx: commands.Context, *, channel_name: str) -> None:
        """create_channel işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.create_channel [parametreler]`"""
        channel = await ctx.guild.create_text_channel(name=channel_name)
        await self._log(ctx, "CREATE_CHANNEL", channel.id, channel_name)
        await ctx.send(embed=EmbedBuilder(
            title="✅ Kanal Oluşturuldu",
            description=f"{channel.mention} başarıyla oluşturuldu.",
            color=discord.Color.green(),
        ).set_timestamp().build())

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(manage_channels=True)
    async def delete_channel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ) -> None:
        """Bir metin kanalını siler. Kullanım: `f.delete_channel #kanal`"""
        if not channel.permissions_for(ctx.author).manage_channels:
            return await ctx.send(embed=EmbedBuilder(title="❌ Yetki Hatası", description="Bu kanalı silme yetkiniz yok.", color=discord.Color.red()).build())
        channel_id = channel.id
        channel_name = channel.name
        await channel.delete()
        await self._log(ctx, "DELETE_CHANNEL", channel_id, channel_name)
        await ctx.send(embed=EmbedBuilder(
            title="🗑️ Kanal Silindi",
            description=f"`#{channel_name}` kanalı silindi.",
            color=discord.Color.green(),
        ).set_timestamp().build())

    @commands.command()
    @kumiho_check("owner")
    @commands.bot_has_permissions(manage_channels=True)
    async def nuke(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """nuke işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.nuke [parametreler]`"""
        target_channel = channel or ctx.channel
        if not target_channel.permissions_for(ctx.author).manage_channels:
            return await ctx.send(embed=EmbedBuilder(title="❌ Yetki Hatası", description="Bu kanalı sıfırlama (nuke) yetkiniz yok.", color=discord.Color.red()).build())
        pos = target_channel.position

        new_channel = await target_channel.clone(reason=f"Nuke by {ctx.author}")
        await target_channel.delete(reason=f"Nuke by {ctx.author}")
        await new_channel.edit(position=pos)

        embed = EmbedBuilder(
            title="☢️ Kanal Sıfırlandı",
            description=f"Kanal **{ctx.author}** tarafından nukelendi.",
            color=discord.Color.red(),
        ).set_timestamp().build()
        await new_channel.send(embed=embed)
        await self._log(ctx, "NUKE", new_channel.id, f"Kanal sıfırlandı: {new_channel.name}")

    # ==================================================================
    # Mod log geçmişi
    # ==================================================================

    @commands.command(aliases=["history"])
    @kumiho_check("owner")
    async def modlogs(
        self,
        ctx: commands.Context,
        user: discord.Member | None = None,
        limit: int = 10,
    ) -> None:
        """
        Sunucunun mod eylem geçmişini gösterir.
        Kullanım: `f.modlogs [@kullanıcı] [limit]`
        """
        rows = await self.bot.db.fetch_admin_events(
            guild_id=ctx.guild.id,
            target_id=user.id if user else None,
            limit=min(limit, 25),
        )

        if not rows:
            return await ctx.send(embed=EmbedBuilder(
                title="📜 Mod Log",
                description="Hiçbir kayıt bulunamadı.",
                color=discord.Color.orange(),
            ).build())

        title = f"📜 Mod Log{f' — {user.display_name}' if user else ''}"
        description = ""
        for row in rows:
            admin = ctx.guild.get_member(int(row["admin_id"])) or f"<@{row['admin_id']}>"
            description += (
                f"**{row['action_type']}** • {row['timestamp'][:16]}\n"
                f"› Yetkili: {admin} • Hedef: <@{row['target_id']}>\n"
                f"› Sebep: {row['reason']}\n\n"
            )

        embed = EmbedBuilder(
            title=title,
            description=description.strip(),
            color=discord.Color.blurple(),
        ).set_footer(f"{len(rows)} kayıt gösteriliyor").build()
        await ctx.send(embed=embed)

    # ==================================================================
    # Son
    # ==================================================================


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
