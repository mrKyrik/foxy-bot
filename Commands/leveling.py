"""
Commands/leveling.py
--------------------
Sunucu XP/seviye sistemi — tamamen SQLite destekli.

Veri katmanı:
  • levels tablosu → user_id, guild_id, xp, level, message_count
  • level_rewards tablosu → guild_id, level, role_id     (USER-DB.db)
  • level_ignores tablosu → guild_id, channel_id         (USER-DB.db)
  • level_settings tablosu → guild_id, level_channel_id, min_xp, max_xp

Pillow yüklenmediyse rank komutu text embed döndürür.
"""

from core.checks import kumiho_check, kumiho_app_check
import io
import logging
import platform
import random
import time

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
    category = "Gelişim ve Ekonomi"
    """
    State-of-the-art server-scoped leveling cog with Pillow rank card rendering.
    Optimized with RAM caching and O(log N) rank counting.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # In-memory cooldown: user_id_str -> last_xp_time
        self._xp_cd: dict[str, float] = {}
        
        # RAM Caches
        self.ignored_channels: set[str] = set() # "guild_id:channel_id"
        self.level_rewards: dict[str, dict[int, int]] = {} # guild_id -> {level: role_id}
        self.level_settings: dict[str, dict] = {} # guild_id -> {"channel_id": int, "min_xp": int, "max_xp": int}

    async def cog_load(self):
        self.cleanup_xp_cd.start()
        # Initial Cache Load
        await self._ensure_level_tables()
        await self._load_caches()

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

    # ── DB & Cache Helpers ────────────────────────────────────────────────────────────

    async def _ensure_level_tables(self) -> None:
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
        CREATE TABLE IF NOT EXISTS level_settings (
            guild_id TEXT PRIMARY KEY,
            level_channel_id TEXT,
            min_xp INTEGER DEFAULT 15,
            max_xp INTEGER DEFAULT 25
        );
        """)
        await self.db.user_db.commit()

    async def _load_caches(self):
        # Ignores
        ignores = await self.db.fetchall("SELECT guild_id, channel_id FROM level_ignores")
        self.ignored_channels = {f"{r['guild_id']}:{r['channel_id']}" for r in ignores}
        
        # Rewards
        rewards = await self.db.fetchall("SELECT guild_id, level, role_id FROM level_rewards")
        self.level_rewards.clear()
        for r in rewards:
            gid = r["guild_id"]
            if gid not in self.level_rewards:
                self.level_rewards[gid] = {}
            self.level_rewards[gid][r["level"]] = int(r["role_id"])
            
        # Settings
        settings = await self.db.fetchall("SELECT guild_id, level_channel_id, min_xp, max_xp FROM level_settings")
        self.level_settings.clear()
        for r in settings:
            self.level_settings[r["guild_id"]] = {
                "channel_id": int(r["level_channel_id"]) if r["level_channel_id"] else None,
                "min_xp": r["min_xp"],
                "max_xp": r["max_xp"]
            }

    def _get_setting(self, guild_id: str, key: str, default):
        if guild_id in self.level_settings and key in self.level_settings[guild_id]:
            val = self.level_settings[guild_id][key]
            if val is not None:
                return val
        return default

    # ── XP Listener ───────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        guild_id_str = str(message.guild.id)
        
        # O(1) Cache Ignore Check
        if f"{guild_id_str}:{message.channel.id}" in self.ignored_channels:
            return

        # 60-second cooldown
        u_key = f"{guild_id_str}:{message.author.id}"
        now = time.time()
        if now - self._xp_cd.get(u_key, 0.0) < 60:
            return
        self._xp_cd[u_key] = now

        # Custom XP Rate
        min_xp = self._get_setting(guild_id_str, "min_xp", 15)
        max_xp = self._get_setting(guild_id_str, "max_xp", 25)
        # Ensure max >= min
        if max_xp < min_xp: max_xp = min_xp
        xp_gain = random.randint(min_xp, max_xp)

        # UPSERT and return new state
        user_id_str = str(message.author.id)
        
        # To avoid extra queries, first insert if not exists
        await self.db.execute(
            "INSERT OR IGNORE INTO levels (user_id, guild_id, xp, level, message_count) VALUES (?, ?, 0, 0, 0)",
            user_id_str, guild_id_str
        )
        
        # Update and read in one go
        await self.db.execute(
            "UPDATE levels SET xp = xp + ?, message_count = message_count + 1 WHERE user_id = ? AND guild_id = ?",
            xp_gain, user_id_str, guild_id_str
        )
        
        profile = await self.db.fetchone(
            "SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?",
            user_id_str, guild_id_str
        )
        
        if not profile: return
        
        new_xp = profile["xp"]
        level = profile["level"]
        needed = _get_xp_needed(level)

        if new_xp >= needed:
            # Level up!
            new_level = level + 1
            leftover_xp = new_xp - needed
            
            await self.db.execute(
                "UPDATE levels SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?",
                leftover_xp, new_level, user_id_str, guild_id_str
            )
            
            # Message
            embed = discord.Embed(
                title="🎉 Level Up!",
                description=f"Tebrikler {message.author.mention}, **{new_level}** seviyesine ulaştın!",
                color=discord.Color.green(),
            )
            
            # Specific Channel Check
            channel_id = self._get_setting(guild_id_str, "channel_id", None)
            target_channel = message.channel
            if channel_id:
                ch = message.guild.get_channel(channel_id)
                if ch: target_channel = ch
                
            try:
                await target_channel.send(embed=embed)
            except Exception:
                pass

            # O(1) Cache Role Reward
            if guild_id_str in self.level_rewards and new_level in self.level_rewards[guild_id_str]:
                role_id = self.level_rewards[guild_id_str][new_level]
                role = message.guild.get_role(role_id)
                if role:
                    try:
                        await message.author.add_roles(role, reason="Level role reward")
                    except Exception:
                        pass

    # ── Rank Card ─────────────────────────────────────────────────────────────

    @commands.command(name="rank")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def rank(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """rank işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.rank [@user]`"""
        member = member or ctx.author
        if member.bot:
            return await ctx.send("❌ Bots do not earn XP!")

        # UPSERT
        await self.db.execute(
            "INSERT OR IGNORE INTO levels (user_id, guild_id, xp, level, message_count) VALUES (?, ?, 0, 0, 0)",
            str(member.id), str(ctx.guild.id)
        )
        profile = await self.db.fetchone(
            "SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?",
            str(member.id), str(ctx.guild.id)
        )
        xp, level = profile["xp"], profile["level"]
        needed = _get_xp_needed(level)

        # O(log N) Rank Query
        rank_row = await self.db.fetchone(
            "SELECT COUNT(*) as rank FROM levels WHERE guild_id = ? AND (level > ? OR (level = ? AND xp > ?))",
            str(ctx.guild.id), level, level, xp
        )
        rank_pos = rank_row["rank"] + 1

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
            avatar_bytes = None
            try:
                avatar_bytes = await member.display_avatar.replace(size=256, static_format="png").read()
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
            f"• `{ctx.prefix}level ignore_remove [#channel]` — Unblock XP in channel\n"
            f"• `{ctx.prefix}level channel set [#channel]` — Set a specific channel for level up messages\n"
            f"• `{ctx.prefix}level channel remove` — Send level up messages to current channel\n"
            f"• `{ctx.prefix}level xp_rate set <min> <max>` — Configure XP gained per message"
        )

    # REWARDS
    @level_group.command(name="reward_add", aliases=["add_reward", "reward"])
    @kumiho_check("owner")
    async def level_reward_add(
        self, ctx: commands.Context, level: int = None, role: discord.Role = None
    ) -> None:
        if level is None or not role:
            return await ctx.send(f"Usage: `{ctx.prefix}level reward_add <level> <@role>`")
        await self.db.execute(
            "INSERT OR REPLACE INTO level_rewards (guild_id, level, role_id) VALUES (?, ?, ?)",
            str(ctx.guild.id), level, str(role.id),
        )
        await self._load_caches()
        await ctx.send(f"✅ Level **{level}** reward set to {role.mention}.")

    @level_group.command(name="reward_remove", aliases=["remove_reward"])
    @kumiho_check("owner")
    async def level_reward_remove(self, ctx: commands.Context, level: int = None) -> None:
        if level is None:
            return await ctx.send(f"Usage: `{ctx.prefix}level reward_remove <level>`")
        await self.db.execute(
            "DELETE FROM level_rewards WHERE guild_id=? AND level=?",
            str(ctx.guild.id), level,
        )
        await self._load_caches()
        await ctx.send(f"✅ Cleared role reward for Level **{level}**.")

    @level_group.command(name="reward_list", aliases=["rewards"])
    @kumiho_check("owner")
    async def level_reward_list(self, ctx: commands.Context) -> None:
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

    # IGNORES
    @level_group.command(name="ignore_add", aliases=["ignore"])
    @kumiho_check("owner")
    async def level_ignore_add(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ) -> None:
        channel = channel or ctx.channel
        await self.db.execute(
            "INSERT OR IGNORE INTO level_ignores (guild_id, channel_id) VALUES (?, ?)",
            str(ctx.guild.id), str(channel.id),
        )
        await self._load_caches()
        await ctx.send(f"✅ XP gain blocked in {channel.mention}.")

    @level_group.command(name="ignore_remove", aliases=["unignore"])
    @kumiho_check("owner")
    async def level_ignore_remove(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ) -> None:
        channel = channel or ctx.channel
        await self.db.execute(
            "DELETE FROM level_ignores WHERE guild_id=? AND channel_id=?",
            str(ctx.guild.id), str(channel.id),
        )
        await self._load_caches()
        await ctx.send(f"✅ Restored XP gain in {channel.mention}.")

    # CHANNEL & XP RATE SETTINGS
    @level_group.group(name="channel", invoke_without_command=True)
    async def level_channel_group(self, ctx: commands.Context):
        await ctx.send(f"Usage: `{ctx.prefix}level channel set #kanal` veya `{ctx.prefix}level channel remove`")

    @level_channel_group.command(name="set")
    @kumiho_check("owner")
    async def level_channel_set(self, ctx: commands.Context, channel: discord.TextChannel):
        await self.db.execute(
            "INSERT INTO level_settings (guild_id, level_channel_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET level_channel_id=excluded.level_channel_id",
            str(ctx.guild.id), str(channel.id)
        )
        await self._load_caches()
        await ctx.send(f"✅ Seviye atlama mesajları artık {channel.mention} kanalına gönderilecek.")

    @level_channel_group.command(name="remove")
    @kumiho_check("owner")
    async def level_channel_remove(self, ctx: commands.Context):
        await self.db.execute(
            "UPDATE level_settings SET level_channel_id = NULL WHERE guild_id = ?",
            str(ctx.guild.id)
        )
        await self._load_caches()
        await ctx.send("✅ Özel seviye kanalı kaldırıldı. Mesajlar kazanıldığı kanala gönderilecek.")

    @level_group.group(name="xp_rate", invoke_without_command=True)
    async def level_xp_rate_group(self, ctx: commands.Context):
        await ctx.send(f"Usage: `{ctx.prefix}level xp_rate set <min> <max>`")

    @level_xp_rate_group.command(name="set")
    @kumiho_check("owner")
    async def level_xp_rate_set(self, ctx: commands.Context, min_xp: int, max_xp: int):
        if min_xp < 0 or max_xp < min_xp:
            return await ctx.send("❌ Geçersiz XP değerleri. (min >= 0, max >= min olmalı)")
            
        await self.db.execute(
            "INSERT INTO level_settings (guild_id, min_xp, max_xp) VALUES (?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET min_xp=excluded.min_xp, max_xp=excluded.max_xp",
            str(ctx.guild.id), min_xp, max_xp
        )
        await self._load_caches()
        await ctx.send(f"✅ Bu sunucu için mesaj başına kazanılacak XP limiti **{min_xp} - {max_xp}** olarak güncellendi.")

    # ── XP Leaderboard ────────────────────────────────────────────────────────

    @commands.command(name="leaderboard_xp", aliases=["lb_xp", "xplb"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def lb_xp(self, ctx: commands.Context) -> None:
        """leaderboard_xp işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.leaderboard_xp`"""
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
