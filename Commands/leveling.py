from __future__ import annotations
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
import os
import random
import time
import asyncio

import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    _PILLOW = True
except ImportError:
    _PILLOW = False


def _get_xp_needed(level: int) -> int:
    return 100 * (level ** 2) + 100

def _generate_levelup_card_sync(member_name: str, avatar_bytes: bytes, new_level: int, user_id: str) -> io.BytesIO:
    if not _PILLOW:
        return None
        
    width, height = 800, 250
    bg_path = f"Data/banners/{user_id}.png"
    if os.path.exists(bg_path):
        try:
            card = Image.open(bg_path).convert("RGBA")
            if card.size != (width, height):
                card = ImageOps.fit(card, (width, height), method=Image.Resampling.LANCZOS)
        except Exception:
            card = Image.new("RGBA", (width, height), (15, 23, 42, 255))
    else:
        card = Image.new("RGBA", (width, height), (15, 23, 42, 255))

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 150))
    card = Image.alpha_composite(card, overlay)
    draw = ImageDraw.Draw(card)

    av_size = 180
    if avatar_bytes:
        av_img = Image.open(io.BytesIO(avatar_bytes)).resize((av_size, av_size), Image.Resampling.LANCZOS).convert("RGBA")
    else:
        av_img = Image.new("RGBA", (av_size, av_size), (0, 200, 255, 255))

    mask = Image.new("L", (av_size, av_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, av_size, av_size), fill=255)
    ax, ay = 35, (height - av_size) // 2
    card.paste(av_img, (ax, ay), mask)
    draw.ellipse((ax - 3, ay - 3, ax + av_size + 3, ay + av_size + 3), outline=(16, 185, 129, 255), width=6)

    try:
        if platform.system() == "Windows":
            font_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 55)
            font_sub = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 35)
        else:
            font_title = ImageFont.truetype("arial.ttf", 55)
            font_sub = ImageFont.truetype("arial.ttf", 35)
    except Exception:
        font_title = font_sub = ImageFont.load_default()

    draw.text((250, 70), "LEVEL UP!", fill=(16, 185, 129), font=font_title)
    draw.text((250, 140), f"{member_name} \nSeviye {new_level} ulaştı!", fill=(255, 255, 255), font=font_sub)

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    buf.seek(0)
    return buf

def _generate_leaderboard_image_sync(lb_data: list, guild_name: str, lb_type: str) -> io.BytesIO:
    if not _PILLOW:
        return None
        
    width = 850
    row_height = 70
    padding = 20
    header_height = 80
    height = header_height + (len(lb_data) * row_height) + padding
    
    card = Image.new("RGBA", (width, height), (36, 39, 46, 255))
    draw = ImageDraw.Draw(card)

    try:
        if platform.system() == "Windows":
            font_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 40)
            font_rank = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 24)
            font_name = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 26)
            font_small = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 20)
        else:
            font_title = ImageFont.truetype("arial.ttf", 40)
            font_rank = ImageFont.truetype("arial.ttf", 24)
            font_name = ImageFont.truetype("arial.ttf", 26)
            font_small = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font_title = font_rank = font_name = font_small = ImageFont.load_default()

    title_text = f"{guild_name} - {'XP' if lb_type == 'xp' else 'Ses'} Sıralaması"
    draw.text((width//2, 40), title_text, fill=(255, 255, 255), font=font_title, anchor="mm")

    y_offset = header_height
    for idx, row in enumerate(lb_data):
        rank = row["rank"]
        
        # Color mapping for top 3
        if rank == 1: rank_color = (0, 255, 255)
        elif rank == 2: rank_color = (255, 215, 0)
        elif rank == 3: rank_color = (0, 255, 0)
        else: rank_color = (180, 180, 180)
        
        # Draw background alternating row
        if idx % 2 == 1:
            draw.rectangle([10, y_offset, width - 10, y_offset + row_height], fill=(47, 49, 54, 255))
            
        # Avatar
        av_size = 50
        ax, ay = 30, y_offset + (row_height - av_size) // 2
        
        if row.get("avatar_bytes"):
            try:
                av_img = Image.open(io.BytesIO(row["avatar_bytes"])).resize((av_size, av_size), Image.Resampling.LANCZOS).convert("RGBA")
            except Exception:
                av_img = Image.new("RGBA", (av_size, av_size), (0, 200, 255, 255))
        else:
            av_img = Image.new("RGBA", (av_size, av_size), (0, 200, 255, 255))
            
        mask = Image.new("L", (av_size, av_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, av_size, av_size), fill=255)
        card.paste(av_img, (ax, ay), mask)
        
        # Rank and Name
        draw.text((100, y_offset + 20), f"#{rank}", fill=rank_color, font=font_rank)
        draw.text((160, y_offset + 18), str(row["name"]), fill=(255, 255, 255), font=font_name)
        
        # Progress Bar
        bar_x, bar_y = 400, y_offset + 25
        bar_w, bar_h = 250, 20
        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=10, fill=(32, 34, 37, 255))
        
        if row.get("ratio", 0) > 0:
            fill_w = int(bar_w * min(row["ratio"], 1.0))
            if fill_w > 0:
                draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=10, fill=rank_color)
                
        # Progress text
        if "progress_text" in row:
            draw.text((bar_x + bar_w - 5, bar_y - 20), row["progress_text"], fill=rank_color, font=font_small, anchor="ra")
            
        # Level text
        if "level" in row:
            draw.text((700, y_offset + 20), f"Lvl {row['level']}", fill=(255, 255, 255), font=font_name)
        else:
            draw.text((700, y_offset + 20), f"{row.get('voice_hrs', '0')} Saat", fill=(255, 255, 255), font=font_name)
            
        y_offset += row_height

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    buf.seek(0)
    return buf

class Leveling(commands.Cog):
    category = "Gelişim ve Ekonomi"
    category_emoji = "🪙"
    """
    State-of-the-art server-scoped leveling cog with Pillow rank card rendering.
    Optimized with RAM caching and O(log N) rank counting.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # In-memory cooldown: user_id_str -> last_xp_time
        self._xp_cd: dict[str, float] = {}
        
        # Voice tracking: user_id -> (guild_id, join_time)
        self.voice_sessions: dict[int, tuple[int, float]] = {}
        
        # RAM Caches
        self.ignored_channels: set[str] = set() # "guild_id:channel_id"
        self.level_rewards: dict[str, dict[int, int]] = {} # guild_id -> {level: role_id}
        self.level_settings: dict[str, dict] = {} # guild_id -> {"channel_id": int, "min_xp": int, "max_xp": int}
        self.level_multipliers: dict[str, dict[int, float]] = {} # guild_id -> {role_id: multiplier}

    async def cog_load(self):
        self.cleanup_xp_cd.start()
        self.sync_voice_times.start()
        # Initial Cache Load
        await self._ensure_level_tables()
        await self._load_caches()

    async def cog_unload(self):
        self.cleanup_xp_cd.cancel()
        self.sync_voice_times.cancel()

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
        pass

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

        # Multipliers
        multipliers = await self.db.fetchall("SELECT guild_id, role_id, multiplier FROM level_multipliers")
        self.level_multipliers.clear()
        for r in multipliers:
            gid = r["guild_id"]
            if gid not in self.level_multipliers:
                self.level_multipliers[gid] = {}
            self.level_multipliers[gid][int(r["role_id"])] = float(r["multiplier"])

    def _get_setting(self, guild_id: str, key: str, default):
        if guild_id in self.level_settings and key in self.level_settings[guild_id]:
            val = self.level_settings[guild_id][key]
            if val is not None:
                return val
        return default

    async def add_xp(self, member: discord.Member, xp_gain: int, is_voice: bool = False, voice_minutes: int = 0, fallback_channel: discord.TextChannel = None) -> None:
        user_id_str = str(member.id)
        guild_id_str = str(member.guild.id)
        
        # Apply Role Multipliers (Stacking) if not applied before
        total_multiplier = 1.0
        if guild_id_str in self.level_multipliers and hasattr(member, "roles"):
            for role in member.roles:
                if role.id in self.level_multipliers[guild_id_str]:
                    total_multiplier *= self.level_multipliers[guild_id_str][role.id]
        
        xp_gain = int(xp_gain * total_multiplier)

        # To avoid extra queries, first insert if not exists
        await self.db.execute(
            "INSERT OR IGNORE INTO levels (user_id, guild_id, xp, level, message_count) VALUES (?, ?, 0, 0, 0)",
            user_id_str, guild_id_str
        )
        
        if is_voice:
            await self.db.execute(
                "UPDATE levels SET xp = xp + ?, voice_time = voice_time + ? WHERE user_id = ? AND guild_id = ?",
                xp_gain, voice_minutes, user_id_str, guild_id_str
            )
        else:
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
            
            channel_id = self._get_setting(guild_id_str, "channel_id", None)
            target_channel = None
            if channel_id:
                target_channel = member.guild.get_channel(channel_id)
            
            if not target_channel and not is_voice and fallback_channel:
                target_channel = fallback_channel
            
            if target_channel:
                try:
                    # Generate Image
                    avatar_bytes = None
                    try:
                        avatar_bytes = await member.display_avatar.replace(size=256, static_format="png").read()
                    except Exception:
                        pass
                    
                    buf = await asyncio.to_thread(
                        _generate_levelup_card_sync,
                        member.display_name,
                        avatar_bytes,
                        new_level,
                        str(member.id)
                    )
                    
                    if buf:
                        await target_channel.send(
                            content=f"🎉 Tebrikler {member.mention}, **{new_level}** seviyesine ulaştın!",
                            file=discord.File(buf, filename="levelup.png")
                        )
                    else:
                        # Fallback if Pillow is disabled
                        embed = discord.Embed(
                            title="🎉 Level Up!",
                            description=f"Tebrikler {member.mention}, **{new_level}** seviyesine ulaştın!",
                            color=discord.Color.green(),
                        )
                        await target_channel.send(content=member.mention, embed=embed)
                except Exception as e:
                    log.error(f"Level up message failed: {e}")

            if guild_id_str in self.level_rewards and new_level in self.level_rewards[guild_id_str]:
                role_id = self.level_rewards[guild_id_str][new_level]
                role = member.guild.get_role(role_id)
                if role:
                    try:
                        await member.add_roles(role, reason="Level role reward")
                    except Exception:
                        pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        guild_id_str = str(message.guild.id)
        
        if f"{guild_id_str}:{message.channel.id}" in self.ignored_channels:
            return

        u_key = f"{guild_id_str}:{message.author.id}"
        now = time.time()
        if now - self._xp_cd.get(u_key, 0.0) < 60:
            return
        self._xp_cd[u_key] = now

        min_xp = self._get_setting(guild_id_str, "min_xp", 15)
        max_xp = self._get_setting(guild_id_str, "max_xp", 25)
        if max_xp < min_xp: max_xp = min_xp
        base_xp = random.randint(min_xp, max_xp)

        # Use helper. Helper handles multiplier.
        await self.add_xp(message.author, base_xp, is_voice=False, fallback_channel=message.channel)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        if member.bot or not member.guild:
            return

        # Is user eligible for voice XP?
        # Must not be AFK channel. If deafened, must be streaming/video.
        def is_eligible(vs: discord.VoiceState) -> bool:
            if not vs.channel or vs.afk:
                return False
            if vs.self_deaf or vs.deaf:
                if not (vs.self_stream or vs.self_video):
                    return False
            return True

        before_elig = is_eligible(before)
        after_elig = is_eligible(after)

        if after_elig and not before_elig:
            # Started session
            self.voice_sessions[member.id] = (member.guild.id, time.time())
        elif before_elig and not after_elig:
            # Ended session
            session = self.voice_sessions.pop(member.id, None)
            if session:
                guild_id, start_time = session
                duration_mins = int((time.time() - start_time) / 60)
                if duration_mins > 0:
                    # 1 min = 1 XP
                    await self.add_xp(member, duration_mins, is_voice=True, voice_minutes=duration_mins)

    @tasks.loop(minutes=60)
    async def sync_voice_times(self) -> None:
        """Saves current voice sessions periodically without ending them."""
        now = time.time()
        for member_id, session in list(self.voice_sessions.items()):
            guild_id, start_time = session
            duration_mins = int((now - start_time) / 60)
            if duration_mins > 0:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    member = guild.get_member(member_id)
                    if member:
                        await self.add_xp(member, duration_mins, is_voice=True, voice_minutes=duration_mins)
                        # Reset start time
                        self.voice_sessions[member_id] = (guild_id, now)


    # ── Rank Card ─────────────────────────────────────────────────────────────

    @commands.command(name="rank")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    @kumiho_check("public")
    async def rank(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """Check your or someone else's rank.\n\n**Usage:** `{prefix}rank`"""
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
            # Check global profile
            global_prof = await self.db.fetchone(
                "SELECT color_hex FROM global_profiles WHERE user_id = ?",
                str(member.id)
            )
            color_hex = global_prof["color_hex"] if global_prof and global_prof["color_hex"] else "#10B981"
            
            # Convert hex to RGB tuple
            try:
                c = color_hex.lstrip("#")
                primary_color = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
            except Exception:
                primary_color = (16, 185, 129)

            avatar_bytes = None
            try:
                avatar_bytes = await member.display_avatar.replace(size=256, static_format="png").read()
            except Exception:
                pass

            width, height = 900, 250
            
            # Load Background
            bg_path = f"Data/banners/{member.id}.png"
            if os.path.exists(bg_path):
                try:
                    card = Image.open(bg_path).convert("RGBA")
                    # Ensure it is 900x250
                    if card.size != (width, height):
                        card = ImageOps.fit(card, (width, height), method=Image.Resampling.LANCZOS)
                except Exception as e:
                    log.error(f"Failed to load banner for {member.id}: {e}")
                    card = Image.new("RGBA", (width, height), (15, 23, 42, 255))
            else:
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
                    font_lg = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 38)
                    font_sm = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 26)
                else:
                    font_lg = ImageFont.truetype("arial.ttf", 40)
                    font_sm = font_lg
            except Exception:
                font_lg = font_sm = ImageFont.load_default()

            draw.text((250, 45), member.display_name, fill=(255, 255, 255), font=font_lg)
            draw.text((width - 60, 45), f"Lvl {level}  |  #{rank_pos}", fill=primary_color, font=font_lg, anchor="ra")

            bar_x, bar_y = 250, 150
            bar_w, bar_h = 600, 30
            draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=15, fill=(30, 41, 59, 200))

            ratio = xp / needed if needed > 0 else 0
            ratio = min(max(ratio, 0.0), 1.0)
            fill_w = int(bar_w * ratio)

            if fill_w > 0:
                draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=15, fill=primary_color)

            draw.text((bar_x + bar_w, bar_y - 25), f"{xp} / {needed} XP", fill=(200, 200, 200), font=font_sm, anchor="ra")

            buf = io.BytesIO()
            card.save(buf, format="PNG")
            buf.seek(0)

        await ctx.send(file=discord.File(buf, filename=f"rank-{member.id}.png"))

    # ── Level Settings ────────────────────────────────────────────────────────

    @commands.group(name="level", invoke_without_command=True)
    async def level_group(self, ctx: commands.Context) -> None:
        """level işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.level`"""
        from Commands.administration.setup import LevelSetupView
        embed = discord.Embed(
            title="⭐ Seviye Sistemi Kurulumu",
            description="**Seviye (XP) Sistemi Ayarları**\nLevel atlama kanalını ve sistem durumunu buradan tek tıkla yönetebilirsiniz.",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed, view=LevelSetupView(self.bot))

    # REWARDS
    @level_group.command(name="reward_add", aliases=["add_reward", "reward"])
    @kumiho_check("owner")
    async def level_reward_add(
        self, ctx: commands.Context, level: int = None, role: discord.Role = None
    ) -> None:
        """Add a role reward for a level.\n\n**Usage:** `{prefix}level_reward_add`"""
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
        """Remove a role reward for a level.\n\n**Usage:** `{prefix}level_reward_remove`"""
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
        """List all level role rewards.\n\n**Usage:** `{prefix}level_reward_list`"""
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

    # MULTIPLIERS
    @level_group.command(name="multiplier_add")
    @kumiho_check("owner")
    async def level_multiplier_add(self, ctx: commands.Context, role: discord.Role, multiplier: float):
        """Add an XP multiplier to a role.\n\n**Usage:** `{prefix}level_multiplier_add`"""
        if multiplier <= 0:
            return await ctx.send("❌ Çarpan 0'dan büyük olmalıdır.")
            
        await self.db.execute(
            "INSERT INTO level_multipliers (guild_id, role_id, multiplier) VALUES (?, ?, ?) ON CONFLICT(guild_id, role_id) DO UPDATE SET multiplier=excluded.multiplier",
            str(ctx.guild.id), str(role.id), float(multiplier)
        )
        await self._load_caches()
        await ctx.send(f"✅ {role.mention} rolü için XP çarpanı **{multiplier}x** olarak ayarlandı.")

    @level_group.command(name="multiplier_remove")
    @kumiho_check("owner")
    async def level_multiplier_remove(self, ctx: commands.Context, role: discord.Role):
        """Remove an XP multiplier from a role.\n\n**Usage:** `{prefix}level_multiplier_remove`"""
        await self.db.execute(
            "DELETE FROM level_multipliers WHERE guild_id=? AND role_id=?",
            str(ctx.guild.id), str(role.id)
        )
        await self._load_caches()
        await ctx.send(f"✅ {role.name} rolünün XP çarpanı kaldırıldı.")

    @level_group.command(name="multiplier_list")
    @kumiho_check("owner")
    async def level_multiplier_list(self, ctx: commands.Context):
        """List all XP multipliers.\n\n**Usage:** `{prefix}level_multiplier_list`"""
        rows = await self.db.fetchall(
            "SELECT role_id, multiplier FROM level_multipliers WHERE guild_id=? ORDER BY multiplier DESC",
            str(ctx.guild.id)
        )
        if not rows:
            return await ctx.send("❌ Herhangi bir rol çarpanı ayarlanmamış.")
            
        embed = discord.Embed(title="✨ Rol XP Çarpanları", color=discord.Color.purple())
        desc = ""
        for row in rows:
            role = ctx.guild.get_role(int(row["role_id"]))
            role_text = role.mention if role else f"ID: {row['role_id']}"
            desc += f"• {role_text} ➡️ **{row['multiplier']}x**\n"
        embed.description = desc
        await ctx.send(embed=embed)

    # IGNORES
    @level_group.command(name="ignore_add", aliases=["ignore"])
    @kumiho_check("owner")
    async def level_ignore_add(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ) -> None:
        """Add a channel to the XP ignore list.\n\n**Usage:** `{prefix}level_ignore_add`"""
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
        """Remove a channel from the XP ignore list.\n\n**Usage:** `{prefix}level_ignore_remove`"""
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
        """Manage level up announcement channels.\n\n**Usage:** `{prefix}level_channel_group`"""
        await ctx.send(f"Usage: `{ctx.prefix}level channel set #kanal` veya `{ctx.prefix}level channel remove`")

    @level_channel_group.command(name="set")
    @kumiho_check("owner")
    async def level_channel_set(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel for level up announcements.\n\n**Usage:** `{prefix}level_channel_set`"""
        await self.db.execute(
            "INSERT INTO level_settings (guild_id, level_channel_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET level_channel_id=excluded.level_channel_id",
            str(ctx.guild.id), str(channel.id)
        )
        await self._load_caches()
        await ctx.send(f"✅ Seviye atlama mesajları artık {channel.mention} kanalına gönderilecek.")

    @level_channel_group.command(name="remove")
    @kumiho_check("owner")
    async def level_channel_remove(self, ctx: commands.Context):
        """Disable level up announcements.\n\n**Usage:** `{prefix}level_channel_remove`"""
        await self.db.execute(
            "UPDATE level_settings SET level_channel_id = NULL WHERE guild_id = ?",
            str(ctx.guild.id)
        )
        await self._load_caches()
        await ctx.send("✅ Özel seviye kanalı kaldırıldı. Mesajlar kazanıldığı kanala gönderilecek.")

    @level_group.group(name="xp_rate", invoke_without_command=True)
    async def level_xp_rate_group(self, ctx: commands.Context):
        """Manage the server XP rate.\n\n**Usage:** `{prefix}level_xp_rate_group`"""
        await ctx.send(f"Usage: `{ctx.prefix}level xp_rate set <min> <max>`")

    @level_xp_rate_group.command(name="set")
    @kumiho_check("owner")
    async def level_xp_rate_set(self, ctx: commands.Context, min_xp: int, max_xp: int):
        """Set the server global XP multiplier.\n\n**Usage:** `{prefix}level_xp_rate_set`"""
        if min_xp < 0 or max_xp < min_xp:
            return await ctx.send("❌ Geçersiz XP değerleri. (min >= 0, max >= min olmalı)")
            
        await self.db.execute(
            "INSERT INTO level_settings (guild_id, min_xp, max_xp) VALUES (?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET min_xp=excluded.min_xp, max_xp=excluded.max_xp",
            str(ctx.guild.id), min_xp, max_xp
        )
        await self._load_caches()
        await ctx.send(f"✅ Bu sunucu için mesaj başına kazanılacak XP limiti **{min_xp} - {max_xp}** olarak güncellendi.")

    # GLOBAL PROFILES (BANNERS & COLORS)
    @level_group.command(name="rank_bg")
    @kumiho_check("public")
    async def level_rank_bg(self, ctx: commands.Context):
        """Kendi Rank arka planını değiştirir. Mesaja bir resim eklemelisin!"""
        if not ctx.message.attachments:
            return await ctx.send("❌ Arka plan ayarlamak için bu komutla birlikte bir resim yüklemelisin (attachment)!")
            
        attachment = ctx.message.attachments[0]
        if not attachment.content_type or not attachment.content_type.startswith("image/"):
            return await ctx.send("❌ Lütfen geçerli bir görsel dosyası yükle (PNG, JPG vb.).")
            
        # 5 MB Limit
        if attachment.size > 5 * 1024 * 1024:
            return await ctx.send("❌ Yüklediğin görsel çok büyük! Lütfen **5 MB**'dan daha küçük bir dosya yükle.")
            
        await ctx.send("⏳ Görsel işleniyor, lütfen bekle...", delete_after=5)
        
        try:
            image_bytes = await attachment.read()
            img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
            
            # Fit to 900x250
            img = ImageOps.fit(img, (900, 250), method=Image.Resampling.LANCZOS)
            
            # Save as PNG
            bg_path = f"Data/banners/{ctx.author.id}.png"
            img.save(bg_path, "PNG", optimize=True)
            
            # Insert into DB just to be safe (color_hex is preserved if exists)
            await self.db.execute(
                "INSERT INTO global_profiles (user_id) VALUES (?) ON CONFLICT(user_id) DO NOTHING",
                str(ctx.author.id)
            )
            
            await ctx.send(f"✅ Rank kartı arka planın başarıyla güncellendi! Görmek için `{ctx.prefix}rank` yazabilirsin.")
        except Exception as e:
            log.error(f"Failed to process banner for {ctx.author.id}: {e}")
            await ctx.send("❌ Görsel işlenirken bir hata oluştu.")

    @level_group.command(name="rank_color")
    @kumiho_check("public")
    async def level_rank_color(self, ctx: commands.Context, hex_code: str):
        """Kendi Rank tema rengini değiştirir. Örn: #FF0000"""
        if not hex_code.startswith("#") or len(hex_code) not in (4, 7):
            return await ctx.send("❌ Lütfen geçerli bir HEX kodu gir. Örn: `#FF5733`")
            
        await self.db.execute(
            "INSERT INTO global_profiles (user_id, color_hex) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET color_hex=excluded.color_hex",
            str(ctx.author.id), hex_code
        )
        await ctx.send(f"✅ Rank kartı temanın ana rengi **{hex_code}** olarak güncellendi! Görmek için `{ctx.prefix}rank` yazabilirsin.")


    # ── XP Leaderboard ────────────────────────────────────────────────────────

    @commands.command(name="leaderboard_xp", aliases=["lb_xp", "xplb", "ranktop", "toprank"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    @kumiho_check("public")
    async def lb_xp(self, ctx: commands.Context) -> None:
        """View the XP leaderboard.\n\n**Usage:** `{prefix}leaderboard_xp`"""
        rows = await self.db.fetchall(
            "SELECT user_id, level, xp FROM levels WHERE guild_id=? ORDER BY level DESC, xp DESC",
            str(ctx.guild.id),
        )
        if not rows:
            return await ctx.send("❌ No XP profiles in this server yet.")

        view = LeaderboardView(ctx, rows, lb_type="xp")
        await view.start()

    @commands.command(name="leaderboard_voice", aliases=["lb_vc", "lbvc", "sestop", "ses_top", "ses_rank"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    @kumiho_check("public")
    async def lb_vc(self, ctx: commands.Context) -> None:
        """View the voice XP leaderboard.\n\n**Usage:** `{prefix}leaderboard_voice`"""
        rows = await self.db.fetchall(
            "SELECT user_id, voice_time FROM levels WHERE guild_id=? AND voice_time > 0 ORDER BY voice_time DESC",
            str(ctx.guild.id),
        )
        if not rows:
            return await ctx.send("❌ Bu sunucuda henüz kaydedilmiş ses süresi yok.")

        view = LeaderboardView(ctx, rows, lb_type="voice")
        await view.start()

class LeaderboardView(discord.ui.View):
    def __init__(self, ctx: commands.Context, rows: list[dict], lb_type: str = "xp", per_page: int = 10):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.rows = rows
        self.lb_type = lb_type
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = max(1, (len(rows) - 1) // per_page + 1)
        self.message = None
        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = self.current_page == 0
        self.next_btn.disabled = self.current_page == self.total_pages - 1

    async def get_page_content(self):
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_rows = self.rows[start:end]
        
        lb_data = []
        for idx, row in enumerate(page_rows, start + 1):
            m = self.ctx.guild.get_member(int(row["user_id"]))
            name = m.display_name if m else f"Bilinmeyen (ID: {row['user_id']})"
            
            avatar_bytes = None
            if m:
                try:
                    avatar_bytes = await m.display_avatar.replace(size=64, static_format="png").read()
                except Exception:
                    pass
            
            data_dict = {
                "rank": idx,
                "name": name,
                "avatar_bytes": avatar_bytes
            }
            
            if self.lb_type == "voice":
                mins = row.get("voice_time", 0)
                h = mins // 60
                data_dict["voice_hrs"] = str(h)
                data_dict["ratio"] = min(mins / 600, 1.0) # Arbitrary max scale for voice progress
                data_dict["progress_text"] = f"{mins} Dakika"
            else:
                level = row.get("level", 0)
                xp = row.get("xp", 0)
                needed = _get_xp_needed(level)
                data_dict["level"] = level
                data_dict["ratio"] = xp / needed if needed > 0 else 0
                data_dict["progress_text"] = f"{xp} / {needed} XP"
                
            lb_data.append(data_dict)
            
        buf = await asyncio.to_thread(
            _generate_leaderboard_image_sync,
            lb_data,
            self.ctx.guild.name,
            self.lb_type
        )
        
        if buf:
            return discord.File(buf, filename="leaderboard.png")
        return None

    async def start(self):
        msg = await self.ctx.send("⏳ Tablo yükleniyor...", delete_after=10)
        file = await self.get_page_content()
        if file:
            self.message = await self.ctx.send(
                content=f"Sayfa {self.current_page + 1}/{self.total_pages}",
                file=file,
                view=self
            )
        else:
            await self.ctx.send("❌ Resim oluşturulamadı. Pillow kurulu mu?")

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.primary, custom_id="prev")
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Bu menüyü sen açmadın.", ephemeral=True)
        await interaction.response.defer()
        self.current_page -= 1
        self.update_buttons()
        file = await self.get_page_content()
        await interaction.edit_original_response(content=f"Sayfa {self.current_page + 1}/{self.total_pages}", attachments=[file], view=self)

    @discord.ui.button(emoji="🔍", label="Beni Bul", style=discord.ButtonStyle.secondary, custom_id="find_me")
    async def find_me_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Bu menüyü sen açmadın.", ephemeral=True)
        
        user_index = -1
        for idx, row in enumerate(self.rows):
            if int(row["user_id"]) == self.ctx.author.id:
                user_index = idx
                break
        
        if user_index == -1:
            return await interaction.response.send_message("❌ Henüz sıralamada değilsin.", ephemeral=True)
            
        await interaction.response.defer()
        self.current_page = user_index // self.per_page
        self.update_buttons()
        file = await self.get_page_content()
        await interaction.edit_original_response(content=f"Sayfa {self.current_page + 1}/{self.total_pages}", attachments=[file], view=self)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.primary, custom_id="next")
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Bu menüyü sen açmadın.", ephemeral=True)
        await interaction.response.defer()
        self.current_page += 1
        self.update_buttons()
        file = await self.get_page_content()
        await interaction.edit_original_response(content=f"Sayfa {self.current_page + 1}/{self.total_pages}", attachments=[file], view=self)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leveling(bot))
