"""
Commands/fun.py
---------------
Eğlence komutları: tepki GIF'leri, oyunlar, istatistikler, anket vs.

Trivia ödülü ekonomi sistemine SQL üzerinden bağlanır.
"""

from core.checks import kumiho_check
import asyncio
import html
import logging
import os
import random
import time
from json import load
from pathlib import Path

import aiohttp
import discord
from discord.ext import commands

from core.utils import json_load, json_save

log = logging.getLogger(__name__)



ANSWERS_FILE = Path("Data/answers.json")
RAGE_FILE = Path("Data/ragepoints.json")


class Fun(commands.Cog):
    category = "Eğlence ve Araçlar"
    """
    Fun commands for the bot.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        try:
            with open(ANSWERS_FILE, "r", encoding="utf-8") as f:
                self.answers: list[str] = load(f)
        except FileNotFoundError:
            self.answers = ["Yes", "No", "Maybe", "Ask again later"]
            log.warning("answers.json not found, using default 8ball answers.")

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"❌ Cooldown active! Please wait **{error.retry_after:.1f}s**.")
        else:
            await ctx.send(f"An error occurred: {error}")

    # ──────────────────────────────────────────────────────────────────────
    # GIF Helper
    # ──────────────────────────────────────────────────────────────────────

    async def get_reaction_gif(self, action: str) -> str:
        """Fetches an anime SFW action GIF. Falls back to a static Giphy URL."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        }
        fallbacks = {
            "kiss":     "https://media.giphy.com/media/Fq1umVPXBYu0o/giphy.gif",
            "cuddle":   "https://media.giphy.com/media/lrr9MREL673Tq/giphy.gif",
            "bite":     "https://media.giphy.com/media/129a5KUtuxQH28/giphy.gif",
            "punch":    "https://media.giphy.com/media/11Heubawyp81hC/giphy.gif",
            "poke":     "https://media.giphy.com/media/yC7rxoBy2QZoc/giphy.gif",
            "lick":     "https://media.giphy.com/media/105t3CVCQkBJ1C/giphy.gif",
            "boop":     "https://media.giphy.com/media/10g47xRjTIGxQ4/giphy.gif",
            "tickle":   "https://media.giphy.com/media/U3BWiPeOAzfXi/giphy.gif",
            "wave":     "https://media.giphy.com/media/V8E0wV5D1fSSY/giphy.gif",
            "highfive": "https://media.giphy.com/media/1108D2tVa1dxUA/giphy.gif",
            "cry":      "https://media.giphy.com/media/8YutMatqkTfSE/giphy.gif",
            "laugh":    "https://media.giphy.com/media/132Z1K2h0G3yN2/giphy.gif",
            "blush":    "https://media.giphy.com/media/wW95fEq09hOI8/giphy.gif",
            "yeet":     "https://media.giphy.com/media/5PhDdJQd2yG1MvHzJ6/giphy.gif",
            "dance":    "https://media.giphy.com/media/143v0Z4767T15u/giphy.gif",
            "slap":     "https://media.giphy.com/media/Zau0yrl17uzdK/giphy.gif",
            "hug":      "https://media.giphy.com/media/du4D0b0HWgxG5lLLuk/giphy.gif",
            "pat":      "https://media.giphy.com/media/N0gIaUggWTCBW/giphy.gif",
        }

        if action in ("lick", "boop"):
            url = f"https://api.otakugifs.xyz/gif?reaction={action}"
        elif action == "hug":
            url = "https://nekos.best/api/v2/hug"
        else:
            url = f"https://nekos.best/api/v2/{action}"

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if action in ("lick", "boop"):
                            return data.get("url") or fallbacks.get(action, "")
                        results = data.get("results", [])
                        if results:
                            return results[0].get("url") or fallbacks.get(action, "")
        except Exception:
            pass
        return fallbacks.get(action, "https://media.giphy.com/media/V8E0wV5D1fSSY/giphy.gif")

    # ──────────────────────────────────────────────────────────────────────
    # Text Commands
    # ──────────────────────────────────────────────────────────────────────
    @commands.command(name="8ball")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def _8ball(self, ctx: commands.Context, *, question: str = None) -> None:
        """8ball işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.8ball [parametreler]`"""
        if question is None:
            return await ctx.send(f"Usage: `{ctx.prefix}8ball <question>`")
        answer = random.choice(self.answers)
        embed = discord.Embed(title="Magic 8-Ball 🎱", color=discord.Color.blurple())
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=answer, inline=False)
        embed.set_footer(text=f"Asked by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    @commands.command()

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def say(self, ctx: commands.Context, target: str = None, *, message: str = None) -> None:
        """say işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.say [parametreler]`"""
        if target is None:
            return await ctx.send(f"Usage: `{ctx.prefix}say <message>`")

        user = None
        try:
            user = await commands.MemberConverter().convert(ctx, target)
        except commands.MemberNotFound:
            pass

        is_owner = await ctx.bot.is_owner(ctx.author)
        if user is not None and is_owner:
            if message is None:
                return await ctx.send(f"Usage: `{ctx.prefix}say @user <message>`")
            avatar_bytes = await user.display_avatar.read()
            webhook = await ctx.channel.create_webhook(
                name=user.display_name, avatar=avatar_bytes, reason="say command"
            )
            await ctx.message.delete()
            try:
                await webhook.send(message)
            finally:
                await webhook.delete()
        else:
            full_msg = f"{target} {message or ''}".strip()
            await ctx.message.delete()
            await ctx.send(full_msg)
    @commands.command()

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def joke(self, ctx: commands.Context) -> None:
        """joke işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.joke [parametreler]`"""
        url = "https://v2.jokeapi.dev/joke/Any?safe-mode"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.json()
                if data.get("type") == "single":
                    await ctx.send(data["joke"])
                else:
                    await ctx.send(f"{data['setup']}\n\n*...{data['delivery']}*")
    @commands.command()

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def mock(self, ctx: commands.Context, *, message: str = None) -> None:
        """mock işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.mock [parametreler]`"""
        if message is None and not ctx.message.reference:
            return await ctx.send(f"Usage: `{ctx.prefix}mock <message>` or reply to mock")
        if ctx.message.reference:
            ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            message = ref.content
        mocked = "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(message))
        await ctx.reply(mocked, mention_author=False)
    @commands.command()

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def love(
        self,
        ctx: commands.Context,
        user: discord.Member = None,
        user2: discord.Member = None,
    ) -> None:
        """
        Measures the love between two users.
        Usage: `f.love <user> [user2]`
        """
        if user is None:
            return await ctx.send(f"Usage: `{ctx.prefix}love <user> [user2]`")
        if user2 is None:
            user2 = ctx.author

        lovers: dict[int, int | tuple] = {
            1323079941964959825: (797045576218837022, 1510308477472346262),
            764446193358077972: 832680878035304508,
            456823546228768769: 771826919334477866,
            1005651182301229196: 1326646655801622661,
        }

        is_lover_match = False
        if user.id != user2.id:
            for key, value in lovers.items():
                if isinstance(value, tuple):
                    if (
                        (user.id == key and user2.id in value)
                        or (user2.id == key and user.id in value)
                        or (user.id in value and user2.id in value)
                    ):
                        is_lover_match = True
                        break
                else:
                    if (user.id == key and user2.id == value) or (
                        user.id == value and user2.id == key
                    ):
                        is_lover_match = True
                        break

        if user.id == user2.id or is_lover_match:
            pct = 100
        else:
            pct = random.randint(0, 100)

        if pct >= 90:
            color, verdict = discord.Color.dark_red(), "What a perfect match!"
        elif pct >= 60:
            color, verdict = discord.Color.red(), "You two are totally in love!"
        elif pct >= 30:
            color, verdict = discord.Color.orange(), "There is a spark! Keep trying!"
        else:
            color, verdict = discord.Color.dark_gray(), "Yea... No"

        embed = discord.Embed(
            title="**Love Measure!**",
            description=f"How much does **{user.mention}** love **{user2.mention}**?",
            color=color,
        )
        embed.add_field(name="**Love Percentage**", value=f"**{pct}%** ❤️", inline=False)
        embed.add_field(name="**Verdict**", value=verdict, inline=False)
        await ctx.send(embed=embed)

        if user.id == user2.id:
            await ctx.send("-# You should love yourself no matter what! <:Enterprise_Heart:1510336292616016003>")
        elif pct == 100:
            await ctx.send("-# Maybe you two should marry~ <:Belfast_Smirk:1510332475220689067>")

    # ── Rage Points ────────────────────────────────────────────────────────

    @commands.group(name="rage", aliases=["ragebait", "rb"], invoke_without_command=True)
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def rage_group(
        self, ctx: commands.Context, member: discord.Member = None, *, amount: int = 5
    ) -> None:
        """
        Gives ragebait points to a user.
        Usage: `f.rage @user [amount]`
        """
        if member is None:
            return await ctx.send(f"Usage: `{ctx.prefix}rage @user [amount]`")

        g_id, u_id = str(ctx.guild.id), str(member.id)
        row = await self.bot.db.fetchone("SELECT points FROM ragepoints WHERE guild_id=? AND user_id=?", g_id, u_id)
        current = row["points"] if row else 0
        new_total = current + amount
        
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO ragepoints (guild_id, user_id, points) VALUES (?, ?, ?)",
            g_id, u_id, new_total
        )

        await ctx.send(
            f"Added **{amount}** rage points to {member.mention}! "
            f"Total: {new_total}"
        )

    @rage_group.command(name="list")
    async def rage_list(self, ctx: commands.Context) -> None:
        """list hakkında detaylı bilgi gösterir. Kullanım: `f.list`"""
        g_id = str(ctx.guild.id)
        rows = await self.bot.db.fetchall("SELECT user_id, points FROM ragepoints WHERE guild_id=? ORDER BY points DESC LIMIT 10", g_id)
        
        if not rows:
            return await ctx.send("No rage points in this server yet!")
            
        embed = discord.Embed(
            title=f"{ctx.guild.name} Ragebait Leaderboard", color=discord.Color.red()
        )
        desc = ""
        for idx, row in enumerate(rows, 1):
            uid = str(row["user_id"])
            pts = row["points"]
            m = ctx.guild.get_member(int(uid))
            name = m.mention if m else f"Unknown ({uid})"
            desc += f"**#{idx}** {name} — `{pts} pts`\n"
        embed.description = desc
        await ctx.send(embed=embed)

    @rage_group.command(name="remove")
    async def rage_remove(
        self, ctx: commands.Context, member: discord.Member = None, amount: int = None
    ) -> None:
        """Removes rage points from a user. Usage: `f.rage remove @user <amount>`"""
        if member is None or amount is None:
            return await ctx.send(f"Usage: `{ctx.prefix}rage remove @user <amount>`")
        g_id, u_id = str(ctx.guild.id), str(member.id)
        
        row = await self.bot.db.fetchone("SELECT points FROM ragepoints WHERE guild_id=? AND user_id=?", g_id, u_id)
        if not row:
            return await ctx.send(f"{member.mention} doesn't have any points.")
            
        current = row["points"]
        new_total = max(0, current - amount)
        
        await self.bot.db.execute(
            "UPDATE ragepoints SET points=? WHERE guild_id=? AND user_id=?",
            new_total, g_id, u_id
        )

        await ctx.send(
            f"Removed **{amount}** rage points from {member.mention}. "
            f"Total: {new_total}"
        )

    @rage_group.command(name="set")
    async def rage_set(
        self, ctx: commands.Context, member: discord.Member = None, amount: int = None
    ) -> None:
        """Sets a user's rage points. Usage: `f.rage set @user <amount>`"""
        if member is None or amount is None:
            return await ctx.send(f"Usage: `{ctx.prefix}rage set @user <amount>`")
        g_id, u_id = str(ctx.guild.id), str(member.id)
        
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO ragepoints (guild_id, user_id, points) VALUES (?, ?, ?)",
            g_id, u_id, amount
        )
        await ctx.send(f"Set {member.mention}'s rage points to **{amount}**.")

    # ── Fun Meters ─────────────────────────────────────────────────────────
    @commands.command(name="howgay")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def howgay(self, ctx: commands.Context, user: discord.Member = None) -> None:
        """howgay işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.howgay [user]`"""
        user = user or ctx.author
        pct = random.randint(0, 100)
        embed = discord.Embed(
            title="🌈 **Gay Rate!**",
            description=f"How gay is **{user.mention}**?",
            color=discord.Color.from_rgb(
                random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
            ),
        )
        verdict = (
            "Absolute queen!" if pct >= 90
            else "Pretty gay if you ask me!" if pct >= 60
            else "A little bit fruity" if pct >= 30
            else "Straight as a ruler... or are you?"
        )
        embed.add_field(name="**Gay Percentage**", value=f"**{pct}%**", inline=False)
        embed.add_field(name="**Verdict**", value=verdict, inline=False)
        embed.set_footer(text=f"Measured by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    @commands.command(name="howaustic", aliases=["howautistic"])

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def howaustic(self, ctx: commands.Context, user: discord.Member = None) -> None:
        """howaustic işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.howaustic [user]`"""
        user = user or ctx.author
        pct = random.randint(0, 100)
        embed = discord.Embed(
            title="🧩 **Autism Rate!**",
            description=f"How autistic is **{user.mention}**?",
            color=discord.Color.from_rgb(
                random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
            ),
        )
        verdict = (
            "Maximum autism reached!" if pct >= 90
            else "Very hyperfocused today!" if pct >= 60
            else "A touch of the acoustic" if pct >= 30
            else "Neurotypical... boring!"
        )
        embed.add_field(name="**Autism Percentage**", value=f"**{pct}%**", inline=False)
        embed.add_field(name="**Verdict**", value=verdict, inline=False)
        embed.set_footer(text=f"Measured by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    @commands.command(name="iq")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def iq(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """iq işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.iq [user]`"""
        member = member or ctx.author
        random.seed(member.id + int(time.time() // 86400))
        iq_val = random.randint(50, 150)
        random.seed()
        verdict = (
            "Single digit braincell activity detected." if iq_val < 80
            else "Slightly below average, but you try your best." if iq_val < 100
            else "Completely average human citizen." if iq_val < 120
            else "Very smart! A potential mastermind." if iq_val < 135
            else "Absolute genius! Successor to Einstein."
        )
        embed = discord.Embed(
            title="🧠 IQ Intelligence Test",
            description=(
                f"Measuring **{member.display_name}**'s intelligence...\n\n"
                f"Result: **{iq_val} IQ**\nVerdict: *{verdict}*"
            ),
            color=discord.Color.from_rgb(150, 0, 255),
        )
        await ctx.send(embed=embed)

    # ── Games ──────────────────────────────────────────────────────────────
    @commands.command(name="meme")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def meme(self, ctx: commands.Context) -> None:
        """meme işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.meme`"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://meme-api.com/gimme") as resp:
                    if resp.status != 200:
                        return await ctx.send("❌ Failed to fetch meme.")
                    data = await resp.json()
            embed = discord.Embed(
                title=data.get("title", "Reddit Meme"),
                url=data.get("postLink"),
                color=discord.Color.from_rgb(
                    random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
                ),
            )
            embed.set_image(url=data.get("url"))
            embed.set_footer(text=f"👍 {data.get('ups', 0)} | r/{data.get('subreddit')}")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Failed to fetch meme: {e}")
    @commands.command(name="cat", aliases=["meow"])

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def cat(self, ctx: commands.Context) -> None:
        """cat işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.cat`"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.thecatapi.com/v1/images/search") as resp:
                    if resp.status != 200:
                        return await ctx.send("❌ Failed to fetch cat image.")
                    data = await resp.json()
            embed = discord.Embed(
                title="🐱 Adorable Meow!",
                color=discord.Color.from_rgb(
                    random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
                ),
            )
            embed.set_image(url=data[0]["url"])
            embed.set_footer(text="Powered by thecatapi.com")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Failed to fetch cat: {e}")
    @commands.command(name="dog", aliases=["woof"])

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def dog(self, ctx: commands.Context) -> None:
        """dog işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.dog`"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://dog.ceo/api/breeds/image/random") as resp:
                    if resp.status != 200:
                        return await ctx.send("❌ Failed to fetch dog image.")
                    data = await resp.json()
            embed = discord.Embed(
                title="🐕 Cute Woof!",
                color=discord.Color.from_rgb(
                    random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
                ),
            )
            embed.set_image(url=data["message"])
            embed.set_footer(text="Powered by dog.ceo")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Failed to fetch dog: {e}")
    @commands.command(name="coinflip", aliases=["cf"])

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def coinflip(self, ctx: commands.Context) -> None:
        """coinflip işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.coinflip`"""
        result = random.choice(["Heads 🪙", "Tails 🪙"])
        embed = discord.Embed(
            title="Coin Flip",
            description=f"The coin landed on: **{result}**",
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"Flipped by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    @commands.command(name="roll", aliases=["dice"])

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def roll(self, ctx: commands.Context, sides: int = 6) -> None:
        """roll işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.roll [sides]`"""
        if sides < 2:
            return await ctx.send("❌ A dice must have at least 2 sides.")
        result = random.randint(1, sides)
        embed = discord.Embed(
            title="Dice Roll 🎲",
            description=f"You rolled a **{sides}**-sided dice and got: **{result}**",
            color=discord.Color.from_rgb(0, 200, 255),
        )
        embed.set_footer(text=f"Rolled by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    @commands.command(name="rps")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def rps(self, ctx: commands.Context, choice: str = None) -> None:
        """rps işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.rps <rock|paper|scissors>`"""
        if not choice:
            return await ctx.send(f"Usage: `{ctx.prefix}rps <rock|paper|scissors>`")
        options = ["rock", "paper", "scissors"]
        user_choice = choice.strip().lower()
        if user_choice not in options:
            return await ctx.send("❌ Choose: `rock`, `paper`, or `scissors`.")
        bot_choice = random.choice(options)
        emoji_map = {"rock": "Rock 🪨", "paper": "Paper 📄", "scissors": "Scissors ✂️"}
        if user_choice == bot_choice:
            result, color = "Tie! 🤝", discord.Color.orange()
        elif (user_choice == "rock" and bot_choice == "scissors") or \
             (user_choice == "paper" and bot_choice == "rock") or \
             (user_choice == "scissors" and bot_choice == "paper"):
            result, color = "You Win! 🎉", discord.Color.green()
        else:
            result, color = "I Win! 😈", discord.Color.red()
        embed = discord.Embed(
            title="Rock Paper Scissors",
            description=(
                f"**{result}**\n\n"
                f"**You chose:** {emoji_map[user_choice]}\n"
                f"**I chose:** {emoji_map[bot_choice]}"
            ),
            color=color,
        )
        embed.set_footer(text=f"Played with {ctx.author.display_name}")
        await ctx.send(embed=embed)
    @commands.command(name="choose", aliases=["choice"])

    @kumiho_check("public")
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def choose(self, ctx: commands.Context, *, choices: str = None) -> None:
        """choose işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.choose opt1, opt2, ...`"""
        if not choices:
            return await ctx.send(f"Usage: `{ctx.prefix}choose <opt1>, <opt2>, ...`")
        options = [c.strip() for c in choices.split(",") if c.strip()]
        if len(options) < 2:
            return await ctx.send("❌ Please provide at least 2 comma-separated options.")
        await ctx.send(f"🎯 I choose: **{random.choice(options)}**")
    @commands.command(name="fact")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def fact(self, ctx: commands.Context) -> None:
        """fact işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.fact`"""
        fallbacks = [
            "Banging your head against a wall for one hour burns 150 calories.",
            "In Switzerland it is illegal to own just one guinea pig.",
            "Pteronophobia is the fear of being tickled by feathers.",
            "Snakes can help predict earthquakes up to 75 miles away.",
            "Crow groups are called a murder.",
        ]
        fact_text = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://uselessfacts.jsph.pl/api/v2/facts/random?language=en"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        fact_text = data.get("text")
        except Exception:
            pass
        if not fact_text:
            fact_text = random.choice(fallbacks)
        embed = discord.Embed(
            title="💡 Random Fact", description=fact_text,
            color=discord.Color.from_rgb(0, 200, 255),
        )
        await ctx.send(embed=embed)
    @commands.command(name="trivia")

    @kumiho_check("public")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def trivia(self, ctx: commands.Context) -> None:
        """trivia işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.trivia [parametreler]`"""
        fallback_questions = [
            {"question": "What is the capital of France?", "correct_answer": "Paris",
             "incorrect_answers": ["London", "Berlin", "Rome"]},
            {"question": "Which planet is known as the Red Planet?", "correct_answer": "Mars",
             "incorrect_answers": ["Earth", "Jupiter", "Venus"]},
            {"question": "Who wrote Romeo and Juliet?", "correct_answer": "William Shakespeare",
             "incorrect_answers": ["Charles Dickens", "Leo Tolstoy", "Mark Twain"]},
        ]

        q_data = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://opentdb.com/api.php?amount=1&type=multiple"
                ) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        if res.get("response_code") == 0:
                            q_data = res["results"][0]
        except Exception:
            pass

        if not q_data:
            q_data = random.choice(fallback_questions)

        question = html.unescape(q_data["question"])
        correct = html.unescape(q_data["correct_answer"])
        incorrects = [html.unescape(a) for a in q_data["incorrect_answers"]]

        options = incorrects + [correct]
        random.shuffle(options)
        correct_letter = "ABCD"[options.index(correct)]
        letter_map = {i: c for i, c in enumerate("ABCD")}

        desc = f"**{question}**\n\n"
        for idx, opt in enumerate(options):
            desc += f"**{letter_map[idx]}** — {opt}\n"

        embed = discord.Embed(
            title="🧠 Trivia Question", description=desc, color=discord.Color.blue()
        )
        embed.set_footer(text="Type A, B, C or D within 15 seconds!")
        msg = await ctx.send(embed=embed)

        def check(m: discord.Message) -> bool:
            return (
                m.author.id == ctx.author.id
                and m.channel.id == ctx.channel.id
                and m.content.upper() in ("A", "B", "C", "D")
            )

        try:
            answer_msg = await self.bot.wait_for("message", check=check, timeout=15.0)
            user_ans = answer_msg.content.upper()

            if user_ans == correct_letter:
                # Award 100 coins via Economy cog (SQL path)
                eco_cog = self.bot.get_cog("Economy")
                if eco_cog:
                    try:
                        await eco_cog.add_wallet(ctx.guild.id, ctx.author.id, 100)
                    except Exception as exc:
                        log.warning("Trivia coin award failed: %s", exc)

                embed.color = discord.Color.green()
                embed.description = (
                    f"🎉 **CORRECT!**\n\nThe answer was **{correct_letter}) {correct}**.\n"
                    "You won **100 coins**!"
                )
            else:
                embed.color = discord.Color.red()
                embed.description = (
                    f"😡 **INCORRECT!**\n\nThe answer was **{correct_letter}) {correct}**.\n"
                    "Better luck next time!"
                )

        except asyncio.TimeoutError:
            embed.color = discord.Color.red()
            embed.description = (
                f"⏱️ **TIMED OUT!**\n\nThe answer was **{correct_letter}) {correct}**."
            )

        await msg.edit(embed=embed)

    # ── Reaction GIF Commands ─────────────────────────────────────────────

    def _reaction_embed(self, desc: str, color: tuple) -> discord.Embed:
        return discord.Embed(
            description=desc, color=discord.Color.from_rgb(*color)
        )
    @commands.command(name="slap")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def slap(self, ctx: commands.Context, member: discord.Member = None, *, reason: str = None) -> None:
        """slap işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.slap @user [reason]`"""
        if not member:
            return await ctx.send(f"Usage: `{ctx.prefix}slap @user [reason]`")
        msgs = [
            f"slapped {member.mention} with a giant smelly wet trout! 🐟",
            f"slapped {member.mention} with a squeaky rubber chicken! 🐔",
            f"slapped {member.mention} so hard they flew to Madagascar! 🌍",
            f"gave {member.mention} a legendary backhand of justice! 🫲",
            f"threw a cream pie in {member.mention}'s face! 🎂",
        ]
        reason_text = f"\nReason: *{reason}*" if reason else ""
        gif = await self.get_reaction_gif("slap")
        embed = self._reaction_embed(
            f"**{ctx.author.display_name}** {random.choice(msgs)}{reason_text}", (255, 100, 0)
        )
        embed.set_image(url=gif)
        await ctx.send(embed=embed)

    async def _send_reaction(self, ctx, action, member, self_msg, other_msg, color):
        if not member:
            return await ctx.send(f"Usage: `{ctx.prefix}{action} @user`")
        gif = await self.get_reaction_gif(action)
        msg = self_msg if member.id == ctx.author.id else other_msg
        embed = self._reaction_embed(msg, color)
        embed.set_image(url=gif)
        await ctx.send(embed=embed)
    @commands.command(name="hug")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def hug(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """hug işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.hug @user`"""
        await self._send_reaction(ctx, "hug", member,
            f"**{ctx.author.display_name}** hugged themselves... 🤗",
            f"**{ctx.author.display_name}** gave **{member.mention if member else ''}** a super warm hug! ❤️",
            (255, 100, 203))
    @commands.command(name="pat")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def pat(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """pat işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.pat @user`"""
        await self._send_reaction(ctx, "pat", member,
            f"**{ctx.author.display_name}** patted their own head. 🥺",
            f"**{ctx.author.display_name}** gently patted **{member.mention if member else ''}**! ✨",
            (255, 203, 100))
    @commands.command(name="kiss")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def kiss(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """kiss işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.kiss @user`"""
        await self._send_reaction(ctx, "kiss", member,
            f"**{ctx.author.display_name}** kissed the mirror... how lonely. 💙",
            f"**{ctx.author.display_name}** kissed **{member.mention if member else ''}** lovingly! 💙",
            (255, 100, 203))
    @commands.command(name="cuddle")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def cuddle(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """cuddle işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.cuddle @user`"""
        await self._send_reaction(ctx, "cuddle", member,
            f"**{ctx.author.display_name}** cuddles a soft teddy bear. 🧸",
            f"**{ctx.author.display_name}** cuddles **{member.mention if member else ''}** tightly! 🧸",
            (255, 150, 150))
    @commands.command(name="bite")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def bite(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """bite işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.bite @user`"""
        await self._send_reaction(ctx, "bite", member,
            f"**{ctx.author.display_name}** bit their own tongue! 😬",
            f"**{ctx.author.display_name}** bit **{member.mention if member else ''}**! Ouch! 😬",
            (200, 50, 50))
    @commands.command(name="punch")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def punch(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """punch işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.punch @user`"""
        await self._send_reaction(ctx, "punch", member,
            f"**{ctx.author.display_name}** punched the air with excitement! 👊",
            f"**{ctx.author.display_name}** punched **{member.mention if member else ''}**! 👊",
            (180, 50, 50))
    @commands.command(name="poke")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def poke(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """poke işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.poke @user`"""
        await self._send_reaction(ctx, "poke", member,
            f"**{ctx.author.display_name}** poked their own cheek. 👈",
            f"**{ctx.author.display_name}** poked **{member.mention if member else ''}**! Pay attention! 👈",
            (150, 200, 255))
    @commands.command(name="lick")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def lick(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """lick işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.lick @user`"""
        await self._send_reaction(ctx, "lick", member,
            f"**{ctx.author.display_name}** licks a strawberry ice cream. 🍓",
            f"**{ctx.author.display_name}** licked **{member.mention if member else ''}**! 😛",
            (255, 100, 150))
    @commands.command(name="boop")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def boop(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """boop işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.boop @user`"""
        await self._send_reaction(ctx, "boop", member,
            f"**{ctx.author.display_name}** booped their own nose. 👃",
            f"**{ctx.author.display_name}** booped **{member.mention if member else ''}**'s nose! Boop! 👃",
            (255, 180, 180))
    @commands.command(name="tickle")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def tickle(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """tickle işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.tickle @user`"""
        await self._send_reaction(ctx, "tickle", member,
            f"**{ctx.author.display_name}** tried to tickle themselves... nope. 😅",
            f"**{ctx.author.display_name}** tickled **{member.mention if member else ''}**! 😂",
            (255, 220, 100))
    @commands.command(name="wave")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def wave(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """wave işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.wave @user`"""
        await self._send_reaction(ctx, "wave", member,
            f"**{ctx.author.display_name}** waved to the crowd! 👋",
            f"**{ctx.author.display_name}** waved at **{member.mention if member else ''}**! 👋",
            (100, 255, 150))
    @commands.command(name="highfive")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def highfive(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """highfive işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.highfive @user`"""
        await self._send_reaction(ctx, "highfive", member,
            f"**{ctx.author.display_name}** high-fived the wall! 🖐️",
            f"**{ctx.author.display_name}** high-fived **{member.mention if member else ''}**! 🖐️",
            (255, 200, 100))
    @commands.command(name="cry")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def cry(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """cry işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.cry [@user]`"""
        gif = await self.get_reaction_gif("cry")
        if not member or member.id == ctx.author.id:
            desc = f"**{ctx.author.display_name}** is crying in the corner... 😭"
        else:
            desc = f"**{ctx.author.display_name}** is crying because of **{member.mention}**! 😭"
        embed = self._reaction_embed(desc, (100, 180, 255))
        embed.set_image(url=gif)
        await ctx.send(embed=embed)
    @commands.command(name="laugh")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def laugh(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """laugh işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.laugh [@user]`"""
        gif = await self.get_reaction_gif("laugh")
        if not member or member.id == ctx.author.id:
            desc = f"**{ctx.author.display_name}** burst into laughter! 😂"
        else:
            desc = f"**{ctx.author.display_name}** is laughing at **{member.mention}**! 😂"
        embed = self._reaction_embed(desc, (255, 230, 100))
        embed.set_image(url=gif)
        await ctx.send(embed=embed)
    @commands.command(name="blush")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def blush(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """blush işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.blush [@user]`"""
        gif = await self.get_reaction_gif("blush")
        if not member or member.id == ctx.author.id:
            desc = f"**{ctx.author.display_name}** blushed warmly! 😳"
        else:
            desc = f"**{ctx.author.display_name}** blushed because of **{member.mention}**! 😳"
        embed = self._reaction_embed(desc, (255, 100, 150))
        embed.set_image(url=gif)
        await ctx.send(embed=embed)
    @commands.command(name="yeet")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def yeet(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """yeet işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.yeet @user`"""
        if not member:
            return await ctx.send(f"Usage: `{ctx.prefix}yeet @user`")
        gif = await self.get_reaction_gif("yeet")
        if member.id == ctx.author.id:
            desc = f"**{ctx.author.display_name}** yeeted their homework! 🌍"
        else:
            desc = f"**{ctx.author.display_name}** yeeted **{member.mention}** into orbit! 🌍"
        embed = self._reaction_embed(desc, (255, 80, 80))
        embed.set_image(url=gif)
        await ctx.send(embed=embed)
    @commands.command(name="dance")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def dance(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """dance işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.dance [@user]`"""
        gif = await self.get_reaction_gif("dance")
        if not member or member.id == ctx.author.id:
            desc = f"**{ctx.author.display_name}** is dancing solo and loving it! 🎶"
        else:
            desc = f"**{ctx.author.display_name}** is dancing with **{member.mention}**! 🎶"
        embed = self._reaction_embed(desc, (200, 100, 255))
        embed.set_image(url=gif)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Fun(bot))
