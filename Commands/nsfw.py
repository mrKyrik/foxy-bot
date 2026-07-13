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
    category = "Eğlence ve Araçlar"
    category_emoji = "🛠️"
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
        """NSFW commands group.

**Usage:** `{prefix}nsfw`"""
        await ctx.send(random.choice(HORNY_DONKEY_QUOTES))

    @nsfw_group.command(name="bdsm")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def nsfw_bdsm(self, ctx: commands.Context) -> None:
        """Get an NSFW bdsm image.

**Usage:** `{prefix}nsfw bdsm`"""
        await ctx.send(random.choice(HORNY_DONKEY_QUOTES))

    @nsfw_group.command(name="hentai")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def nsfw_hentai(self, ctx: commands.Context) -> None:
        """Get a random hentai image.\n\n**Usage:** `{prefix}hentai`"""
        await ctx.send(random.choice(HORNY_DONKEY_QUOTES))

    @nsfw_group.command(name="feet")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def nsfw_feet(self, ctx: commands.Context) -> None:
        """Get a random feet image.\n\n**Usage:** `{prefix}feet`"""
        await ctx.send(random.choice(HORNY_DONKEY_QUOTES))

    @nsfw_group.command(name="rule34")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def nsfw_rule34(self, ctx: commands.Context) -> None:
        """Search for rule34 images.\n\n**Usage:** `{prefix}rule34`"""
        await ctx.send(random.choice(HORNY_DONKEY_QUOTES))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Nsfw(bot))
