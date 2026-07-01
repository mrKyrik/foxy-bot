"""
Commands/nsfw.py
----------------
Premium "yetişkin içerik" modülü — hepsi troll yanıtları verir.
"""

import random
import discord
from discord.ext import commands


HORNY_DONKEY_QUOTES = [
    "Go to horny jail immediately, you absolute donkey! 🐴",
    "What the hell are you looking for, you horny ass donkey? 🐴",
    "Seriously? Go touch some grass, you horny donkey! 🐴",
    "Get out of here before I kick your horny donkey ass! 🐴",
    "Stop looking for BDSM and get a job, you horny little donkey! 🐴",
    "My database is pure, unlike your horny donkey mind! 🐴",
    "No way, you horny donkey! I am not showing you that. 🐴",
    "Seek help, you absolute horny donkey! 🐴",
]


class Nsfw(commands.Cog):
    """
    Access premium uncensored 18+ adult content and mature feeds.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"❌ Cooldown active! Please wait **{error.retry_after:.1f}s**.")
        else:
            await ctx.send(f"An error occurred: {error}")

    @commands.group(name="nsfw", invoke_without_command=True)
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def nsfw_group(self, ctx: commands.Context) -> None:
        """
        Unlocks premium mature adult category feeds.
        Usage: `f.nsfw <subcommand>` (e.g. `f.nsfw bdsm`)
        """
        await ctx.send(random.choice(HORNY_DONKEY_QUOTES))

    @nsfw_group.command(name="bdsm")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def nsfw_bdsm(self, ctx: commands.Context) -> None:
        """
        Queries premium BDSM networks for uncensored media.
        Usage: `f.nsfw bdsm`
        """
        await ctx.send(random.choice(HORNY_DONKEY_QUOTES))

    @nsfw_group.command(name="hentai")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def nsfw_hentai(self, ctx: commands.Context) -> None:
        """
        Returns high-resolution uncensored Japanese hentai and anime art.
        Usage: `f.nsfw hentai`
        """
        await ctx.send(random.choice(HORNY_DONKEY_QUOTES))

    @nsfw_group.command(name="feet")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def nsfw_feet(self, ctx: commands.Context) -> None:
        """
        Displays ultra high-definition foot fetish gallery uploads.
        Usage: `f.nsfw feet`
        """
        await ctx.send(random.choice(HORNY_DONKEY_QUOTES))

    @nsfw_group.command(name="rule34")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def nsfw_rule34(self, ctx: commands.Context) -> None:
        """
        Connects directly to the rule34 API to fetch the latest artwork.
        Usage: `f.nsfw rule34`
        """
        await ctx.send(random.choice(HORNY_DONKEY_QUOTES))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Nsfw(bot))
