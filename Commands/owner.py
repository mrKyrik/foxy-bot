"""
Commands/owner.py
-----------------
Premium developer / sunucu sahibi komut paketi.

Ban sistemi artık JSON dosyaları yerine SQL tablosu kullanıyor:
  • bot_bans   → global bot yasakları
  • eco_bans   → ekonomi yasakları

Economy coin işlemleri Economy cog'u üzerinden yapılıyor.
"""

import logging
import os

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

_EXTRA_ADMINS = os.getenv("EXTRA_ADMIN_IDS", "")
_ALLOWED_IDS: frozenset[int] = frozenset(int(i.strip()) for i in _EXTRA_ADMINS.split(",") if i.strip().isdigit())


class Owner(commands.Cog):
    category = "Yönetim ve Ayarlar"
    """
    Premium developer and server owner command suite.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self):
        return self.bot.db

    # ── Auth check ────────────────────────────────────────────────────────────

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.author.id in _ALLOWED_IDS:
            return True

        owner_env = [o.strip() for o in (os.getenv("OWNER_ID") or "").split(",") if o.strip()]
        if str(ctx.author.id) in owner_env:
            return True

        try:
            if await self.bot.is_owner(ctx.author):
                return True
        except Exception:
            pass

        await ctx.send("❌ Only authorized bot owners can use this command suite.")
        return False

    # ── User resolver ─────────────────────────────────────────────────────────

    async def _resolve_user(self, ctx: commands.Context, target: str) -> tuple[str | None, str]:
        """Resolves mention, ID or username to (user_id_str, display_str)."""
        if not target:
            return None, ""
        cleaned = target.replace("<@", "").replace(">", "").replace("!", "").strip()
        if cleaned.isdigit():
            try:
                u = await self.bot.fetch_user(int(cleaned))
                return cleaned, u.mention
            except Exception:
                return cleaned, f"User (ID: {cleaned})"
        if ctx.guild:
            t_lower = target.lower()
            for m in ctx.guild.members:
                if t_lower in (m.name.lower(), m.display_name.lower()):
                    return str(m.id), m.mention
        return None, ""

    # ── Economy Admin Commands ────────────────────────────────────────────────

    @commands.command(name="givemoney", aliases=["ecogive", "mint"])
    async def givemoney(self, ctx: commands.Context, target: str = None, amount: int = None) -> None:
        """givemoney işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.givemoney [parametreler]`"""
        if not target or amount is None or amount <= 0:
            return await ctx.send(f"Usage: `{ctx.prefix}givemoney <@user/ID/username> <amount>`")

        user_id, mention = await self._resolve_user(ctx, target)
        if not user_id:
            return await ctx.send("❌ Could not resolve the specified user.")

        eco_cog = self.bot.get_cog("Economy")
        if eco_cog:
            await eco_cog.add_wallet(ctx.guild.id, int(user_id), amount)
        else:
            await self.db.execute(
                "INSERT OR IGNORE INTO economy (user_id, guild_id) VALUES (?, ?)",
                user_id, str(ctx.guild.id),
            )
            await self.db.execute(
                "UPDATE economy SET wallet=wallet+? WHERE user_id=? AND guild_id=?",
                amount, user_id, str(ctx.guild.id),
            )

        log.info("givemoney: %s coins → user %s by %s", amount, user_id, ctx.author.id)
        await ctx.send(f"✅ Added **{amount:,} coins** to {mention}'s wallet.")

    @commands.command(name="takemoney", aliases=["ecotake"])
    async def takemoney(self, ctx: commands.Context, target: str = None, amount: int = None) -> None:
        """takemoney işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.takemoney [parametreler]`"""
        if not target or amount is None or amount <= 0:
            return await ctx.send(f"Usage: `{ctx.prefix}takemoney <@user/ID/username> <amount>`")

        user_id, mention = await self._resolve_user(ctx, target)
        if not user_id:
            return await ctx.send("❌ Could not resolve the specified user.")

        await self.db.execute(
            "INSERT OR IGNORE INTO economy (user_id, guild_id) VALUES (?, ?)",
            user_id, str(ctx.guild.id),
        )
        await self.db.execute(
            "UPDATE economy SET wallet=MAX(0, wallet-?) WHERE user_id=? AND guild_id=?",
            amount, user_id, str(ctx.guild.id),
        )
        log.info("takemoney: %s coins ← user %s by %s", amount, user_id, ctx.author.id)
        await ctx.send(f"✅ Removed up to **{amount:,} coins** from {mention}'s wallet.")

    # ── Bot-wide Ban Commands (SQL) ───────────────────────────────────────────

    @commands.command(name="ecoban", aliases=["economyban"])
    async def ecoban(self, ctx: commands.Context, *, target: str = None) -> None:
        """ecoban işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.ecoban [parametreler]`"""
        if not target:
            return await ctx.send(f"Usage: `{ctx.prefix}ecoban <@user/ID/username>`")
        user_id, mention = await self._resolve_user(ctx, target)
        if not user_id:
            return await ctx.send("❌ Could not resolve the specified user.")

        await self._ensure_ban_tables()
        await self.db.execute(
            "INSERT OR IGNORE INTO eco_bans (user_id) VALUES (?)", user_id
        )
        log.info("ecoban: user %s banned by %s", user_id, ctx.author.id)
        await ctx.send(f"✅ Banned {mention} from the economy system.")

    @commands.command(name="ecounban", aliases=["economyunban"])
    async def ecounban(self, ctx: commands.Context, *, target: str = None) -> None:
        """ecounban işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.ecounban [parametreler]`"""
        if not target:
            return await ctx.send(f"Usage: `{ctx.prefix}ecounban <@user/ID/username>`")
        user_id, mention = await self._resolve_user(ctx, target)
        if not user_id:
            return await ctx.send("❌ Could not resolve the specified user.")

        await self._ensure_ban_tables()
        await self.db.execute("DELETE FROM eco_bans WHERE user_id=?", user_id)
        log.info("ecounban: user %s unbanned by %s", user_id, ctx.author.id)
        await ctx.send(f"✅ Unbanned {mention} from the economy system.")

    @commands.command(name="botban", aliases=["banbot"])
    async def botban(self, ctx: commands.Context, *, target: str = None) -> None:
        """botban işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.botban [parametreler]`"""
        if not target:
            return await ctx.send(f"Usage: `{ctx.prefix}botban <@user/ID/username>`")
        user_id, mention = await self._resolve_user(ctx, target)
        if not user_id:
            return await ctx.send("❌ Could not resolve the specified user.")

        await self._ensure_ban_tables()
        await self.db.execute(
            "INSERT OR IGNORE INTO bot_bans (user_id) VALUES (?)", user_id
        )
        log.info("botban: user %s banned by %s", user_id, ctx.author.id)
        await ctx.send(f"✅ Banned {mention} from the bot.")

    @commands.command(name="botunban", aliases=["unbanbot"])
    async def botunban(self, ctx: commands.Context, *, target: str = None) -> None:
        """botunban işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.botunban [parametreler]`"""
        if not target:
            return await ctx.send(f"Usage: `{ctx.prefix}botunban <@user/ID/username>`")
        user_id, mention = await self._resolve_user(ctx, target)
        if not user_id:
            return await ctx.send("❌ Could not resolve the specified user.")

        await self._ensure_ban_tables()
        await self.db.execute("DELETE FROM bot_bans WHERE user_id=?", user_id)
        log.info("botunban: user %s unbanned by %s", user_id, ctx.author.id)
        await ctx.send(f"✅ Unbanned {mention} from the bot.")

    # ── Ban table initializer ─────────────────────────────────────────────────

    @commands.command(name="sync")
    async def sync_tree(self, ctx: commands.Context) -> None:
        """sync işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.sync [parametreler]`"""
        try:
            # Sadece bu sunucuya anında senkronize et (hemen çalışması için)
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"✅ {len(synced)} adet slash (/) komutu bu sunucu ile senkronize edildi. (Anında geçerli)")
        except Exception as e:
            await ctx.send(f"❌ Senkronizasyon hatası: {e}")

    async def _ensure_ban_tables(self) -> None:
        await self.db.user_db.executescript("""
        CREATE TABLE IF NOT EXISTS bot_bans (
            user_id TEXT PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS eco_bans (
            user_id TEXT PRIMARY KEY
        );
        """)
        await self.db.user_db.commit()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Owner(bot))
