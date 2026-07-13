from __future__ import annotations
import logging
import os
import platform
import time

import discord
import psutil
import asyncio
import json
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
    category = "Eğlence ve Araçlar"
    category_emoji = "🛠️"
    """
    Utility commands for the bot.
    """

    def __init__(self, bot):
        self.category = "Eğlence ve Araçlar"
        self.bot = bot
        self.bot_start_time = time.time()

    @commands.command()
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def ping(self, ctx):
        """Check the bot's latency.

**Usage:** `{prefix}ping`"""
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
        """List the bot owners.

**Usage:** `{prefix}owners`"""
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
        """View a user's banner.\n\n**Usage:** `{prefix}banner`"""
        member = member or ctx.author
        user = await self.bot.fetch_user(member.id)
        banner = user.banner
        embed = discord.Embed(
            title=f"{member.display_name}'s Banner",
            color=discord.Color.blurple(),
        )
        if not banner:
            return await ctx.send("No banner found.")
        else:
            embed.set_image(url=_LUMINA_BANNER)
            embed.set_footer(text="No banner found. Using default banner.")
        await ctx.send(embed=embed)

    @commands.command(
        aliases=["pfp", "profile picture"],
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def avatar(self, ctx, member: discord.Member = None):
        """View a user's avatar.\n\n**Usage:** `{prefix}avatar`"""
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
    """Get information about the bot.\n\n**Usage:** `{prefix}about`"""

        uptime = round(time.time() - self.bot_start_time)

        mins, secs = divmod(uptime, 60)
        hours, mins = divmod(mins, 60)
        days, hours = divmod(hours, 24)
        uptime_str = f"`{days}d {hours}h {mins}m {secs}s`"
        
        pm2_stats_str = ""
        try:
            stats = {
                "Kumiho-Bot": {"cpu": 0.0, "ram": 0.0},
                "Kumiho-API": {"cpu": 0.0, "ram": 0.0},
                "Kumiho-Dashboard": {"cpu": 0.0, "ram": 0.0}
            }
            
            for p in psutil.process_iter(['cmdline']):
                try:
                    cmdline = p.info.get('cmdline')
                    if not cmdline:
                        continue
                    
                    cmd_str = ' '.join(cmdline).lower()
                    app_name = None
                    
                    if "main.py" in cmd_str and "python" in cmd_str:
                        app_name = "Kumiho-Bot"
                    elif "uvicorn" in cmd_str and "main:app" in cmd_str:
                        app_name = "Kumiho-API"
                    elif ("processcontainerfork" in cmd_str and "node" in cmd_str) or "vite" in cmd_str:
                        app_name = "Kumiho-Dashboard"
                    
                    if app_name:
                        # Fetch CPU percent (non-blocking if interval=None, but we need a quick measure so interval=0.1)
                        # To avoid blocking discord loop, we just use memory_percent or non-blocking cpu_percent
                        cpu = p.cpu_percent(interval=None) 
                        ram = p.memory_info().rss / (1024 * 1024)
                        stats[app_name]["cpu"] += cpu
                        stats[app_name]["ram"] += ram
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Need to call cpu_percent twice for accurate readings (first call is usually 0.0 without interval)
            await asyncio.sleep(0.5)
            
            for p in psutil.process_iter(['cmdline']):
                try:
                    cmdline = p.info.get('cmdline')
                    if not cmdline:
                        continue
                    
                    cmd_str = ' '.join(cmdline).lower()
                    app_name = None
                    
                    if "main.py" in cmd_str and "python" in cmd_str:
                        app_name = "Kumiho-Bot"
                    elif "uvicorn" in cmd_str and "main:app" in cmd_str:
                        app_name = "Kumiho-API"
                    elif ("processcontainerfork" in cmd_str and "node" in cmd_str) or "vite" in cmd_str:
                        app_name = "Kumiho-Dashboard"
                    
                    if app_name:
                        cpu = p.cpu_percent(interval=None) 
                        # Update the CPU value with the second reading
                        stats[app_name]["cpu"] = cpu
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            stats_lines = []
            for name, data in stats.items():
                stats_lines.append(f"• **{name}**: `{data['cpu']:.1f}%` CPU | `{data['ram']:.1f} MB` RAM")
            
            pm2_stats_str = "\n".join(stats_lines)
        except Exception as e:
            log.error(f"Failed to get psutil app stats: {e}")
            pass

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
        
        if pm2_stats_str:
            embed.add_field(name="Kumiho Apps Usage (PM2)", value=pm2_stats_str, inline=False)
        else:
            embed.add_field(name="Host CPU Usage", value=f"{psutil.cpu_percent()}%", inline=True)
            embed.add_field(name="Host RAM Usage", value=f"{psutil.virtual_memory().percent}%", inline=True)
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

    @commands.command(aliases=["ui", "whois"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def userinfo(self, ctx, member: discord.Member = None):
    """View detailed information about a user.\n\n**Usage:** `{prefix}userinfo`"""
        member = member or ctx.author

        profile = member.display_avatar.url
        name = member.name
        id = member.id

        statusEmojis = {
            "online": "🟢 Online",
            "idle": "🌙 Idle",
            "dnd": "🔴 Do Not Disturb",
            "offline": "⚪ Offline",
        }

        status = statusEmojis.get(str(member.status).lower(), "⚪ Offline")
        activity = member.activity.name if member.activity else "None"
        activity = f"{status} | {activity}"

        created = f"<t:{int(member.created_at.timestamp())}:F>\n(<t:{int(member.created_at.timestamp())}:R>)"
        joined = (
            f"<t:{int(member.joined_at.timestamp())}:F>\n(<t:{int(member.joined_at.timestamp())}:R>)"
            if member.joined_at
            else "N/A"
        )

        key_perms = []
        perms = {
            "administrator": "👑 Administrator",
            "manage_guild": "⚙️ Manage Server",
            "manage_roles": "🛡️ Manage Roles",
            "manage_channels": "📁 Manage Channels",
            "kick_members": "👢 Kick Members",
            "ban_members": "🔨 Ban Members",
        }
        for perm, label in perms.items():
            if getattr(member.guild_permissions, perm):
                key_perms.append(label)

        key_perms_text = ", ".join(key_perms) if key_perms else "Standard Member"

        roles = [role.mention for role in reversed(member.roles[1:])]
        rolesText = ", ".join(roles) if roles else "N/A"

        colour = member.color if member.color.value != 0 else discord.Color.blurple()

        embeded = discord.Embed(
            title=f"User Info | {member.display_name}",
            color=colour,
        )
        embeded.set_thumbnail(url=profile)

        embeded.add_field(name="Username", value=name, inline=True)
        embeded.add_field(name="ID", value=f"```{id}```", inline=True)
        embeded.add_field(
            name="Status | Activity",
            value=activity,
            inline=True,
        )

        embeded.add_field(name="📅 Account Created", value=created, inline=True)
        embeded.add_field(name="📥 Joined Server", value=joined, inline=True)

        embeded.add_field(
            name="🔑 Key Permissions", value=f"`{key_perms_text}`", inline=False
        )
        embeded.add_field(
            name=f"🎭 Roles ({len(roles)})", value=rolesText, inline=False
        )

        await ctx.send(embed=embeded)

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
