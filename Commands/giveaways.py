"""
Commands/giveaways.py
---------------------
Sunucu bazlı, arka planda çalışan otomatik çekiliş sistemi.

Veri depolama: Data/giveaways.json
(çekiliş verileri JSON'da kalır — anlık, geçici veridir)
"""

import logging
import random
import time
from pathlib import Path

import discord
from discord.ext import commands, tasks

from core.utils import json_load, json_save, parse_duration

log = logging.getLogger(__name__)

DB_FILE = Path("Data/giveaways.json")


def _load() -> dict:
    data = json_load(DB_FILE)
    data.setdefault("active", [])
    data.setdefault("history", [])
    return data


class Giveaways(commands.Cog):
    """
    State-of-the-art server-scoped background task-loop automated giveaways system.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.check_active_giveaways.start()

    def cog_unload(self) -> None:
        self.check_active_giveaways.cancel()

    @tasks.loop(seconds=10.0)
    async def check_active_giveaways(self) -> None:
        await self.bot.wait_until_ready()
        data = _load()
        active_list = data.get("active", [])
        if not active_list:
            return

        now = time.time()
        updated_active = []
        changed = False

        for gw in active_list:
            if now >= gw["end_time"]:
                changed = True
                await self._end_giveaway(gw, data)
            else:
                updated_active.append(gw)

        if changed:
            data["active"] = updated_active
            json_save(DB_FILE, data)

    async def _end_giveaway(self, gw: dict, data: dict) -> None:
        guild = self.bot.get_guild(gw["guild_id"])
        if not guild:
            data["history"].append(gw)
            return
        channel = guild.get_channel(gw["channel_id"])
        if not channel:
            data["history"].append(gw)
            return
        try:
            msg = await channel.fetch_message(gw["message_id"])
        except discord.NotFound:
            data["history"].append(gw)
            return
        except Exception:
            return

        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        no_entry_embed = discord.Embed(
            title="🎊 GIVEAWAY ENDED",
            description=f"Prize: **{gw['prize']}**\nWinner: *No entries received.*",
            color=discord.Color.red(),
        )

        if not reaction:
            await msg.edit(embed=no_entry_embed)
            await channel.send(f"❌ Giveaway for **{gw['prize']}** ended, but no participants entered!")
            data["history"].append(gw)
            return

        users = [u async for u in reaction.users() if not u.bot]
        if not users:
            await msg.edit(embed=no_entry_embed)
            await channel.send(f"❌ Giveaway for **{gw['prize']}** ended, but no participants entered!")
            data["history"].append(gw)
            return

        winners_count = gw.get("winners_count", 1)
        winners = random.sample(users, min(len(users), winners_count))
        mentions = ", ".join(w.mention for w in winners)

        embed_ended = discord.Embed(
            title="🎊 GIVEAWAY ENDED",
            description=f"Prize: **{gw['prize']}**\nWinner(s): {mentions}",
            color=discord.Color.red(),
        )
        await msg.edit(embed=embed_ended)
        await channel.send(
            f"🎉 Congratulations {mentions}! You won the giveaway for **{gw['prize']}**!"
        )
        gw["winners"] = [w.id for w in winners]
        data["history"].append(gw)

    # ── Commands ─────────────────────────────────────────────────────────

    @commands.group(name="giveaway", aliases=["gway"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def giveaway_group(self, ctx: commands.Context) -> None:
        """Setup and manage guild giveaways."""
        p = ctx.prefix
        await ctx.send(
            "🎊 **Server Giveaway Suite**\n"
            f"• `{p}giveaway start <dur> <prize>` — Start a giveaway (e.g. `{p}gway start 1h Nitro`)\n"
            f"• `{p}giveaway end <msg_id>` — End a giveaway early\n"
            f"• `{p}giveaway reroll <msg_id>` — Reroll winner\n"
            f"• `{p}giveaway list` — View active giveaways"
        )

    @giveaway_group.command(name="start")
    @commands.has_permissions(manage_guild=True)
    async def giveaway_start(
        self, ctx: commands.Context, duration: str = None, *, prize: str = None
    ) -> None:
        """
        Starts a server giveaway in the current channel.
        Usage: `f.giveaway start 10m Gift Card`
        """
        if not duration or not prize:
            return await ctx.send(
                f"Usage: `{ctx.prefix}giveaway start <duration> <prize>`"
            )

        secs = parse_duration(duration)
        if secs <= 0:
            return await ctx.send(
                "❌ Invalid duration! Use formats like `30s`, `15m`, `2h`, `1d`."
            )

        end_time = time.time() + secs
        end_time_dt = discord.utils.format_dt(
            discord.utils.utcfromtimestamp(end_time), style="R"
        )

        embed = discord.Embed(
            title="🎊 NEW GIVEAWAY!",
            description=(
                f"React with 🎉 to enter!\n\n"
                f"Prize: **{prize}**\n"
                f"Ends: {end_time_dt}\n"
                f"Hosted by: {ctx.author.mention}"
            ),
            color=discord.Color.green(),
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("🎉")

        data = _load()
        data["active"].append(
            {
                "guild_id": ctx.guild.id,
                "channel_id": ctx.channel.id,
                "message_id": msg.id,
                "end_time": end_time,
                "prize": prize,
                "winners_count": 1,
            }
        )
        json_save(DB_FILE, data)

        try:
            await ctx.message.delete()
        except Exception:
            pass

    @giveaway_group.command(name="end")
    @commands.has_permissions(manage_guild=True)
    async def giveaway_end(
        self, ctx: commands.Context, message_id: int = None
    ) -> None:
        """Ends an active giveaway early. Usage: `f.giveaway end <message_id>`"""
        if not message_id:
            return await ctx.send(f"Usage: `{ctx.prefix}giveaway end <message_id>`")

        data = _load()
        target = next(
            (gw for gw in data["active"] if gw["message_id"] == message_id), None
        )

        if not target:
            return await ctx.send("❌ No active giveaway found with that message ID.")

        target["end_time"] = time.time()
        await self._end_giveaway(target, data)
        data["active"].remove(target)
        json_save(DB_FILE, data)
        await ctx.send("✅ Giveaway ended early.")

    @giveaway_group.command(name="reroll")
    @commands.has_permissions(manage_guild=True)
    async def giveaway_reroll(
        self, ctx: commands.Context, message_id: int = None
    ) -> None:
        """Rerolls a new winner from an ended giveaway. Usage: `f.giveaway reroll <message_id>`"""
        if not message_id:
            return await ctx.send(f"Usage: `{ctx.prefix}giveaway reroll <message_id>`")

        data = _load()
        # Check still active
        if any(gw["message_id"] == message_id for gw in data["active"]):
            return await ctx.send(
                "❌ That giveaway is still active! Use `f.giveaway end` first."
            )

        target = next(
            (gw for gw in data["history"] if gw["message_id"] == message_id), None
        )
        if not target:
            return await ctx.send("❌ No giveaway record found with that message ID.")

        channel = ctx.guild.get_channel(target["channel_id"])
        if not channel:
            return await ctx.send("❌ Channel not found.")

        try:
            msg = await channel.fetch_message(target["message_id"])
        except Exception:
            return await ctx.send("❌ Original giveaway message not found.")

        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        if not reaction:
            return await ctx.send("❌ No reactions found on the giveaway message.")

        users = [u async for u in reaction.users() if not u.bot]
        if not users:
            return await ctx.send("❌ No eligible participants to reroll.")

        new_winner = random.choice(users)
        await channel.send(
            f"🎉 **REROLL!** The new winner for **{target['prize']}** is "
            f"{new_winner.mention}! Congratulations!"
        )

    @giveaway_group.command(name="list")
    async def giveaway_list(self, ctx: commands.Context) -> None:
        """Lists all active giveaways in the server."""
        data = _load()
        guild_active = [
            gw for gw in data["active"] if gw["guild_id"] == ctx.guild.id
        ]

        if not guild_active:
            return await ctx.send("❌ No active giveaways in this server.")

        embed = discord.Embed(
            title="🎊 Active Server Giveaways", color=discord.Color.green()
        )
        desc = ""
        for idx, gw in enumerate(guild_active, 1):
            chan = ctx.guild.get_channel(gw["channel_id"])
            chan_mention = chan.mention if chan else f"ID: {gw['channel_id']}"
            time_dt = discord.utils.format_dt(
                discord.utils.utcfromtimestamp(gw["end_time"]), style="R"
            )
            desc += (
                f"**#{idx}** Prize: **{gw['prize']}** in {chan_mention}\n"
                f"Ends: {time_dt}\n`Message ID: {gw['message_id']}`\n\n"
            )
        embed.description = desc
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Giveaways(bot))
