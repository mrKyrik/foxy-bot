import logging
import os
import platform
import time

import discord
import psutil
from discord.ext import commands

log = logging.getLogger(__name__)

_OWNER_IDS: list[str] = [
    o.strip() for o in (os.getenv("OWNER_ID") or "").split(",") if o.strip()
]
# Lumina Labs banner — static fallback
_LUMINA_BANNER = (
    "https://cdn.discordapp.com/banners/1505199750855659570/"
    "7b097c5d9cffbb17df26b5357adf92a1.png?size=512"
)


class Utils(commands.Cog):
    """
    Utility commands for the bot.
    """

    def __init__(self, bot):
        self.bot = bot
        self.bot_start_time = time.time()

    @commands.command()
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def ping(self, ctx):
        """
        Returns the bot's latency.
        Usage: `.ping`
        """
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: **{round(self.bot.latency * 1000)}ms**",
            color=discord.Color.from_rgb(0, 200, 255),
        )
        embed.set_image(url=_LUMINA_BANNER)
        await ctx.send(embed=embed)

    @commands.command(aliases=["owner"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def owners(self, ctx):
        """
        Returns the owners of the bot.
        Usage: `.[owners|owner]`
        """
        names = []
        for user_id in _OWNER_IDS:
            user = ctx.bot.get_user(int(user_id))
            names.append(user.display_name if user else f"Unknown User ({user_id})")
        if not names:
            return await ctx.send("No owners found.")
        await ctx.send(f"The owners of this bot are: {', '.join(names)}")

    @commands.command()
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def banner(self, ctx, member: discord.Member = None):
        """
        Returns the displayed banner of the mentioned/replyed person
        Usage: `.banner [member]`
        Arguments:
            member (discord.Member, optional): The member whose banner to retrieve. Defaults to the command author.
        """
        member = member or ctx.author
        user = await self.bot.fetch_user(member.id)
        banner = user.banner
        embed = discord.Embed(
            title=f"{member.display_name}'s Banner",
            color=discord.Color.blurple(),
        )
        if banner:
            embed.add_field(name="Link", value=f"[Display Banner]({banner.url})")
            embed.set_image(url=banner.url)
        else:
            embed.set_image(url=_LUMINA_BANNER)
            embed.set_footer(text="No banner found. Using default banner.")
        await ctx.send(embed=embed)

    @commands.command(
        aliases=["pfp", "profile picture"],
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def avatar(self, ctx, member: discord.Member = None):
        """
        Returns the displayed avatar of the mentioned/replyed person
        Usage: `.[avatar|pfp] [member]`
        Arguments:
            member (discord.Member, optional): The member whose avatar to retrieve. Defaults to the command author.
        """
        member = member or ctx.author

        dAvatar = member.display_avatar
        avatar = member.avatar

        embeded = discord.Embed(
            title=f"{member.display_name}'s Avatar",
            color=discord.Color.blurple(),
        )
        globalUrl = avatar.url if avatar else dAvatar.url

        embeded.add_field(
            name="Links",
            value=f"[Display Avatar]({dAvatar.url}) | [Global Avatar]({globalUrl})",
        )
        embeded.set_image(url=dAvatar.url)

        await ctx.send(embed=embeded)

    @commands.command(name="about", aliases=["botinfo", "stats"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def about(self, ctx):
        """
        Returns statistics and details about the bot.
        Usage: `.[about|botinfo|stats]`
        """

        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        uptime = round(time.time() - self.bot_start_time)

        mins, secs = divmod(uptime, 60)
        hours, mins = divmod(mins, 60)
        days, hours = divmod(hours, 24)
        uptime_str = f"`{days}d {hours}h {mins}m {secs}s`"

        embed = discord.Embed(
            title="🤖 **Bot Information & System Stats**",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(
            name="Library", value=f"discord.py `v{discord.__version__}`", inline=True
        )
        embed.add_field(
            name="Python Version", value=f"`v{platform.python_version()}`", inline=True
        )
        embed.add_field(name="OS Platform", value=f"`{platform.system()}`", inline=True)
        embed.add_field(name="CPU Usage", value=f"{cpu}%", inline=True)
        embed.add_field(name="RAM Usage", value=f"{ram}%", inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(
            name="Servers Count", value=f"`{len(self.bot.guilds)} guilds`", inline=True
        )
        embed.add_field(
            name="Total Users",
            value=f"`{sum(g.member_count for g in self.bot.guilds if g.member_count) if self.bot.guilds else 0} members`",
            inline=True,
        )
        embed.add_field(
            name="Ping / Latency",
            value=f"`{round(self.bot.latency * 1000)}ms`",
            inline=True,
        )
        await ctx.send(embed=embed)

    async def cog_command_error(self, ctx, error):

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.")
            return
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("I do not have permission to do that.")
            return
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"On cooldown. Please wait **{error.retry_after:.1f} seconds**."
            )
            return

        await ctx.send(f"An error occurred: {error}")


async def setup(bot):
    await bot.add_cog(Utils(bot))
