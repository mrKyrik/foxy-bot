"""
Commands/leveling.py
--------------------
Sunucu XP/seviye sistemi — tamamen SQLite destekli.

Veri katmanı:
  • levels tablosu → user_id, guild_id, xp, level, message_count
  • level_rewards tablosu → guild_id, level, role_id     (USER-DB.db)
  • level_ignores tablosu → guild_id, channel_id         (USER-DB.db)

Pillow yüklenmediyse rank komutu text embed döndürür.
"""

import io
import logging
import platform
import random
import time

import aiohttp
import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
    _PILLOW = True
except ImportError:
    _PILLOW = False


def _get_xp_needed(level: int) -> int:
    return 100 * (level ** 2) + 100


class Leveling(commands.Cog):
    """
    State-of-the-art server-scoped leveling cog with Pillow rank card rendering.
    All data is stored in SQLite via bot.db.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # In-memory cooldown: user_id_str -> last_xp_time
        self._xp_cd: dict[str, float] = {}

    async def cog_load(self):
        self.cleanup_xp_cd.start()

    async def cog_unload(self):
        self.cleanup_xp_cd.cancel()

    @tasks.loop(minutes=10)
    async def cleanup_xp_cd(self):
        now = time.time()
        for k in list(self._xp_cd.keys()):
            if now - self._xp_cd[k] > 60:
                del self._xp_cd[k]

    @property
    def db(self):
        return self.bot.db

    # ── DB Helpers ────────────────────────────────────────────────────────────

    async def _ensure_level_tables(self) -> None:
        """Create level_rewards and level_ignores tables if absent."""
        await self.db.user_db.executescript("""
        CREATE TABLE IF NOT EXISTS level_rewards (
            guild_id TEXT,
            level    INTEGER,
            role_id  TEXT,
            PRIMARY KEY (guild_id, level)
        );
        CREATE TABLE IF NOT EXISTS level_ignores (
            guild_id   TEXT,
            channel_id TEXT,
            PRIMARY KEY (guild_id, channel_id)
        );
        """)
        await self.db.user_db.commit()

    async def get_profile(self, guild_id: int, user_id: int) -> dict:
        await self.db.execute(
            "INSERT OR IGNORE INTO levels (user_id, guild_id) VALUES (?, ?)",
            str(user_id), str(guild_id),
        )
        row = await self.db.fetchone(
            "SELECT xp, level, message_count FROM levels WHERE user_id=? AND guild_id=?",
            str(user_id), str(guild_id),
        )
        return dict(row) if row else {"xp": 0, "level": 0, "message_count": 0}

    # ── XP Listener ───────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self._ensure_level_tables()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        # Channel ignore check
        ignored = await self.db.fetchone(
            "SELECT 1 FROM level_ignores WHERE guild_id=? AND channel_id=?",
            str(message.guild.id), str(message.channel.id),
        )
        if ignored:
            return

        # 60-second per-user cooldown (in-memory)
        u_key = f"{message.guild.id}:{message.author.id}"
        now = time.time()
        if now - self._xp_cd.get(u_key, 0.0) < 60:
            return
        self._xp_cd[u_key] = now

        profile = await self.get_profile(message.guild.id, message.author.id)
        xp_gain = random.randint(15, 25)
        new_xp = profile["xp"] + xp_gain
        level = profile["level"]
        msg_count = profile["message_count"] + 1
        needed = _get_xp_needed(level)

        if new_xp >= needed:
            # Level up
            new_level = level + 1
            new_xp = new_xp - needed
            await self.db.execute(
                """UPDATE levels SET xp=?, level=?, message_count=?
                   WHERE user_id=? AND guild_id=?""",
                new_xp, new_level, msg_count,
                str(message.author.id), str(message.guild.id),
            )
            try:
                embed = discord.Embed(
                    title="🎉 Level Up!",
                    description=f"Congratulations {message.author.mention}, you reached level **{new_level}**!",
                    color=discord.Color.green(),
                )
                await message.channel.send(embed=embed)
            except Exception:
                pass

            # Reward role
            reward = await self.db.fetchone(
                "SELECT role_id FROM level_rewards WHERE guild_id=? AND level=?",
                str(message.guild.id), new_level,
            )
            if reward:
                role = message.guild.get_role(int(reward["role_id"]))
                if role:
                    try:
                        await message.author.add_roles(role, reason="Level role reward")
                    except Exception:
                        pass
        else:
            await self.db.execute(
                """UPDATE levels SET xp=?, message_count=?
                   WHERE user_id=? AND guild_id=?""",
                new_xp, msg_count,
                str(message.author.id), str(message.guild.id),
            )

    # ── Rank Card ─────────────────────────────────────────────────────────────

    @commands.command(name="rank")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def rank(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """Displays your rank card. Usage: `f.rank [@user]`"""
        member = member or ctx.author
        if member.bot:
            return await ctx.send("❌ Bots do not earn XP!")

        profile = await self.get_profile(ctx.guild.id, member.id)
        xp, level = profile["xp"], profile["level"]
        needed = _get_xp_needed(level)

        # Rank position
        rows = await self.db.fetchall(
            "SELECT user_id, level, xp FROM levels WHERE guild_id=? ORDER BY level DESC, xp DESC",
            str(ctx.guild.id),
        )
        rank_pos = next(
            (idx for idx, r in enumerate(rows, 1) if r["user_id"] == str(member.id)),
            len(rows),
        )

        if not _PILLOW:
            embed = discord.Embed(
                title=f"🎖️ {member.display_name}'s Rank", color=discord.Color.blue()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Level", value=f"`{level}`", inline=True)
            embed.add_field(name="Rank", value=f"`#{rank_pos}`", inline=True)
            embed.add_field(name="XP Progress", value=f"`{xp} / {needed} XP`", inline=False)
            return await ctx.send(embed=embed)

        async with ctx.typing():
            # Fetch avatar bytes
            avatar_bytes = None
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(str(member.display_avatar.url)) as resp:
                        if resp.status == 200:
                            avatar_bytes = await resp.read()
            except Exception:
                pass

            width, height = 900, 250
            card = Image.new("RGBA", (width, height), (15, 23, 42, 255))
            draw = ImageDraw.Draw(card)

            # Avatar
            av_size = 180
            if avatar_bytes:
                av_img = Image.open(io.BytesIO(avatar_bytes)).resize(
                    (av_size, av_size), Image.Resampling.LANCZOS
                ).convert("RGBA")
            else:
                av_img = Image.new("RGBA", (av_size, av_size), (0, 200, 255, 255))

            mask = Image.new("L", (av_size, av_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, av_size, av_size), fill=255)
            ax, ay = 35, (height - av_size) // 2
            card.paste(av_img, (ax, ay), mask)
            draw.ellipse(
                (ax - 3, ay - 3, ax + av_size + 3, ay + av_size + 3),
                outline=(0, 200, 255, 255), width=6,
            )

            # Fonts
            try:
                if platform.system() == "Windows":
                    fn = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 38)
                    fs = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 26)
                    fl = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 34)
                else:
                    fn = ImageFont.truetype("arial.ttf", 38)
                    fs = fn; fl = fn
            except Exception:
                fn = fs = fl = ImageFont.load_default()

            draw.text((250, 50),  member.name,                       fill=(255, 255, 255, 255), font=fn)
            draw.text((250, 105), f"LEVEL {level}  |  RANK #{rank_pos}", fill=(0, 200, 255, 255), font=fl)
            draw.text((250, 155), f"{xp} / {needed} XP",              fill=(200, 200, 200, 255), font=fs)

            # Progress bar
            bx, by, bw, bh = 250, 195, 600, 24
            pct = min(1.0, xp / needed)
            draw.rectangle((bx, by, bx + bw, by + bh), fill=(50, 50, 50, 255))
            if pct > 0:
                draw.rectangle((bx, by, bx + int(bw * pct), by + bh), fill=(0, 200, 255, 255))

            buf = io.BytesIO()
            card.save(buf, format="PNG")
            buf.seek(0)

        await ctx.send(file=discord.File(buf, filename=f"rank-{member.id}.png"))

    # ── Level Settings ────────────────────────────────────────────────────────

    @commands.group(name="level", invoke_without_command=True)
    async def level_group(self, ctx: commands.Context) -> None:
        """Configure the leveling system."""
        await ctx.send(
            "⚙️ **Leveling Settings Suite**\n"
            f"• `{ctx.prefix}level reward_add <lvl> <@role>` — Add a reward role\n"
            f"• `{ctx.prefix}level reward_remove <lvl>` — Remove a reward role\n"
            f"• `{ctx.prefix}level reward_list` — List reward roles\n"
            f"• `{ctx.prefix}level ignore_add [#channel]` — Block XP in channel\n"
            f"• `{ctx.prefix}level ignore_remove [#channel]` — Unblock XP in channel"
        )

    @level_group.command(name="reward_add", aliases=["add_reward", "reward"])
    @commands.has_permissions(administrator=True)
    async def level_reward_add(
        self, ctx: commands.Context, level: int = None, role: discord.Role = None
    ) -> None:
        """Creates a level reward role. Usage: `f.level reward_add <level> <@role>`"""
        if level is None or not role:
            return await ctx.send(f"Usage: `{ctx.prefix}level reward_add <level> <@role>`")
        await self._ensure_level_tables()
        await self.db.execute(
            "INSERT OR REPLACE INTO level_rewards (guild_id, level, role_id) VALUES (?, ?, ?)",
            str(ctx.guild.id), level, str(role.id),
        )
        await ctx.send(f"✅ Level **{level}** reward set to {role.mention}.")

    @level_group.command(name="reward_remove", aliases=["remove_reward"])
    @commands.has_permissions(administrator=True)
    async def level_reward_remove(self, ctx: commands.Context, level: int = None) -> None:
        """Removes a level reward role. Usage: `f.level reward_remove <level>`"""
        if level is None:
            return await ctx.send(f"Usage: `{ctx.prefix}level reward_remove <level>`")
        await self._ensure_level_tables()
        await self.db.execute(
            "DELETE FROM level_rewards WHERE guild_id=? AND level=?",
            str(ctx.guild.id), level,
        )
        await ctx.send(f"✅ Cleared role reward for Level **{level}**.")

    @level_group.command(name="reward_list", aliases=["rewards"])
    async def level_reward_list(self, ctx: commands.Context) -> None:
        """Lists all level reward roles. Usage: `f.level reward_list`"""
        await self._ensure_level_tables()
        rows = await self.db.fetchall(
            "SELECT level, role_id FROM level_rewards WHERE guild_id=? ORDER BY level ASC",
            str(ctx.guild.id),
        )
        if not rows:
            return await ctx.send("❌ No level role rewards configured.")
        embed = discord.Embed(title="⚙️ Level Role Rewards", color=discord.Color.blue())
        desc = ""
        for row in rows:
            role = ctx.guild.get_role(int(row["role_id"]))
            role_text = role.mention if role else f"ID: {row['role_id']}"
            desc += f"• **Level {row['level']}** ➡️ {role_text}\n"
        embed.description = desc
        await ctx.send(embed=embed)

    @level_group.command(name="ignore_add", aliases=["ignore"])
    @commands.has_permissions(administrator=True)
    async def level_ignore_add(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ) -> None:
        """Blocks XP in a channel. Usage: `f.level ignore_add [#channel]`"""
        channel = channel or ctx.channel
        await self._ensure_level_tables()
        await self.db.execute(
            "INSERT OR IGNORE INTO level_ignores (guild_id, channel_id) VALUES (?, ?)",
            str(ctx.guild.id), str(channel.id),
        )
        await ctx.send(f"✅ XP gain blocked in {channel.mention}.")

    @level_group.command(name="ignore_remove", aliases=["unignore"])
    @commands.has_permissions(administrator=True)
    async def level_ignore_remove(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ) -> None:
        """Unblocks XP in a channel. Usage: `f.level ignore_remove [#channel]`"""
        channel = channel or ctx.channel
        await self._ensure_level_tables()
        await self.db.execute(
            "DELETE FROM level_ignores WHERE guild_id=? AND channel_id=?",
            str(ctx.guild.id), str(channel.id),
        )
        await ctx.send(f"✅ Restored XP gain in {channel.mention}.")

    # ── XP Leaderboard ────────────────────────────────────────────────────────

    @commands.command(name="leaderboard_xp", aliases=["lb_xp", "xplb"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def lb_xp(self, ctx: commands.Context) -> None:
        """Shows the XP leaderboard. Usage: `f.leaderboard_xp`"""
        rows = await self.db.fetchall(
            "SELECT user_id, level, xp FROM levels WHERE guild_id=? ORDER BY level DESC, xp DESC LIMIT 10",
            str(ctx.guild.id),
        )
        if not rows:
            return await ctx.send("❌ No XP profiles in this server yet.")

        embed = discord.Embed(title="🏆 Server XP Leaderboard", color=discord.Color.gold())
        desc = ""
        for idx, row in enumerate(rows, 1):
            m = ctx.guild.get_member(int(row["user_id"]))
            name = m.mention if m else f"ID: {row['user_id']}"
            # Approximate total XP earned
            total = row["xp"] + sum(_get_xp_needed(l) for l in range(row["level"]))
            desc += f"**#{idx}** {name} — Level `{row['level']}` (`{total:,} total XP`)\n"
        embed.description = desc
        embed.set_footer(text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leveling(bot))
