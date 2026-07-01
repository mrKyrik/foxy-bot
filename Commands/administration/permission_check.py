"""
Commands/administration/permission_check.py
-------------------------------------------
Özel Discord rol bazlı izin sistemi.

Her sunucu için roller ve bu rollere atanmış izinler `USER-DB.db` → `role_permissions`
tablosunda saklanır. Bu modül, komutların başına eklenen `@has_permission("kick")`
gibi decorator'ları sağlar.

Kullanım:
    from Commands.administration.permission_check import has_permission

    class Moderation(commands.Cog):
        @commands.command()
        @has_permission("kick")
        async def kick(self, ctx, user: discord.Member, *, reason="Belirtilmedi"):
            ...

ÖNEMLI: predicate hiçbir zaman ctx.send() çağırmaz.
Mesaj gönderme sorumluluğu cog_command_error'a aittir.
Bu sayede filter_commands() (f.help) sırasında spam olmaz.
"""

import logging

import discord
from discord.ext import commands

from core.embed import EmbedBuilder

log = logging.getLogger(__name__)


def has_permission(perm_name: str):
    """
    Kullanıcının rollerinden herhangi birinin verilen izne sahip olup olmadığını
    `USER-DB.db → role_permissions` tablosundan async olarak kontrol eden decorator.

    Yetki yoksa CheckFailure(perm_name) raise eder — mesaj göndermez.
    Mesaj gönderme cog_command_error'a bırakılmıştır.

    Args:
        perm_name: İzin adı (örn. "kick", "ban", "timeout")

    Returns:
        commands.check decorator'ı
    """

    async def predicate(ctx: commands.Context) -> bool:
        # DM'de çalışmaz
        if not ctx.guild:
            raise commands.CheckFailure("no_guild")

        db = ctx.bot.db
        guild_id = str(ctx.guild.id)
        user_role_ids = [str(role.id) for role in ctx.author.roles]

        # Sunucu sahibi, Discord Yöneticisi veya Bot Sahibi (601344424429092864) ise direkt izin ver.
        if (
            ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
            or ctx.author.id == 601344424429092864
        ):
            return True

        if not user_role_ids:
            raise commands.CheckFailure(perm_name)

        # Kullanıcının rollerinden herhangi biri bu izne sahip mi?
        placeholders = ",".join(["?"] * len(user_role_ids))
        row = await db.fetchone(
            f"""
            SELECT 1
            FROM role_permissions
            WHERE guild_id = ?
              AND permission_name = ?
              AND role_id IN ({placeholders})
            LIMIT 1
            """,
            guild_id,
            perm_name,
            *user_role_ids,
        )

        if row:
            log.debug(
                "İzin onaylandı | guild=%s | user=%s | perm=%s",
                guild_id,
                ctx.author.id,
                perm_name,
            )
            return True

        # Yetki yok — sadece exception, mesaj yok
        raise commands.CheckFailure(perm_name)

    return commands.check(predicate)

async def setup(bot: commands.Bot) -> None:
    pass

async def send_denied(ctx: commands.Context, perm_name: str) -> None:
    """
    İzin reddedildiğinde kullanıcıya embed ile bildir.
    cog_command_error tarafından çağrılır.
    """
    if perm_name == "no_guild":
        await ctx.send("❌ Bu komut sadece sunucularda kullanılabilir.")
        return

    embed = (
        EmbedBuilder(
            title="❌ Yetki Reddedildi",
            description=(
                f"Bu komutu kullanabilmek için rollerinden birinin "
                f"`{perm_name}` iznine sahip olması gerekiyor.\n\n"
                f"Sunucu yöneticisi izin vermek için `f.grant @rol {perm_name}` komutunu kullanabilir."
            ),
            color=discord.Color.red(),
        )
        .set_footer("Azalea İzin Sistemi")
        .build()
    )
    await ctx.send(embed=embed)
