from __future__ import annotations
"""
Commands/suggestions.py
------------------------
Sunucu bazlı öneri kartı, oylama ve inceleme sistemi.

Veri depolama: SQLite USER-DB.db (suggestions, suggestion_config)
"""

from core.checks import kumiho_check, kumiho_app_check
import asyncio
import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class Suggestions(commands.Cog):
    category = "Topluluk ve Etkileşim"
    category_emoji = "👥"
    """
    State-of-the-art server-scoped suggestion cards voting and reviewing system.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.group(name="suggest", invoke_without_command=True)
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def suggest(self, ctx: commands.Context, *, text: str = None) -> None:
        """Submit a suggestion to the server.

**Usage:** `{prefix}suggest <text>`"""
        if not text:
            if ctx.author.guild_permissions.manage_guild:
                from Commands.administration.setup import SuggestionSetupView
                embed = discord.Embed(
                    title="💡 Öneri Sistemi Kurulumu",
                    description="Öneri kanalını tek bir tıkla aşağıdan hızlıca ayarlayabilirsiniz.",
                    color=discord.Color.blurple()
                )
                return await ctx.send(embed=embed, view=SuggestionSetupView(self.bot))
            return await ctx.send(f"Usage: `{ctx.prefix}suggest <your suggestion text>`")

        g_id = str(ctx.guild.id)
        
        row = await self.bot.db.fetchone("SELECT channel_id FROM suggestion_config WHERE guild_id=?", g_id)
        if not row or not row["channel_id"]:
            return await ctx.send(
                "❌ No suggestions channel configured! Ask an admin: `f.suggest channel #kanal`"
            )

        chan_id = int(row["channel_id"])
        chan = ctx.guild.get_channel(chan_id)
        if not chan:
            return await ctx.send("❌ Configured suggestions channel could not be found.")

        await self.bot.db.execute(
            "INSERT INTO suggestions (guild_id, author_id, text, status, reason) VALUES (?, ?, ?, ?, ?)",
            g_id, str(ctx.author.id), text, "pending", ""
        )
        
        s_id_row = await self.bot.db.fetchone(
            "SELECT suggestion_id FROM suggestions WHERE guild_id=? AND author_id=? ORDER BY suggestion_id DESC LIMIT 1",
            g_id, str(ctx.author.id)
        )
        s_id = s_id_row["suggestion_id"]

        embed = discord.Embed(
            title=f"💡 Suggestion #{s_id}",
            description=text,
            color=discord.Color.yellow(),
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Status", value="🕐 Pending Review", inline=False)
        embed.set_footer(text="React with 👍 or 👎 to vote!")

        try:
            msg = await chan.send(embed=embed)
            await msg.add_reaction("👍")
            await msg.add_reaction("👎")
        except Exception as e:
            log.error("Öneri gönderilemedi: %s", e)
            return await ctx.send(f"❌ Failed to post suggestion: {e}")

        await self.bot.db.execute("UPDATE suggestions SET message_id=? WHERE suggestion_id=?", str(msg.id), s_id)

        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.send(
            f"✅ Successfully submitted suggestion #{s_id} in {chan.mention}!",
            delete_after=5,
        )

    @suggest.command(name="channel")
    @kumiho_check("owner")
    async def suggest_channel(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ) -> None:
        """Sets the server suggestions channel. Usage: `f.suggest channel #kanal`"""
        if not channel:
            return await ctx.send(f"Usage: `{ctx.prefix}suggest channel <#channel>`")
        
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO suggestion_config (guild_id, channel_id) VALUES (?, ?)",
            str(ctx.guild.id), str(channel.id)
        )
        await ctx.send(f"✅ Suggestion board channel set to {channel.mention}.")

    async def _update_status(
        self,
        ctx: commands.Context,
        suggestion_id: int,
        status: str,
        color: discord.Color,
        status_text: str,
        reason: str,
    ) -> None:
        g_id = str(ctx.guild.id)
        
        sg = await self.bot.db.fetchone("SELECT * FROM suggestions WHERE guild_id=? AND suggestion_id=?", g_id, suggestion_id)
        if not sg:
            return await ctx.send("❌ Suggestion not found in database.")

        conf = await self.bot.db.fetchone("SELECT channel_id FROM suggestion_config WHERE guild_id=?", g_id)
        chan_id = conf["channel_id"] if conf else None
        chan = ctx.guild.get_channel(int(chan_id)) if chan_id else None
        if not chan:
            return await ctx.send("❌ Suggestions board channel not found.")

        try:
            msg = await chan.fetch_message(int(sg["message_id"]))
        except Exception:
            return await ctx.send("❌ Original suggestion message not found.")

        await self.bot.db.execute("UPDATE suggestions SET status=?, reason=? WHERE suggestion_id=?", status, reason, suggestion_id)

        author_id = int(sg["author_id"])
        author = ctx.guild.get_member(author_id)
        author_name = author.name if author else f"ID: {author_id}"

        embed = discord.Embed(
            title=f"💡 Suggestion #{suggestion_id}",
            description=sg["text"],
            color=color,
        )
        embed.set_author(
            name=author_name,
            icon_url=author.display_avatar.url if author else None,
        )
        embed.add_field(name="Status", value=status_text, inline=False)
        if reason:
            embed.add_field(name="Staff Feedback", value=reason, inline=False)

        await msg.edit(embed=embed)
        await ctx.send(
            f"✅ Marked suggestion #{suggestion_id} as **{status.upper()}**."
        )

    @suggest.command(name="approve")
    @kumiho_check("owner")
    async def suggest_approve(
        self, ctx: commands.Context, suggestion_id: int = None, *, reason: str = ""
    ) -> None:
        """Approves a suggestion. Usage: `f.suggest approve <id> [reason]`"""
        if suggestion_id is None:
            return await ctx.send(f"Usage: `{ctx.prefix}suggest approve <id> [reason]`")
        await self._update_status(
            ctx, suggestion_id, "approved", discord.Color.green(), "✅ Approved", reason
        )

    @suggest.command(name="deny")
    @kumiho_check("owner")
    async def suggest_deny(
        self, ctx: commands.Context, suggestion_id: int = None, *, reason: str = ""
    ) -> None:
        """Denies a suggestion. Usage: `f.suggest deny <id> [reason]`"""
        if suggestion_id is None:
            return await ctx.send(f"Usage: `{ctx.prefix}suggest deny <id> [reason]`")
        await self._update_status(
            ctx, suggestion_id, "denied", discord.Color.red(), "❌ Denied", reason
        )

    @suggest.command(name="consider")
    @kumiho_check("owner")
    async def suggest_consider(
        self, ctx: commands.Context, suggestion_id: int = None, *, reason: str = ""
    ) -> None:
        """Marks suggestion as under consideration. Usage: `f.suggest consider <id> [reason]`"""
        if suggestion_id is None:
            return await ctx.send(f"Usage: `{ctx.prefix}suggest consider <id> [reason]`")
        await self._update_status(
            ctx,
            suggestion_id,
            "considered",
            discord.Color.blue(),
            "🔵 In Consideration",
            reason,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Suggestions(bot))
