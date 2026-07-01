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
    Kanal:        create_channel, delete_channel
    Geçmiş:       modlogs
"""

import logging
from datetime import timedelta

import discord
from discord.ext import commands

from core.embed import EmbedBuilder
from Commands.administration.permission_check import has_permission, send_denied

log = logging.getLogger(__name__)


class Moderation(commands.Cog):
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

    # ==================================================================
    # Üye komutları
    # ==================================================================

    @commands.command()
    @has_permission("kick")
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

        if user.top_role.position >= ctx.author.top_role.position:
            return await ctx.send(embed=EmbedBuilder(
                title="⚠️ Hiyerarşi Hatası",
                description="Bu kullanıcının rolü sizinkiyle eşit ya da daha yüksek.",
                color=discord.Color.orange(),
            ).build())

        await user.kick(reason=reason)
        await self._log(ctx, "KICK", user.id, reason)

        embed = EmbedBuilder(
            title="👢 Kullanıcı Atıldı",
            description=f"{user.mention} sunucudan atıldı.\n**Sebep:** {reason}",
            color=discord.Color.green(),
        ).set_footer(f"İşlemi yapan: {ctx.author}").set_timestamp().build()
        await ctx.send(embed=embed)

    @commands.command()
    @has_permission("ban")
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

        if user.top_role.position >= ctx.author.top_role.position:
            return await ctx.send(embed=EmbedBuilder(
                title="⚠️ Hiyerarşi Hatası",
                description="Bu kullanıcının rolü sizinkiyle eşit ya da daha yüksek.",
                color=discord.Color.orange(),
            ).build())

        await user.ban(reason=reason)
        await self._log(ctx, "BAN", user.id, reason)

        embed = EmbedBuilder(
            title="🔨 Kullanıcı Banlandı",
            description=f"{user.mention} sunucudan banlandı.\n**Sebep:** {reason}",
            color=discord.Color.red(),
        ).set_footer(f"İşlemi yapan: {ctx.author}").set_timestamp().build()
        await ctx.send(embed=embed)

    @commands.command()
    @has_permission("ban")
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
    @has_permission("timeout")
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
        if user.top_role.position >= ctx.author.top_role.position:
            return await ctx.send(embed=EmbedBuilder(
                title="⚠️ Hiyerarşi Hatası",
                description="Bu kullanıcıyı susturamazsınız.",
                color=discord.Color.orange(),
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
    @has_permission("untimeout")
    @commands.bot_has_permissions(moderate_members=True)
    async def untimeout(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """
        Kullanıcının susturmasını kaldırır.
        Kullanım: `f.untimeout @kullanıcı [sebep]`
        """
        if user.top_role.position >= ctx.author.top_role.position:
            return await ctx.send(embed=EmbedBuilder(
                title="⚠️ Hiyerarşi Hatası",
                description="Bu kullanıcının susturmasını kaldıramazsınız.",
                color=discord.Color.orange(),
            ).build())

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
    @has_permission("purge")
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int) -> None:
        """
        Kanaldan belirtilen sayıda mesajı siler (komut mesajı dahil).
        Kullanım: `f.purge <miktar>`
        """
        if amount < 1 or amount > 500:
            return await ctx.send("❌ Miktar 1-500 arasında olmalıdır.")

        deleted = await ctx.channel.purge(limit=amount + 1)
        await self._log(ctx, "PURGE", ctx.channel.id, f"{len(deleted)-1} mesaj silindi")

        embed = EmbedBuilder(
            title="🗑️ Mesajlar Silindi",
            description=f"`{len(deleted)-1}` mesaj başarıyla silindi.",
            color=discord.Color.green(),
        ).set_timestamp().build()
        msg = await ctx.send(embed=embed)
        await msg.delete(delay=5)

    # ==================================================================
    # Uyarı sistemi
    # ==================================================================

    @commands.command()
    @has_permission("warn")
    async def warn(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """
        Kullanıcıya uyarı verir ve veritabanına kaydeder.
        Kullanım: `f.warn @kullanıcı [sebep]`
        """
        if user == ctx.author:
            return await ctx.send("❌ Kendinizi uyaramazsınız.")

        db = self.bot.db
        await db.execute(
            """
            INSERT INTO warns (guild_id, user_id, mod_id, reason)
            VALUES (?, ?, ?, ?)
            """,
            str(ctx.guild.id), str(user.id), str(ctx.author.id), reason,
        )
        await self._log(ctx, "WARN", user.id, reason)

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
    @has_permission("warn")
    async def warns(self, ctx: commands.Context, user: discord.Member) -> None:
        """
        Kullanıcının uyarı geçmişini gösterir.
        Kullanım: `f.warns @kullanıcı`
        """
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
    @has_permission("clearwarn")
    async def clearwarn(self, ctx: commands.Context, warn_id: int) -> None:
        """
        Belirtilen ID'li uyarıyı siler.
        Kullanım: `f.clearwarn <uyarı_id>`
        """
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
    @has_permission("voice_mute")
    @commands.bot_has_permissions(mute_members=True)
    async def vmute(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """Kullanıcıyı ses kanalında susturur. Kullanım: `f.vmute @kullanıcı [sebep]`"""
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
    @has_permission("voice_mute")
    @commands.bot_has_permissions(mute_members=True)
    async def vunmute(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """Kullanıcının ses susturmasını kaldırır. Kullanım: `f.vunmute @kullanıcı [sebep]`"""
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
    @has_permission("voice_deafen")
    @commands.bot_has_permissions(deafen_members=True)
    async def vdeafen(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """Kullanıcıyı ses kanalında sağırlaştırır. Kullanım: `f.vdeafen @kullanıcı [sebep]`"""
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
    @has_permission("voice_deafen")
    @commands.bot_has_permissions(deafen_members=True)
    async def vundeafen(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """Kullanıcının sağırlaştırmasını kaldırır. Kullanım: `f.vundeafen @kullanıcı [sebep]`"""
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
    @has_permission("voice_disconnect")
    @commands.bot_has_permissions(move_members=True)
    async def vdisconnect(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = "Belirtilmedi"
    ) -> None:
        """Kullanıcıyı ses kanalından atar. Kullanım: `f.vdisconnect @kullanıcı [sebep]`"""
        if not user.voice:
            return await ctx.send(embed=EmbedBuilder(
                title="❌ Ses Kanalında Değil", description="Kullanıcı bir ses kanalında yok.",
                color=discord.Color.red(),
            ).build())
        await user.move_to(None, reason=reason)
        await self._log(ctx, "VOICE_DISCONNECT", user.id, reason)
        await ctx.send(embed=EmbedBuilder(
            title="🚪 Ses Kanalından Atıldı",
            description=f"{user.mention} ses kanalından çıkarıldı.\n**Sebep:** {reason}",
            color=discord.Color.green(),
        ).set_timestamp().build())

    @commands.command()
    @has_permission("voice_move")
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
        if not user.voice:
            return await ctx.send(embed=EmbedBuilder(
                title="❌ Ses Kanalında Değil", description="Kullanıcı bir ses kanalında yok.",
                color=discord.Color.red(),
            ).build())
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
    @has_permission("create_channel")
    @commands.bot_has_permissions(manage_channels=True)
    async def create_channel(self, ctx: commands.Context, *, channel_name: str) -> None:
        """Yeni bir metin kanalı oluşturur. Kullanım: `f.create_channel <isim>`"""
        channel = await ctx.guild.create_text_channel(name=channel_name)
        await self._log(ctx, "CREATE_CHANNEL", channel.id, channel_name)
        await ctx.send(embed=EmbedBuilder(
            title="✅ Kanal Oluşturuldu",
            description=f"{channel.mention} başarıyla oluşturuldu.",
            color=discord.Color.green(),
        ).set_timestamp().build())

    @commands.command()
    @has_permission("delete_channel")
    @commands.bot_has_permissions(manage_channels=True)
    async def delete_channel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ) -> None:
        """Bir metin kanalını siler. Kullanım: `f.delete_channel #kanal`"""
        channel_id = channel.id
        channel_name = channel.name
        await channel.delete()
        await self._log(ctx, "DELETE_CHANNEL", channel_id, channel_name)
        await ctx.send(embed=EmbedBuilder(
            title="🗑️ Kanal Silindi",
            description=f"`#{channel_name}` kanalı silindi.",
            color=discord.Color.green(),
        ).set_timestamp().build())

    # ==================================================================
    # Mod log geçmişi
    # ==================================================================

    @commands.command(aliases=["history"])
    @commands.has_permissions(administrator=True)
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
    # Hata yönetimi
    # ==================================================================

    async def cog_command_error(
        self, ctx: commands.Context, error: Exception
    ) -> None:
        # has_permission tarafından fırlatılan CheckFailure — mesajı burada göster
        if isinstance(error, commands.CheckFailure) and not isinstance(
            error, commands.BotMissingPermissions
        ):
            perm_name = str(error) if str(error) else "unknown"
            await send_denied(ctx, perm_name)
            return

        if isinstance(error, commands.BotMissingPermissions):
            missing = ", ".join(error.missing_permissions)
            embed = EmbedBuilder(
                title="❌ Bot Yetkisi Eksik",
                description=f"Bu işlem için şu yetki(ler) gerekiyor: **{missing}**",
                color=discord.Color.red(),
            ).build()
            return await ctx.send(embed=embed)

        if isinstance(error, commands.MemberNotFound):
            embed = EmbedBuilder(
                title="❌ Üye Bulunamadı",
                description="Belirtilen kullanıcı bu sunucuda bulunamadı.",
                color=discord.Color.red(),
            ).build()
            return await ctx.send(embed=embed)

        log.error("Moderation cog hatası [%s]: %s", ctx.command, error, exc_info=error)
        embed = EmbedBuilder(
            title="❌ Beklenmeyen Hata",
            description=f"```py\n{error}```",
            color=discord.Color.dark_red(),
        ).build()
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
