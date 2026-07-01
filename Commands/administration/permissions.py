"""
Commands/administration/permissions.py
--------------------------------------
Sunucu bazlı bot içi rol izin yönetimi.

Yöneticiler bu komutlarla belirli Discord rollerine komut izni verebilir
ya da mevcut izinleri kaldırabilir. İzinler `USER-DB.db → role_permissions`
tablosunda saklanır.

Komutlar:
    f.grant @rol <izin>       — Role izin ver
    f.revoke @rol <izin>      — Rolden izin kaldır
    f.check_perms @rol         — Rolün izinlerini listele
    f.list_perms               — Tüm sunucu izinlerini listele
"""

import logging

import discord
from discord.ext import commands

from core.embed import EmbedBuilder

log = logging.getLogger(__name__)

# Geçerli izin adları — moderation.py ile senkronize tutulmalı
VALID_PERMISSIONS = {
    "kick", "ban", "timeout", "untimeout",
    "purge", "warn", "clearwarn",
    "create_channel", "delete_channel",
    "voice_mute", "voice_deafen", "voice_disconnect", "voice_move",
    "log",
}


class Permissions(commands.Cog):
    """
    Bot içi rol izin yönetimi. Rol bazlı komut erişim kontrolü için kullanılır.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------
    # grant
    # ------------------------------------------------------------------
    @commands.command(name="grant")
    @commands.has_permissions(administrator=True)
    async def grant(
        self, ctx: commands.Context, role: discord.Role, permission: str
    ) -> None:
        """
        Bir role bot komutu izni verir.
        Kullanım: `f.grant @rol <izin>`
        Örnek: `f.grant @Moderatör kick`
        """
        perm = permission.lower()

        if perm not in VALID_PERMISSIONS:
            valid_list = ", ".join(f"`{p}`" for p in sorted(VALID_PERMISSIONS))
            embed = EmbedBuilder(
                title="❌ Geçersiz İzin",
                description=f"Geçerli izinler:\n{valid_list}",
                color=discord.Color.red(),
            ).build()
            return await ctx.send(embed=embed)

        db = self.bot.db
        guild_id = str(ctx.guild.id)
        role_id = str(role.id)

        # Role kaydı yoksa ekle
        await db.execute(
            "INSERT OR IGNORE INTO roles (guild_id, role_id, role_name) VALUES (?, ?, ?)",
            guild_id, role_id, role.name,
        )

        # İzni ver
        try:
            await db.execute(
                "INSERT INTO role_permissions (guild_id, role_id, permission_name) VALUES (?, ?, ?)",
                guild_id, role_id, perm,
            )
            log.info("İzin verildi | guild=%s | role=%s | perm=%s", guild_id, role_id, perm)
            embed = EmbedBuilder(
                title="✅ İzin Verildi",
                description=f"{role.mention} rolüne `{perm}` izni başarıyla eklendi.",
                color=discord.Color.green(),
            ).set_timestamp().build()
        except Exception:
            # UNIQUE constraint — zaten var
            embed = EmbedBuilder(
                title="⚠️ Zaten Mevcut",
                description=f"{role.mention} rolünün `{perm}` izni zaten var.",
                color=discord.Color.orange(),
            ).build()

        await ctx.send(embed=embed)

    # ------------------------------------------------------------------
    # revoke
    # ------------------------------------------------------------------
    @commands.command(name="revoke")
    @commands.has_permissions(administrator=True)
    async def revoke(
        self, ctx: commands.Context, role: discord.Role, permission: str
    ) -> None:
        """
        Bir rolden bot komutu iznini kaldırır.
        Kullanım: `f.revoke @rol <izin>`
        """
        perm = permission.lower()
        db = self.bot.db
        guild_id = str(ctx.guild.id)
        role_id = str(role.id)

        # Önce var mı kontrol et
        row = await db.fetchone(
            "SELECT 1 FROM role_permissions WHERE guild_id=? AND role_id=? AND permission_name=?",
            guild_id, role_id, perm,
        )

        if not row:
            embed = EmbedBuilder(
                title="❌ İzin Bulunamadı",
                description=f"{role.mention} rolünde `{perm}` izni yok.",
                color=discord.Color.red(),
            ).build()
            return await ctx.send(embed=embed)

        await db.execute(
            "DELETE FROM role_permissions WHERE guild_id=? AND role_id=? AND permission_name=?",
            guild_id, role_id, perm,
        )
        log.info("İzin kaldırıldı | guild=%s | role=%s | perm=%s", guild_id, role_id, perm)

        embed = EmbedBuilder(
            title="✅ İzin Kaldırıldı",
            description=f"{role.mention} rolünden `{perm}` izni başarıyla kaldırıldı.",
            color=discord.Color.green(),
        ).set_timestamp().build()
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------
    # check_perms
    # ------------------------------------------------------------------
    @commands.command(name="check_perms")
    @commands.has_permissions(administrator=True)
    async def check_perms(
        self, ctx: commands.Context, role: discord.Role
    ) -> None:
        """
        Bir rolün sahip olduğu bot izinlerini listeler.
        Kullanım: `f.check_perms @rol`
        """
        db = self.bot.db
        guild_id = str(ctx.guild.id)
        role_id = str(role.id)

        rows = await db.fetchall(
            "SELECT permission_name FROM role_permissions WHERE guild_id=? AND role_id=?",
            guild_id, role_id,
        )

        if rows:
            perms_list = "\n".join(f"• `{row['permission_name']}`" for row in rows)
            embed = EmbedBuilder(
                title=f"🔐 {role.name} — İzinler",
                description=perms_list,
                color=discord.Color.blurple(),
            ).set_footer(f"Toplam {len(rows)} izin").build()
        else:
            embed = EmbedBuilder(
                title=f"🔐 {role.name} — İzinler",
                description="Bu rolün hiçbir bot izni yok.",
                color=discord.Color.orange(),
            ).build()

        await ctx.send(embed=embed)

    # ------------------------------------------------------------------
    # list_perms
    # ------------------------------------------------------------------
    @commands.command(name="list_perms")
    @commands.has_permissions(administrator=True)
    async def list_perms(self, ctx: commands.Context) -> None:
        """
        Sunucudaki tüm rol izinlerini listeler.
        Kullanım: `f.list_perms`
        """
        db = self.bot.db
        guild_id = str(ctx.guild.id)

        rows = await db.fetchall(
            """
            SELECT rp.role_id, rp.permission_name, r.role_name
            FROM role_permissions rp
            LEFT JOIN roles r ON rp.guild_id = r.guild_id AND rp.role_id = r.role_id
            WHERE rp.guild_id=?
            ORDER BY rp.role_id, rp.permission_name
            """,
            guild_id,
        )

        if not rows:
            embed = EmbedBuilder(
                title="🔐 Sunucu İzinleri",
                description="Bu sunucuda henüz hiçbir rol izni tanımlanmamış.\n"
                            "Eklemek için `f.grant @rol <izin>` kullan.",
                color=discord.Color.orange(),
            ).build()
            return await ctx.send(embed=embed)

        # Role göre gruplandır
        grouped: dict[str, list[str]] = {}
        for row in rows:
            role_name = row["role_name"] or f"<@&{row['role_id']}>"
            grouped.setdefault(role_name, []).append(row["permission_name"])

        description = ""
        for role_name, perms in grouped.items():
            description += f"**{role_name}**\n"
            description += " ".join(f"`{p}`" for p in perms) + "\n\n"

        embed = EmbedBuilder(
            title="🔐 Sunucu İzinleri",
            description=description.strip(),
            color=discord.Color.blurple(),
        ).set_footer(f"Toplam {len(rows)} izin atanmış").build()
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------
    # Hata yönetimi
    # ------------------------------------------------------------------
    async def cog_command_error(
        self, ctx: commands.Context, error: Exception
    ) -> None:
        if isinstance(error, commands.MissingPermissions):
            embed = EmbedBuilder(
                title="❌ Yetki Eksik",
                description="Bu komutları kullanmak için **Yönetici** yetkisine ihtiyacın var.",
                color=discord.Color.red(),
            ).build()
            await ctx.send(embed=embed)
            return

        if isinstance(error, commands.RoleNotFound):
            embed = EmbedBuilder(
                title="❌ Rol Bulunamadı",
                description="Belirtilen rol bulunamadı. Rol mention (@Rol) veya ID kullan.",
                color=discord.Color.red(),
            ).build()
            await ctx.send(embed=embed)
            return

        log.error("Permissions cog hatası [%s]: %s", ctx.command, error, exc_info=error)
        embed = EmbedBuilder(
            title="❌ Beklenmeyen Hata",
            description=f"```py\n{error}```",
            color=discord.Color.dark_red(),
        ).build()
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Permissions(bot))
