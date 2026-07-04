"""
Commands/economy.py
-------------------
Kapsamlı Discord Economy sistemi — tamamen SQLite destekli.

Veri katmanı:
  • economy       tablosu → cüzdan, banka, cooldown'lar, padlock
  • inventory     tablosu → envanter kalemleri
  • economy_extras tablosu → evlilik, çiftçilik, özel başlık, master_crown timer

Hiçbir JSON dosyası kullanılmaz; tüm erişim bot.db üzerinden yapılır.
"""

from core.checks import kumiho_check
import asyncio
import logging
import random
import time

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# ── Ürün Listeleri ─────────────────────────────────────────────────────────────

SHOP_ITEMS: dict[str, dict] = {
    "fishing_rod":   {"name": "Fishing Rod 🎣",        "price": 500,    "desc": "Allows fishing via `f.fish`"},
    "hunting_rifle": {"name": "Hunting Rifle 🎯",       "price": 1000,   "desc": "Allows hunting via `f.hunt`"},
    "pickaxe":       {"name": "Steel Pickaxe ⛏️",      "price": 2000,   "desc": "Mine valuable ores via `f.mine`"},
    "lucky_gem":     {"name": "Lucky Gem 💎",           "price": 2500,   "desc": "Boosts work & gamble payouts by +25%"},
    "padlock":       {"name": "Shield Padlock 🔒",      "price": 1500,   "desc": "Blocks the next rob attempt on your wallet"},
    "bank_card":     {"name": "Gold Bank Card 💳",      "price": 3000,   "desc": "Boosts work payouts by +15%"},
    "clover":        {"name": "Four-Leaf Clover 🍀",    "price": 800,    "desc": "Boosts slots winnings by +10%"},
    "scratch_card":  {"name": "Scratch Card 🎟️",       "price": 200,    "desc": "Scratch for a chance to win up to 5,000 coins"},
    "wheat_seeds":   {"name": "Wheat Seeds 🌾",         "price": 50,     "desc": "Plant in your farm via `f.farm plant`"},
    "carrot_seeds":  {"name": "Carrot Seeds 🥕",        "price": 100,    "desc": "Plant in your farm via `f.farm plant`"},
    "melon_seeds":   {"name": "Melon Seeds 🍈",         "price": 200,    "desc": "Plant in your farm via `f.farm plant`"},
    "ring":          {"name": "Engagement Ring 💍",     "price": 50000,  "desc": "Propose marriage via `f.marry @user`"},
    "chat_color":    {"name": "Custom Color Perk 🎨",   "price": 50000,  "desc": "Recolor your top role via `f.perk color <hex>`"},
    "custom_title":  {"name": "Custom Title Perk 🏷️",  "price": 100000, "desc": "Custom balance title via `f.perk title <text>`"},
    "master_crown":  {"name": "Master's Crown 👑",      "price": 250000, "desc": "Bot praises you after 3+ hours of silence"},
}

NON_STACKABLE = {
    "fishing_rod", "hunting_rifle", "pickaxe", "lucky_gem",
    "chat_color", "custom_title", "master_crown", "bank_card",
}

SELLABLE_ITEMS: dict[str, dict] = {
    "fishing_rod":   {"name": "Fishing Rod 🎣",        "value": 250},
    "hunting_rifle": {"name": "Hunting Rifle 🎯",       "value": 500},
    "pickaxe":       {"name": "Steel Pickaxe ⛏️",      "value": 1000},
    "lucky_gem":     {"name": "Lucky Gem 💎",           "value": 1250},
    "padlock":       {"name": "Shield Padlock 🔒",      "value": 750},
    "bank_card":     {"name": "Gold Bank Card 💳",      "value": 1500},
    "clover":        {"name": "Four-Leaf Clover 🍀",    "value": 400},
    "scratch_card":  {"name": "Scratch Card 🎟️",       "value": 100},
    "wheat_seeds":   {"name": "Wheat Seeds 🌾",         "value": 25},
    "carrot_seeds":  {"name": "Carrot Seeds 🥕",        "value": 50},
    "melon_seeds":   {"name": "Melon Seeds 🍈",         "value": 100},
    "ring":          {"name": "Engagement Ring 💍",     "value": 25000},
    "chat_color":    {"name": "Custom Color Perk 🎨",   "value": 25000},
    "custom_title":  {"name": "Custom Title Perk 🏷️",  "value": 50000},
    "master_crown":  {"name": "Master's Crown 👑",      "value": 125000},
    "common_fish":   {"name": "Common Fish 🐟",         "value": 50},
    "salmon":        {"name": "Salmon 🐠",              "value": 120},
    "golden_bass":   {"name": "Golden Bass 🐡",         "value": 450},
    "junk_boot":     {"name": "Junk Boot 👢",           "value": 10},
    "rabbit":        {"name": "Rabbit 🐇",              "value": 70},
    "deer":          {"name": "Deer 🦌",                "value": 180},
    "wild_boar":     {"name": "Wild Boar 🐗",           "value": 450},
    "golden_dragon": {"name": "Golden Dragon 🐉",       "value": 1500},
    "coal":          {"name": "Coal Ore 🪨",            "value": 40},
    "iron":          {"name": "Iron Ore 🪙",            "value": 90},
    "gold":          {"name": "Gold Ore 🪙",            "value": 200},
    "diamond":       {"name": "Diamond Gems 💎",        "value": 500},
    "emerald":       {"name": "Emerald Gems 💚",        "value": 1000},
    "wheat":         {"name": "Grown Wheat 🌾",         "value": 150},
    "carrot":        {"name": "Sweet Carrot 🥕",        "value": 300},
    "melon":         {"name": "Juicy Melon 🍈",         "value": 600},
}

CROP_GROW_TIMES = {"wheat": 300, "carrot": 600, "melon": 1200}


# ─────────────────────────────────────────────────────────────────────────────

def _fmt_cd(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m or h:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


class Economy(commands.Cog):
    category = "Gelişim ve Ekonomi"
    """
    Comprehensive persistent Discord Economy Game with premium perks.
    All data is stored in SQLite via bot.db.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._locks: dict[int, asyncio.Lock] = {}

    def _get_lock(self, user_id: int) -> asyncio.Lock:
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        lock = self._get_lock(ctx.author.id)
        await lock.acquire()

    async def cog_after_invoke(self, ctx: commands.Context) -> None:
        lock = self._get_lock(ctx.author.id)
        if lock.locked():
            lock.release()

    @property
    def db(self):
        return self.bot.db

    # ── SQL helper layer ──────────────────────────────────────────────────────

    async def _ensure_economy(self, guild_id: int, user_id: int) -> None:
        """INSERT OR IGNORE a default economy row."""
        await self.db.execute(
            "INSERT OR IGNORE INTO economy (user_id, guild_id) VALUES (?, ?)",
            str(user_id), str(guild_id),
        )

    async def _ensure_extras(self, guild_id: int, user_id: int) -> None:
        await self.db.execute(
            "INSERT OR IGNORE INTO economy_extras (user_id, guild_id) VALUES (?, ?)",
            str(user_id), str(guild_id),
        )

    async def get_economy(self, guild_id: int, user_id: int):
        await self._ensure_economy(guild_id, user_id)
        return await self.db.fetchone(
            "SELECT * FROM economy WHERE user_id=? AND guild_id=?",
            str(user_id), str(guild_id),
        )

    async def get_extras(self, guild_id: int, user_id: int):
        await self._ensure_extras(guild_id, user_id)
        return await self.db.fetchone(
            "SELECT * FROM economy_extras WHERE user_id=? AND guild_id=?",
            str(user_id), str(guild_id),
        )

    async def get_inventory(self, guild_id: int, user_id: int) -> dict[str, int]:
        rows = await self.db.fetchall(
            "SELECT item_id, quantity FROM inventory WHERE user_id=? AND guild_id=?",
            str(user_id), str(guild_id),
        )
        return {r["item_id"]: r["quantity"] for r in rows if r["quantity"] > 0}

    async def set_inventory_item(self, guild_id: int, user_id: int, item_id: str, quantity: int) -> None:
        if quantity <= 0:
            await self.db.execute(
                "DELETE FROM inventory WHERE user_id=? AND guild_id=? AND item_id=?",
                str(user_id), str(guild_id), item_id,
            )
        else:
            await self.db.execute(
                """INSERT INTO inventory (user_id, guild_id, item_id, quantity)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, guild_id, item_id) DO UPDATE SET quantity=excluded.quantity""",
                str(user_id), str(guild_id), item_id, quantity,
            )

    async def add_inventory_item(self, guild_id: int, user_id: int, item_id: str, amount: int = 1) -> None:
        if amount <= 0: return
        await self.db.execute(
            """INSERT INTO inventory (user_id, guild_id, item_id, quantity)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, guild_id, item_id) DO UPDATE SET quantity=quantity + excluded.quantity""",
            str(user_id), str(guild_id), item_id, amount
        )

    async def add_wallet(self, guild_id: int, user_id: int, amount: int) -> None:
        """Public helper so other cogs (e.g. Fun.trivia) can award coins."""
        await self._ensure_economy(guild_id, user_id)
        await self.db.execute(
            "UPDATE economy SET wallet = wallet + ? WHERE user_id=? AND guild_id=?",
            amount, str(user_id), str(guild_id),
        )

    # ── Ban / Error handling ──────────────────────────────────────────────────

    async def cog_check(self, ctx: commands.Context) -> bool:
        row = await self.db.fetchone(
            "SELECT 1 FROM eco_bans WHERE user_id=?",
            str(ctx.author.id),
        )
        if row:
            await ctx.send("❌ You are permanently banned from the economy system.")
            return False
        return True

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"❌ Cooldown active! Please wait **{error.retry_after:.1f}s**.")
        else:
            log.exception("Economy command error in %s", ctx.command, exc_info=error)
            await ctx.send(f"An error occurred: {error}")

    # ── on_message (master_crown) ─────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        inv = await self.get_inventory(message.guild.id, message.author.id)
        if inv.get("master_crown", 0) <= 0:
            return

        extras = await self.get_extras(message.guild.id, message.author.id)
        last_time = extras["last_message_time"] or 0.0
        now = time.time()

        if last_time > 0 and (now - last_time) >= 10800:
            praises = [
                "Oh my god! My supreme master {user} has arrived! 👑",
                "The absolute light of this server, my master {user} is here! 👑",
                "Our master {user} has finally graced the chat! 👑",
                "Master {user} has arrived — make way! 👑",
                "The sole ruler of this server, master {user} is here! 👑",
                "Welcome back, my master {user}! The chat missed you. 👑",
            ]
            praise = random.choice(praises).format(user=message.author.mention)
            try:
                await message.reply(praise)
            except Exception:
                pass

        await self.db.execute(
            "UPDATE economy_extras SET last_message_time=? WHERE user_id=? AND guild_id=?",
            now, str(message.author.id), str(message.guild.id),
        )

    # ── Perk Commands ─────────────────────────────────────────────────────────

    @commands.group(name="perk", invoke_without_command=True)
    async def perk_group(self, ctx: commands.Context) -> None:
        """Manage and activate your purchased perks."""
        await ctx.send(
            "🎯 **Perk Activation Suite**\n"
            f"• `{ctx.prefix}perk color <hex>` — Requires Custom Color Perk\n"
            f"• `{ctx.prefix}perk title <text>` — Requires Custom Title Perk"
        )

    @perk_group.command(name="color")
    async def perk_color(self, ctx: commands.Context, color_hex: str = None) -> None:
        """color işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.color [parametreler]`"""
        if not color_hex:
            return await ctx.send(f"Usage: `{ctx.prefix}perk color <hex>` e.g. `#ff0000`")

        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        if inv.get("chat_color", 0) <= 0:
            return await ctx.send("❌ You do not own the Custom Color Perk!")

        target_role = None
        for role in ctx.author.roles:
            if role != ctx.guild.default_role and role.position < ctx.guild.me.top_role.position:
                target_role = role
                break

        if not target_role:
            return await ctx.send("❌ I couldn't find an editable role assigned to you.")

        try:
            color = discord.Color(int(color_hex.replace("#", ""), 16))
        except ValueError:
            return await ctx.send("❌ Invalid hex color format!")

        try:
            await target_role.edit(color=color, reason=f"Perk by {ctx.author}")
            await ctx.send(f"🎨 Changed `{target_role.name}`'s color to `{color_hex}`!")
        except discord.Forbidden:
            await ctx.send("❌ Missing permissions to edit your role.")

    @perk_group.command(name="title")
    async def perk_title(self, ctx: commands.Context, *, text: str = None) -> None:
        """title işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.title [parametreler]`"""
        if not text:
            return await ctx.send(f"Usage: `{ctx.prefix}perk title <text>`")

        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        if inv.get("custom_title", 0) <= 0:
            return await ctx.send("❌ You do not own the Custom Title Perk!")

        await self._ensure_extras(ctx.guild.id, ctx.author.id)
        await self.db.execute(
            "UPDATE economy_extras SET custom_title_text=? WHERE user_id=? AND guild_id=?",
            text[:50], str(ctx.author.id), str(ctx.guild.id),
        )
        await ctx.send(f"🏷️ Custom title set to: `{text[:50]}`!")

    # ── Balance / Deposit / Withdraw ──────────────────────────────────────────
    @commands.command(name="balance", aliases=["bal", "wallet"])

    @kumiho_check("public")
    async def balance(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """balance işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.balance [@user]`"""
        member = member or ctx.author
        eco = await self.get_economy(ctx.guild.id, member.id)
        extras = await self.get_extras(ctx.guild.id, member.id)

        wallet, bank = eco["wallet"], eco["bank"]
        custom_title = extras["custom_title_text"]
        title = f"👑 [{custom_title}] {member.display_name}'s Balance" if custom_title else f"{member.display_name}'s Balance"

        embed = discord.Embed(title=title, color=discord.Color.gold())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Wallet", value=f"{wallet:,} coins", inline=True)
        embed.add_field(name="Bank", value=f"{bank:,} coins", inline=True)
        embed.add_field(name="Total", value=f"{wallet + bank:,} coins", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)
    @commands.command(name="deposit", aliases=["dep"])

    @kumiho_check("public")
    async def deposit(self, ctx: commands.Context, amount: str = None) -> None:
        """deposit işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.deposit <amount | all>`"""
        if not amount:
            return await ctx.send(f"Usage: `{ctx.prefix}deposit <amount | all>`")

        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        wallet = eco["wallet"]

        dep = wallet if amount.lower() == "all" else self._parse_int(amount)
        if dep is None:
            return await ctx.send("❌ Please provide a valid number or `all`.")
        if dep <= 0:
            return await ctx.send("❌ Deposit amount must be positive.")

        res = await self.db.execute(
            "UPDATE economy SET wallet=wallet-?, bank=bank+? WHERE user_id=? AND guild_id=? AND wallet >= ?",
            dep, dep, str(ctx.author.id), str(ctx.guild.id), dep,
        )
        if res.rowcount == 0:
            return await ctx.send("❌ Not enough coins in your wallet.")

        await ctx.send(f"🏦 Deposited **{dep:,} coins** to your bank.")
    @commands.command(name="withdraw", aliases=["with"])

    @kumiho_check("public")
    async def withdraw(self, ctx: commands.Context, amount: str = None) -> None:
        """withdraw işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.withdraw <amount | all>`"""
        if not amount:
            return await ctx.send(f"Usage: `{ctx.prefix}withdraw <amount | all>`")

        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        bank = eco["bank"]

        amt = bank if amount.lower() == "all" else self._parse_int(amount)
        if amt is None:
            return await ctx.send("❌ Please provide a valid number or `all`.")
        if amt <= 0:
            return await ctx.send("❌ Withdrawal amount must be positive.")

        res = await self.db.execute(
            "UPDATE economy SET bank=bank-?, wallet=wallet+? WHERE user_id=? AND guild_id=? AND bank >= ?",
            amt, amt, str(ctx.author.id), str(ctx.guild.id), amt,
        )
        if res.rowcount == 0:
            return await ctx.send("❌ Not enough coins in your bank.")

        await ctx.send(f"💰 Withdrew **{amt:,} coins** to your wallet.")

    # ── Income Commands ───────────────────────────────────────────────────────
    @commands.command(name="daily")

    @kumiho_check("public")
    async def daily(self, ctx: commands.Context) -> None:
        """daily işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.daily`"""
        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        now = time.time()
        cd = eco["daily_cooldown"] or 0.0

        if now < cd:
            return await ctx.send(f"⏱️ Try again in **{_fmt_cd(cd - now)}**.")

        reward = random.randint(500, 1000)
        await self.db.execute(
            "UPDATE economy SET wallet=wallet+?, daily_cooldown=? WHERE user_id=? AND guild_id=?",
            reward, now + 86400, str(ctx.author.id), str(ctx.guild.id),
        )
        embed = discord.Embed(
            title="🎁 Daily Reward",
            description=f"You claimed **{reward:,} coins**!",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)
    @commands.command(name="work")

    @kumiho_check("public")
    async def work(self, ctx: commands.Context) -> None:
        """work işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.work`"""
        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        now = time.time()
        cd = eco["work_cooldown"] or 0.0

        if now < cd:
            return await ctx.send(f"⏱️ Rest! Wait **{_fmt_cd(cd - now)}**.")

        jobs = [
            ("Madagascar Penguin Researcher", 150, 300),
            ("Discord Bot Developer",         200, 450),
            ("Pizza Delivery Driver",         100, 200),
            ("Submarine Pilot",               250, 500),
            ("Sticker Designer",               80, 180),
            ("Space Explorer",                300, 600),
            ("Cyber Security Consultant",     220, 480),
        ]
        job_name, mn, mx = random.choice(jobs)
        payout = random.randint(mn, mx)

        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        boost = ""
        if inv.get("lucky_gem", 0) > 0:
            payout = int(payout * 1.25)
            boost += " *(Gem +25%)*"
        if inv.get("bank_card", 0) > 0:
            payout = int(payout * 1.15)
            boost += " *(Card +15%)*"

        await self.db.execute(
            "UPDATE economy SET wallet=wallet+?, work_cooldown=? WHERE user_id=? AND guild_id=?",
            payout, now + 1800, str(ctx.author.id), str(ctx.guild.id),
        )
        embed = discord.Embed(
            title="💼 Shift Completed",
            description=f"You worked as a **{job_name}** and earned **{payout:,} coins**!{boost}",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)
    @commands.command(name="beg")

    @kumiho_check("public")
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    async def beg(self, ctx: commands.Context) -> None:
        """beg işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.beg`"""
        if random.random() < 0.60:
            coins = random.randint(15, 80)
            await self.add_wallet(ctx.guild.id, ctx.author.id, coins)
            responses = [
                f"Skipper felt generous and tossed you **{coins:,} coins**! 🐧",
                f"King Julien dropped **{coins:,} coins** in your hat! 👑",
                f"A kind stranger handed you **{coins:,} coins**! 🪙",
                f"You found **{coins:,} coins** on the ground! 🎉",
            ]
            await ctx.send(random.choice(responses))
        else:
            responses = [
                "Rico growled at you. No coins! ❌",
                "Kowalski analyzed your request: 'No way.' ❌",
                "A stranger ignored you. ❌",
                "Go get a job! ❌",
            ]
            await ctx.send(random.choice(responses))

    # ── Gathering ─────────────────────────────────────────────────────────────
    @commands.command(name="fish")

    @kumiho_check("public")
    async def fish(self, ctx: commands.Context) -> None:
        """fish işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.fish (requires Fishing Rod)`"""
        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        if inv.get("fishing_rod", 0) <= 0:
            return await ctx.send(f"❌ You need a **Fishing Rod**! Buy one from `{ctx.prefix}shop`.")

        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        now = time.time()
        if now < (eco["fish_cooldown"] or 0.0):
            return await ctx.send(f"⏱️ Wait **{_fmt_cd(eco['fish_cooldown'] - now)}** before fishing again.")

        fish_types = [
            ("junk_boot",   "Junk Boot 👢",       0.15),
            ("common_fish", "Common Fish 🐟",     0.55),
            ("salmon",      "Salmon 🐠",          0.22),
            ("golden_bass", "Golden Bass 🐡",     0.08),
        ]
        key, name = self._weighted_choice(fish_types)

        qty = inv.get(key, 0) + 1
        await self.set_inventory_item(ctx.guild.id, ctx.author.id, key, qty)
        await self.db.execute(
            "UPDATE economy SET fish_cooldown=? WHERE user_id=? AND guild_id=?",
            now + 120, str(ctx.author.id), str(ctx.guild.id),
        )
        embed = discord.Embed(
            title="🎣 Fishing Success",
            description=f"You caught a **{name}**!\nSell via `{ctx.prefix}sell {key}`.",
            color=discord.Color.teal(),
        )
        await ctx.send(embed=embed)
    @commands.command(name="hunt")

    @kumiho_check("public")
    async def hunt(self, ctx: commands.Context) -> None:
        """hunt işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.hunt (requires Hunting Rifle)`"""
        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        if inv.get("hunting_rifle", 0) <= 0:
            return await ctx.send(f"❌ You need a **Hunting Rifle**! Buy one from `{ctx.prefix}shop`.")

        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        now = time.time()
        if now < (eco["hunt_cooldown"] or 0.0):
            return await ctx.send(f"⏱️ Wait **{_fmt_cd(eco['hunt_cooldown'] - now)}** before hunting again.")

        animals = [
            ("rabbit",       "Rabbit 🐇",        0.50),
            ("deer",         "Deer 🦌",          0.30),
            ("wild_boar",    "Wild Boar 🐗",     0.17),
            ("golden_dragon","Golden Dragon 🐉", 0.03),
        ]
        key, name = self._weighted_choice(animals)

        qty = inv.get(key, 0) + 1
        await self.set_inventory_item(ctx.guild.id, ctx.author.id, key, qty)
        await self.db.execute(
            "UPDATE economy SET hunt_cooldown=? WHERE user_id=? AND guild_id=?",
            now + 180, str(ctx.author.id), str(ctx.guild.id),
        )
        embed = discord.Embed(
            title="🎯 Hunting Success",
            description=f"You tracked down a **{name}**!\nSell via `{ctx.prefix}sell {key}`.",
            color=discord.Color.dark_green(),
        )
        await ctx.send(embed=embed)
    @commands.command(name="mine")

    @kumiho_check("public")
    async def mine(self, ctx: commands.Context) -> None:
        """mine işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.mine (requires Steel Pickaxe)`"""
        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        if inv.get("pickaxe", 0) <= 0:
            return await ctx.send(f"❌ You need a **Steel Pickaxe**! Buy one from `{ctx.prefix}shop`.")

        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        now = time.time()
        if now < (eco["mine_cooldown"] or 0.0):
            return await ctx.send(f"⏱️ Wait **{_fmt_cd(eco['mine_cooldown'] - now)}** before mining again.")

        ores = [
            ("coal",    "Coal Ore 🪨",    0.45),
            ("iron",    "Iron Ore 🪙",    0.30),
            ("gold",    "Gold Ore 🪙",    0.15),
            ("diamond", "Diamond Gems 💎", 0.08),
            ("emerald", "Emerald Gems 💚", 0.02),
        ]
        key, name = self._weighted_choice(ores)

        qty = inv.get(key, 0) + 1
        await self.set_inventory_item(ctx.guild.id, ctx.author.id, key, qty)
        await self.db.execute(
            "UPDATE economy SET mine_cooldown=? WHERE user_id=? AND guild_id=?",
            now + 180, str(ctx.author.id), str(ctx.guild.id),
        )
        embed = discord.Embed(
            title="⛏️ Mining Operation",
            description=f"You struck **{name}**! Sell via `{ctx.prefix}sell {key}`.",
            color=discord.Color.dark_gray(),
        )
        await ctx.send(embed=embed)

    # ── Shop / Inventory ──────────────────────────────────────────────────────
    @commands.command(name="shop", aliases=["store"])

    @kumiho_check("public")
    async def shop(self, ctx: commands.Context) -> None:
        """shop işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.shop`"""
        embed = discord.Embed(
            title="🏪 Server Item Shop",
            description="Buy equipment, shields, perks, and more!",
            color=discord.Color.blurple(),
        )
        for key, item in SHOP_ITEMS.items():
            embed.add_field(
                name=f"{item['name']} — {item['price']:,} coins",
                value=f"{item['desc']}\n`ID: {key}`",
                inline=False,
            )
        embed.set_footer(text=f"Buy with: {ctx.prefix}buy <item_id>")
        await ctx.send(embed=embed)
    @commands.command(name="buy")

    @kumiho_check("public")
    async def buy(self, ctx: commands.Context, item_id: str = None) -> None:
        """buy işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.buy <item_id>`"""
        if not item_id or item_id not in SHOP_ITEMS:
            return await ctx.send(f"❌ Invalid item! Check `{ctx.prefix}shop` for IDs.")

        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        item = SHOP_ITEMS[item_id]
        price = item["price"]

        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        if item_id in NON_STACKABLE and inv.get(item_id, 0) > 0:
            return await ctx.send("❌ You already own this item!")

        res = await self.db.execute(
            "UPDATE economy SET wallet=wallet-? WHERE user_id=? AND guild_id=? AND wallet >= ?",
            price, str(ctx.author.id), str(ctx.guild.id), price,
        )
        if res.rowcount == 0:
            return await ctx.send(f"❌ You need **{price:,} coins** in your wallet.")

        if item_id in NON_STACKABLE:
            await self.set_inventory_item(ctx.guild.id, ctx.author.id, item_id, 1)
        else:
            await self.add_inventory_item(ctx.guild.id, ctx.author.id, item_id, 1)
            
        await ctx.send(f"🎉 Purchased **{item['name']}** for **{price:,} coins**!")
    @commands.command(name="sell")

    @kumiho_check("public")
    async def sell(self, ctx: commands.Context, item_id: str = None, amount: str = "1") -> None:
        """sell işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.sell <item_id> [amount | all]`"""
        if not item_id or item_id not in SELLABLE_ITEMS:
            return await ctx.send(f"Usage: `{ctx.prefix}sell <item_id> [amount | all]`")

        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        owned = inv.get(item_id, 0)

        if owned <= 0:
            return await ctx.send(f"❌ You don't own any **{SELLABLE_ITEMS[item_id]['name']}**.")

        qty = owned if amount.lower() == "all" else self._parse_int(amount)
        if qty is None or qty <= 0 or qty > owned:
            return await ctx.send(f"❌ Invalid amount. You own **{owned}**.")

        item = SELLABLE_ITEMS[item_id]
        earnings = item["value"] * qty
        
        res = await self.db.execute(
            "UPDATE inventory SET quantity=quantity-? WHERE user_id=? AND guild_id=? AND item_id=? AND quantity >= ?",
            qty, str(ctx.author.id), str(ctx.guild.id), item_id, qty
        )
        if res.rowcount == 0:
            return await ctx.send(f"❌ Yetersiz miktar. O kadar **{item['name']}** eşyasına sahip değilsiniz.")
            
        await self.add_wallet(ctx.guild.id, ctx.author.id, earnings)
        await ctx.send(f"💰 Sold **{qty}x {item['name']}** for **{earnings:,} coins**!")
    @commands.command(name="inventory", aliases=["inv"])

    @kumiho_check("public")
    async def inventory(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """inventory işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.inventory [@user]`"""
        member = member or ctx.author
        inv = await self.get_inventory(ctx.guild.id, member.id)

        embed = discord.Embed(
            title=f"{member.display_name}'s Inventory", color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        desc = ""
        for key, qty in inv.items():
            if qty > 0:
                item = SELLABLE_ITEMS.get(key)
                if item:
                    desc += f"• **{item['name']}** — Quantity: `{qty}`\n"
        embed.description = desc or "*Backpack is empty!*"
        embed.set_footer(text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)
    @commands.command(name="use")

    @kumiho_check("public")
    async def use(self, ctx: commands.Context, item_id: str = None) -> None:
        """use işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.use [parametreler]`"""
        if not item_id:
            return await ctx.send(f"Usage: `{ctx.prefix}use <item_id>`")

        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        if inv.get(item_id, 0) <= 0:
            return await ctx.send(f"❌ You don't own any `{item_id}`!")

        if item_id == "padlock":
            eco = await self.get_economy(ctx.guild.id, ctx.author.id)
            if eco["padlock_active"]:
                return await ctx.send("❌ You already have an active Padlock!")
            await self.db.execute(
                "UPDATE economy SET padlock_active=1 WHERE user_id=? AND guild_id=?",
                str(ctx.author.id), str(ctx.guild.id),
            )
            await self.set_inventory_item(ctx.guild.id, ctx.author.id, "padlock", inv["padlock"] - 1)
            await ctx.send("🔒 Activated your **Shield Padlock**! Next rob attempt will be blocked.")

        elif item_id == "scratch_card":
            await self.set_inventory_item(ctx.guild.id, ctx.author.id, "scratch_card", inv["scratch_card"] - 1)
            payout, msg = self._scratch_roll()
            await self.add_wallet(ctx.guild.id, ctx.author.id, payout)
            await ctx.send(msg)
        else:
            await ctx.send(f"❌ `{item_id}` is not directly usable here. Try `padlock` or `scratch_card`.")

    # ── Gambling ──────────────────────────────────────────────────────────────
    @commands.command(name="slots")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def slots(self, ctx: commands.Context, bet: str = None) -> None:
        """slots işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.slots <bet | all>`"""
        if not bet:
            return await ctx.send(f"Usage: `{ctx.prefix}slots <bet | all>`")

        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        wallet = eco["wallet"]
        bet_amount = wallet if bet.lower() == "all" else self._parse_int(bet)
        if bet_amount is None or bet_amount <= 0:
            return await ctx.send("❌ Invalid bet amount.")

        res = await self.db.execute(
            "UPDATE economy SET wallet=wallet-? WHERE user_id=? AND guild_id=? AND wallet >= ?",
            bet_amount, str(ctx.author.id), str(ctx.guild.id), bet_amount
        )
        if res.rowcount == 0:
            return await ctx.send("❌ Not enough coins in your wallet.")

        embed = discord.Embed(
            title="🎰 Slot Machine",
            description="```\n[ 🔄 | 🔄 | 🔄 ]\n```\n*Spinning...*",
            color=discord.Color.blue(),
        )
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(0.7)

        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        choices = ["🍋", "🍒", "🍊", "🍇", "💎", "💎", "👑", "👑"] if inv.get("lucky_gem", 0) > 0 \
                  else ["🍋", "🍒", "🍊", "🍇", "💎", "👑"]

        s1, s2, s3 = random.choice(choices), random.choice(choices), random.choice(choices)

        for step, state in [
            (f"[ {s1} | 🔄 | 🔄 ]", "*Reel 1 stopped...*"),
            (f"[ {s1} | {s2} | 🔄 ]", "*Reel 2 stopped...*"),
        ]:
            embed.description = f"```\n{step}\n```\n{state}"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.7)

        winnings = 0
        if s1 == s2 == s3:
            mult = 5 if s1 == "👑" else 4 if s1 == "💎" else 3
            winnings = bet_amount * mult
        elif s1 == s2 or s2 == s3 or s1 == s3:
            winnings = int(bet_amount * 1.5)

        if winnings > 0 and inv.get("clover", 0) > 0:
            winnings = int(winnings * 1.10)

        if winnings > 0:
            await self.db.execute(
                "UPDATE economy SET wallet=wallet+? WHERE user_id=? AND guild_id=?",
                winnings, str(ctx.author.id), str(ctx.guild.id),
            )

        result = f"🎉 **YOU WON {winnings:,} coins**!" if winnings > 0 else "😢 **YOU LOST!** Better luck next spin."
        embed.description = f"```\n[ {s1} | {s2} | {s3} ]\n```\n{result}"
        embed.color = discord.Color.green() if winnings > 0 else discord.Color.red()
        await msg.edit(embed=embed)
    @commands.command(name="gamble", aliases=["cfg"])

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def gamble(self, ctx: commands.Context, choice: str = None, bet: str = None) -> None:
        """gamble işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.gamble <heads|tails> <bet | all>`"""
        if not choice or not bet:
            return await ctx.send(f"Usage: `{ctx.prefix}gamble <heads|tails> <bet | all>`")
        user_choice = choice.strip().lower()
        if user_choice not in ("heads", "tails"):
            return await ctx.send("❌ Choose `heads` or `tails`.")

        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        wallet = eco["wallet"]
        bet_amount = wallet if bet.lower() == "all" else self._parse_int(bet)
        if bet_amount is None or bet_amount <= 0:
            return await ctx.send("❌ Invalid bet or not enough coins.")

        res = await self.db.execute(
            "UPDATE economy SET wallet=wallet-? WHERE user_id=? AND guild_id=? AND wallet >= ?",
            bet_amount, str(ctx.author.id), str(ctx.guild.id), bet_amount
        )
        if res.rowcount == 0:
            return await ctx.send("❌ Not enough coins in your wallet.")

        embed = discord.Embed(
            title="🪙 High-Stakes Coin Flip",
            description="*The coin is spinning...* 🔄",
            color=discord.Color.gold(),
        )
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(1.0)

        flipped = random.choice(("heads", "tails"))
        if user_choice == flipped:
            winnings = bet_amount * 2
            await self.db.execute(
                "UPDATE economy SET wallet=wallet+? WHERE user_id=? AND guild_id=?",
                winnings, str(ctx.author.id), str(ctx.guild.id),
            )
            embed.description = f"🎉 **YOU WON!** Coin: **{flipped}**. You earned **{winnings:,} coins**!"
            embed.color = discord.Color.green()
        else:
            embed.description = f"😢 **YOU LOST!** Coin: **{flipped}**. You lost **{bet_amount:,} coins**."
            embed.color = discord.Color.red()
        await msg.edit(embed=embed)
    @commands.command(name="roulette")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def roulette(self, ctx: commands.Context, bet_on: str = None, bet: str = None) -> None:
        """roulette işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.roulette <red|black|green|0-36> <bet | all>`"""
        if not bet_on or not bet:
            return await ctx.send(f"Usage: `{ctx.prefix}roulette <red|black|green|0-36> <bet | all>`")

        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        wallet = eco["wallet"]
        bet_amount = wallet if bet.lower() == "all" else self._parse_int(bet)
        if bet_amount is None or bet_amount <= 0:
            return await ctx.send("❌ Invalid bet or not enough coins.")

        res = await self.db.execute(
            "UPDATE economy SET wallet=wallet-? WHERE user_id=? AND guild_id=? AND wallet >= ?",
            bet_amount, str(ctx.author.id), str(ctx.guild.id), bet_amount
        )
        if res.rowcount == 0:
            return await ctx.send("❌ Not enough coins in your wallet.")

        embed = discord.Embed(
            title="🎰 French Roulette",
            description="*The wheel is spinning...* 🔄",
            color=discord.Color.blue(),
        )
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(1.0)

        roll = random.randint(0, 36)
        roll_color = "green" if roll == 0 else ("black" if roll % 2 == 0 else "red")
        bet_on = bet_on.strip().lower()

        win, mult = False, 0
        if bet_on == roll_color:
            win, mult = True, 3 if roll_color == "green" else 2
        elif bet_on.isdigit() and int(bet_on) == roll:
            win, mult = True, 35

        if win:
            winnings = bet_amount * mult
            await self.db.execute(
                "UPDATE economy SET wallet=wallet+? WHERE user_id=? AND guild_id=?",
                winnings, str(ctx.author.id), str(ctx.guild.id),
            )
            embed.description = f"🎉 **YOU WON!** Ball landed on **{roll_color.upper()} {roll}**. You won **{winnings:,} coins**!"
            embed.color = discord.Color.green()
        else:
            embed.description = f"😢 **YOU LOST!** Ball landed on **{roll_color.upper()} {roll}**."
            embed.color = discord.Color.red()
        await msg.edit(embed=embed)
    @commands.command(name="blackjack", aliases=["bj"])

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def blackjack(self, ctx: commands.Context, bet: str = None) -> None:
        """blackjack işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.blackjack <bet | all>`"""
        if not bet:
            return await ctx.send(f"Usage: `{ctx.prefix}blackjack <bet | all>`")

        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        wallet = eco["wallet"]
        bet_amount = wallet if bet.lower() == "all" else self._parse_int(bet)
        if bet_amount is None or bet_amount <= 0:
            return await ctx.send("❌ Invalid bet or not enough coins.")

        res = await self.db.execute(
            "UPDATE economy SET wallet=wallet-? WHERE user_id=? AND guild_id=? AND wallet >= ?",
            bet_amount, str(ctx.author.id), str(ctx.guild.id), bet_amount
        )
        if res.rowcount == 0:
            return await ctx.send("❌ Not enough coins in your wallet.")

        suits = ["♠️", "♥️", "♦️", "♣️"]
        values = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

        def make_deck():
            return [{"suit": s, "val": v} for s in suits for v in values]

        def get_value(hand):
            total, aces = 0, 0
            for c in hand:
                if c["val"] in ("J", "Q", "K"):
                    total += 10
                elif c["val"] == "A":
                    aces += 1; total += 11
                else:
                    total += int(c["val"])
            while total > 21 and aces:
                total -= 10; aces -= 1
            return total

        def fmt(hand, hide=False):
            if hide:
                return f"`[ ? ]` and `[ {hand[1]['val']}{hand[1]['suit']} ]`"
            return ", ".join(f"`[ {c['val']}{c['suit']} ]`" for c in hand)

        deck = make_deck(); random.shuffle(deck)
        ph = [deck.pop(), deck.pop()]
        dh = [deck.pop(), deck.pop()]

        if get_value(ph) == 21:
            if get_value(dh) == 21:
                await self.add_wallet(ctx.guild.id, ctx.author.id, bet_amount)
                return await ctx.send(f"Push! Both got Blackjack. Refunded **{bet_amount:,} coins**.")
            w = int(bet_amount * 2.5)
            await self.add_wallet(ctx.guild.id, ctx.author.id, w)
            return await ctx.send(f"🎉 **Blackjack!** You won **{w:,} coins**!")

        embed = discord.Embed(title="🃏 Blackjack Table", color=discord.Color.blue())
        embed.add_field(name="Your Hand", value=f"{fmt(ph)} (Value: {get_value(ph)})", inline=False)
        embed.add_field(name="Dealer Hand", value=fmt(dh, True), inline=False)
        embed.set_footer(text="Type 'hit'/'h' or 'stand'/'s'")
        msg = await ctx.send(embed=embed)

        def check(m):
            return (m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
                    and m.content.lower() in ("hit", "h", "stand", "s"))

        playing = True
        while playing:
            try:
                am = await self.bot.wait_for("message", check=check, timeout=30.0)
                if am.content.lower() in ("hit", "h"):
                    if not deck:
                        deck = make_deck()
                        random.shuffle(deck)
                    ph.append(deck.pop())
                    pv = get_value(ph)
                    if pv > 21:
                        embed.description = "😢 **Bust!**"
                        embed.color = discord.Color.red()
                        embed.set_field_at(0, name="Your Hand", value=f"{fmt(ph)} (Value: {pv})", inline=False)
                        embed.set_field_at(1, name="Dealer Hand", value=f"{fmt(dh)} (Value: {get_value(dh)})", inline=False)
                        await msg.edit(embed=embed)
                        return
                    embed.set_field_at(0, name="Your Hand", value=f"{fmt(ph)} (Value: {pv})", inline=False)
                    await msg.edit(embed=embed)
                else:
                    playing = False
            except asyncio.TimeoutError:
                playing = False
                await ctx.send("⏱️ Timed out! Standing automatically.")

        dv = get_value(dh)
        while dv < 17:
            if not deck:
                deck = make_deck()
                random.shuffle(deck)
            dh.append(deck.pop()); dv = get_value(dh)
        pv = get_value(ph)

        if dv > 21:
            w = bet_amount * 2; await self.add_wallet(ctx.guild.id, ctx.author.id, w)
            desc, col = f"🎉 **Dealer Bust!** You won **{w:,} coins**!", discord.Color.green()
        elif pv > dv:
            w = bet_amount * 2; await self.add_wallet(ctx.guild.id, ctx.author.id, w)
            desc, col = f"🎉 **You Win!** Won **{w:,} coins**!", discord.Color.green()
        elif pv < dv:
            desc, col = f"😢 **Dealer Wins!** Lost **{bet_amount:,} coins**.", discord.Color.red()
        else:
            await self.add_wallet(ctx.guild.id, ctx.author.id, bet_amount)
            desc, col = "Push! Refunded.", discord.Color.orange()

        embed.color = col; embed.description = desc
        embed.set_field_at(0, name="Your Hand", value=f"{fmt(ph)} (Value: {pv})", inline=False)
        embed.set_field_at(1, name="Dealer Hand", value=f"{fmt(dh)} (Value: {dv})", inline=False)
        embed.set_footer(text="Game Over")
        await msg.edit(embed=embed)
    @commands.command(name="highlow", aliases=["hl"])

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def highlow(self, ctx: commands.Context, bet: str = None) -> None:
        """highlow işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.highlow <bet | all>`"""
        if not bet:
            return await ctx.send(f"Usage: `{ctx.prefix}highlow <bet | all>`")

        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        wallet = eco["wallet"]
        bet_amount = wallet if bet.lower() == "all" else self._parse_int(bet)
        if bet_amount is None or bet_amount <= 0 or wallet < bet_amount:
            return await ctx.send("❌ Invalid bet or not enough coins.")

        await self.db.execute(
            "UPDATE economy SET wallet=wallet-? WHERE user_id=? AND guild_id=?",
            bet_amount, str(ctx.author.id), str(ctx.guild.id),
        )

        start = random.randint(10, 90)
        embed = discord.Embed(
            title="🎲 High-Low Guess",
            description=f"Current number: **{start}**\n\nIs the next number **higher** or **lower**?\nType `higher`/`h` or `lower`/`l`!",
            color=discord.Color.blue(),
        )
        msg = await ctx.send(embed=embed)

        def check(m):
            return (m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
                    and m.content.lower() in ("higher", "h", "lower", "l"))

        try:
            gm = await self.bot.wait_for("message", check=check, timeout=20.0)
            guess = gm.content.lower()
            nxt = start
            while nxt == start:
                nxt = random.randint(1, 100)

            win = (guess in ("higher", "h") and nxt > start) or (guess in ("lower", "l") and nxt < start)
            if win:
                w = bet_amount * 2; await self.add_wallet(ctx.guild.id, ctx.author.id, w)
                embed.description = f"🎉 **CORRECT!** Number was **{nxt}**. Won **{w:,} coins**!"
                embed.color = discord.Color.green()
            else:
                embed.description = f"😢 **WRONG!** Number was **{nxt}**. Lost **{bet_amount:,} coins**."
                embed.color = discord.Color.red()
        except asyncio.TimeoutError:
            embed.description = "⏱️ Timed out! You lost your bet."
            embed.color = discord.Color.red()

        await msg.edit(embed=embed)
    @commands.command(name="crime")

    @kumiho_check("public")
    @commands.cooldown(1, 2700, commands.BucketType.user)
    async def crime(self, ctx: commands.Context) -> None:
        """crime işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.crime (45min cooldown)`"""
        crimes = [
            ("robbed a local bakery",            400,  700),
            ("hacked a minor server",            500,  800),
            ("smuggled illicit anime figures",   600, 1000),
            ("embezzled bank tax refunds",       700, 1200),
        ]
        name, mn, mx = random.choice(crimes)

        if random.random() < 0.60:
            payout = random.randint(mn, mx)
            inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
            if inv.get("lucky_gem", 0):
                payout = int(payout * 1.25)
            if inv.get("bank_card", 0):
                payout = int(payout * 1.15)
            await self.add_wallet(ctx.guild.id, ctx.author.id, payout)
            embed = discord.Embed(
                title="🕵️ Crime Successful",
                description=f"You **{name}** and pocketed **{payout:,} coins**!",
                color=discord.Color.green(),
            )
        else:
            eco = await self.get_economy(ctx.guild.id, ctx.author.id)
            fine = min(eco["wallet"], random.randint(200, 600))
            await self.db.execute(
                "UPDATE economy SET wallet=wallet-? WHERE user_id=? AND guild_id=?",
                fine, str(ctx.author.id), str(ctx.guild.id),
            )
            embed = discord.Embed(
                title="👮 Crime Failed",
                description=f"You were busted and fined **{fine:,} coins**!",
                color=discord.Color.red(),
            )
        await ctx.send(embed=embed)
    @commands.command(name="scratch")

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def scratch(self, ctx: commands.Context) -> None:
        """scratch işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.scratch`"""
        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        if inv.get("scratch_card", 0) <= 0:
            res = await self.db.execute(
                "UPDATE economy SET wallet=wallet-200 WHERE user_id=? AND guild_id=? AND wallet >= 200",
                str(ctx.author.id), str(ctx.guild.id),
            )
            if res.rowcount == 0:
                return await ctx.send("❌ You need a scratch card or **200 coins** to buy one!")

        payout, msg_text = self._scratch_roll()
        await self.add_wallet(ctx.guild.id, ctx.author.id, payout)
        await ctx.send(msg_text)

    # ── Rob / Pay ─────────────────────────────────────────────────────────────
    @commands.command(name="rob", aliases=["steal"])

    @kumiho_check("public")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def rob(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """rob işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.rob @user`"""
        if not member:
            return await ctx.send(f"Usage: `{ctx.prefix}rob @user`")
        if member.id == ctx.author.id:
            return await ctx.send("❌ You cannot rob yourself!")
        if member.bot:
            return await ctx.send("❌ You cannot rob bots!")

        author_eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        target_eco = await self.get_economy(ctx.guild.id, member.id)
        now = time.time()

        if now < (author_eco["rob_cooldown"] or 0.0):
            return await ctx.send(f"⏱️ Wait **{_fmt_cd(author_eco['rob_cooldown'] - now)}** before robbing again.")
        if author_eco["wallet"] < 100:
            return await ctx.send("❌ You need at least **100 coins** to rob someone.")
        if target_eco["wallet"] < 100:
            return await ctx.send(f"❌ {member.mention} doesn't have enough coins to rob.")

        await self.db.execute(
            "UPDATE economy SET rob_cooldown=? WHERE user_id=? AND guild_id=?",
            now + 600, str(ctx.author.id), str(ctx.guild.id),
        )

        if target_eco["padlock_active"]:
            await self.db.execute(
                "UPDATE economy SET padlock_active=0 WHERE user_id=? AND guild_id=?",
                str(member.id), str(ctx.guild.id),
            )
            fine = min(author_eco["wallet"], random.randint(100, 500))
            res = await self.db.execute(
                "UPDATE economy SET wallet=wallet-? WHERE user_id=? AND guild_id=? AND wallet >= ?",
                fine, str(ctx.author.id), str(ctx.guild.id), fine
            )
            if res.rowcount > 0:
                await self.add_wallet(ctx.guild.id, member.id, fine)
            return await ctx.send(
                f"🔒 **{member.display_name}** had a Shield Padlock! "
                f"Rob failed; you were fined **{fine:,} coins** paid to them."
            )

        if random.random() < 0.50:
            pct = random.randint(10, 40)
            stolen = max(50, int(target_eco["wallet"] * pct / 100))
            res = await self.db.execute(
                "UPDATE economy SET wallet=wallet-? WHERE user_id=? AND guild_id=? AND wallet >= ?",
                stolen, str(member.id), str(ctx.guild.id), stolen
            )
            if res.rowcount > 0:
                await self.add_wallet(ctx.guild.id, ctx.author.id, stolen)
                await ctx.send(f"🎉 **SUCCESS!** You robbed {member.mention} and stole **{stolen:,} coins**!")
            else:
                await ctx.send(f"😕 You tried to rob {member.mention}, but their pockets were empty by the time you reached them!")
        else:
            fine = max(100, int(author_eco["wallet"] * 0.10))
            res = await self.db.execute(
                "UPDATE economy SET wallet=wallet-? WHERE user_id=? AND guild_id=? AND wallet >= ?",
                fine, str(ctx.author.id), str(ctx.guild.id), fine
            )
            if res.rowcount > 0:
                await self.add_wallet(ctx.guild.id, member.id, fine)
            await ctx.send(f"👮 **CAUGHT!** Fined **{fine:,} coins** paid to {member.mention}.")
    @commands.command(name="pay", aliases=["give"])

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def pay(self, ctx: commands.Context, member: discord.Member = None, amount: int = None) -> None:
        """pay işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.pay @user <amount>`"""
        if not member or amount is None or amount <= 0:
            return await ctx.send(f"Usage: `{ctx.prefix}pay @user <amount>`")
        if member.id == ctx.author.id:
            return await ctx.send("❌ You cannot pay yourself!")
        if member.bot:
            return await ctx.send("❌ You cannot pay bots!")

        res = await self.db.execute(
            "UPDATE economy SET wallet=wallet-? WHERE user_id=? AND guild_id=? AND wallet >= ?",
            amount, str(ctx.author.id), str(ctx.guild.id), amount
        )
        if res.rowcount == 0:
            return await ctx.send("❌ Not enough coins in your wallet!")

        await self.add_wallet(ctx.guild.id, member.id, amount)
        await ctx.send(f"💰 Transferred **{amount:,} coins** to {member.mention}!")

    # ── Marriage ──────────────────────────────────────────────────────────────
    @commands.command(name="marry")

    @kumiho_check("public")
    async def marry(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """marry işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.marry @user (requires Engagement Ring)`"""
        if not member:
            return await ctx.send(f"Usage: `{ctx.prefix}marry @user`")
        if member.id == ctx.author.id or member.bot:
            return await ctx.send("❌ Invalid target.")

        author_extras = await self.get_extras(ctx.guild.id, ctx.author.id)
        target_extras = await self.get_extras(ctx.guild.id, member.id)

        if author_extras["married_to"]:
            return await ctx.send(f"❌ You're already married! Divorce first via `{ctx.prefix}divorce`.")
        if target_extras["married_to"]:
            return await ctx.send(f"❌ {member.mention} is already married!")

        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        if inv.get("ring", 0) <= 0:
            return await ctx.send(f"❌ You need an **Engagement Ring 💍** from the `{ctx.prefix}shop`!")

        await ctx.send(
            f"💍 **{ctx.author.mention}** proposed to **{member.mention}**!\n"
            "Do you accept? Type `yes` to marry, `no` to decline."
        )

        def check(m):
            return (m.author.id == member.id and m.channel.id == ctx.channel.id
                    and m.content.lower() in ("yes", "no", "evet", "hayır"))

        try:
            reply = await self.bot.wait_for("message", check=check, timeout=30.0)
            if reply.content.lower() in ("yes", "evet"):
                await self.db.execute(
                    "UPDATE economy_extras SET married_to=? WHERE user_id=? AND guild_id=?",
                    str(member.id), str(ctx.author.id), str(ctx.guild.id),
                )
                await self.db.execute(
                    "UPDATE economy_extras SET married_to=? WHERE user_id=? AND guild_id=?",
                    str(ctx.author.id), str(member.id), str(ctx.guild.id),
                )
                await self.set_inventory_item(ctx.guild.id, ctx.author.id, "ring", inv["ring"] - 1)
                await ctx.send(f"🎉 **CONGRATULATIONS!** {ctx.author.mention} and {member.mention} are now married! 💍❤️")
            else:
                await ctx.send(f"💔 {member.mention} declined the proposal.")
        except asyncio.TimeoutError:
            await ctx.send("⏱️ The proposal expired.")
    @commands.command(name="divorce")

    @kumiho_check("public")
    async def divorce(self, ctx: commands.Context) -> None:
        """divorce işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.divorce`"""
        extras = await self.get_extras(ctx.guild.id, ctx.author.id)
        partner_id = extras["married_to"]
        if not partner_id:
            return await ctx.send("❌ You are not currently married.")

        await self.db.execute(
            "UPDATE economy_extras SET married_to=NULL WHERE user_id=? AND guild_id=?",
            str(ctx.author.id), str(ctx.guild.id),
        )
        await self.db.execute(
            "UPDATE economy_extras SET married_to=NULL WHERE user_id=? AND guild_id=?",
            partner_id, str(ctx.guild.id),
        )
        partner = ctx.guild.get_member(int(partner_id))
        await ctx.send(f"💔 You divorced {partner.mention if partner else f'ID: {partner_id}'}. You are now single.")

    # ── Profile / Leaderboard / Cooldowns ────────────────────────────────────
    @commands.command(name="profile", aliases=["prof"])

    @kumiho_check("public")
    async def profile(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """profile işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.profile [@user]`"""
        member = member or ctx.author
        eco = await self.get_economy(ctx.guild.id, member.id)
        extras = await self.get_extras(ctx.guild.id, member.id)
        inv = await self.get_inventory(ctx.guild.id, member.id)

        title = f"👑 [{extras['custom_title_text']}]" if extras["custom_title_text"] else "🎖️ Player Profile"
        embed = discord.Embed(title=title, description=f"Stats for {member.mention}", color=discord.Color.gold())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Wallet", value=f"🪙 {eco['wallet']:,}", inline=True)
        embed.add_field(name="Bank", value=f"🏦 {eco['bank']:,}", inline=True)
        embed.add_field(name="Net Worth", value=f"💰 {eco['wallet'] + eco['bank']:,}", inline=False)

        if extras["married_to"]:
            p = ctx.guild.get_member(int(extras["married_to"]))
            embed.add_field(name="Spouse", value=f"💍 {p.mention if p else extras['married_to']}", inline=True)
        else:
            embed.add_field(name="Relationship", value="💔 Single", inline=True)

        shield = "🔒 Active" if eco["padlock_active"] else "❌ None"
        embed.add_field(name="Shield", value=shield, inline=True)

        inv_desc = "".join(
            f"• {SELLABLE_ITEMS[k]['name']} x`{v}`\n"
            for k, v in inv.items() if v > 0 and k in SELLABLE_ITEMS
        )
        embed.add_field(name="Backpack", value=inv_desc or "*Empty*", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)
    @commands.command(name="leaderboard", aliases=["lb", "richest"])

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def leaderboard(self, ctx: commands.Context) -> None:
        """leaderboard işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.leaderboard`"""
        rows = await self.db.fetchall(
            "SELECT user_id, wallet, bank FROM economy WHERE guild_id=? ORDER BY (wallet+bank) DESC LIMIT 10",
            str(ctx.guild.id),
        )
        if not rows:
            return await ctx.send("❌ No economy profiles in this server yet.")

        embed = discord.Embed(title="🏆 Server Wealth Leaderboard", color=discord.Color.gold())
        desc = ""
        for idx, row in enumerate(rows, 1):
            m = ctx.guild.get_member(int(row["user_id"]))
            name = m.mention if m else f"ID: {row['user_id']}"
            net = row["wallet"] + row["bank"]
            desc += f"**#{idx}** {name} — Net Worth: `{net:,} coins`\n"
        embed.description = desc
        embed.set_footer(text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)
    @commands.command(name="cooldowns", aliases=["cd"])

    @kumiho_check("public")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def cooldowns(self, ctx: commands.Context) -> None:
        """cooldowns işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.cooldowns`"""
        eco = await self.get_economy(ctx.guild.id, ctx.author.id)
        now = time.time()
        timers = {
            "Daily Reward 🎁":       eco["daily_cooldown"] or 0.0,
            "Work Shift 💼":         eco["work_cooldown"]  or 0.0,
            "Fishing 🎣":            eco["fish_cooldown"]  or 0.0,
            "Hunting 🎯":            eco["hunt_cooldown"]  or 0.0,
            "Mining ⛏️":            eco["mine_cooldown"]  or 0.0,
            "Rob / Steal 🥷":        eco["rob_cooldown"]   or 0.0,
        }
        embed = discord.Embed(title="⏱️ Active Economy Cooldowns", color=discord.Color.orange())
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        desc = ""
        for label, cd in timers.items():
            if cd > now:
                desc += f"• **{label}** — Wait `{_fmt_cd(cd - now)}`\n"
            else:
                desc += f"• **{label}** — `Ready!`\n"
        embed.description = desc
        embed.set_footer(text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)

    # ── Farm ──────────────────────────────────────────────────────────────────

    @commands.group(name="farm", invoke_without_command=True)
    async def farm_group(self, ctx: commands.Context) -> None:
        """Virtual crop farm manager."""
        await ctx.send(
            "🌾 **Virtual Farm Controller**\n"
            f"• `{ctx.prefix}farm plant <wheat|carrot|melon>` — Plant a seed\n"
            f"• `{ctx.prefix}farm water` — Water crops (50% faster growth)\n"
            f"• `{ctx.prefix}farm status` — Check growth timer\n"
            f"• `{ctx.prefix}farm harvest` — Harvest fully grown crops"
        )

    @farm_group.command(name="plant")
    async def farm_plant(self, ctx: commands.Context, crop: str = None) -> None:
        """plant işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.plant [parametreler]`"""
        if not crop or crop.lower() not in CROP_GROW_TIMES:
            return await ctx.send(f"Usage: `{ctx.prefix}farm plant <wheat|carrot|melon>`")
        crop = crop.lower()

        extras = await self.get_extras(ctx.guild.id, ctx.author.id)
        if extras["farm_crop"]:
            return await ctx.send("❌ You already have a crop growing! Harvest it first.")

        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        seed_key = f"{crop}_seeds"
        if inv.get(seed_key, 0) <= 0:
            return await ctx.send(f"❌ You don't own any **{crop.title()} Seeds**! Buy from `{ctx.prefix}shop`.")

        await self.set_inventory_item(ctx.guild.id, ctx.author.id, seed_key, inv[seed_key] - 1)
        await self.db.execute(
            """UPDATE economy_extras
               SET farm_crop=?, farm_time=?, farm_watered=0
               WHERE user_id=? AND guild_id=?""",
            crop, time.time(), str(ctx.author.id), str(ctx.guild.id),
        )
        await ctx.send(f"🌱 Planted **{crop.title()}**! Check status with `{ctx.prefix}farm status`.")

    @farm_group.command(name="water")
    async def farm_water(self, ctx: commands.Context) -> None:
        """water işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.water [parametreler]`"""
        extras = await self.get_extras(ctx.guild.id, ctx.author.id)
        if not extras["farm_crop"]:
            return await ctx.send("❌ No crops growing in your plot!")
        if extras["farm_watered"]:
            return await ctx.send("❌ Already watered this grow cycle!")

        grow_needed = CROP_GROW_TIMES[extras["farm_crop"]]
        new_farm_time = extras["farm_time"] - (grow_needed // 2)
        await self.db.execute(
            "UPDATE economy_extras SET farm_time=?, farm_watered=1 WHERE user_id=? AND guild_id=?",
            new_farm_time, str(ctx.author.id), str(ctx.guild.id),
        )
        await ctx.send("💧 Watered your crops! Remaining grow time cut by **50%**.")

    @farm_group.command(name="status")
    async def farm_status(self, ctx: commands.Context) -> None:
        """status işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.status [parametreler]`"""
        extras = await self.get_extras(ctx.guild.id, ctx.author.id)
        if not extras["farm_crop"]:
            return await ctx.send(f"🌾 Farm plot empty. Plant seeds with `{ctx.prefix}farm plant <crop>`!")

        crop = extras["farm_crop"]
        elapsed = time.time() - extras["farm_time"]
        grow_needed = CROP_GROW_TIMES[crop]
        embed = discord.Embed(title="🌾 Farm Plot Status", color=discord.Color.green())

        if elapsed >= grow_needed:
            embed.description = f"Plot: **{crop.title()}**\nStatus: **🌻 Fully Grown!**\nType `{ctx.prefix}farm harvest` to harvest!"
        else:
            rem = grow_needed - elapsed
            m, s = divmod(int(rem), 60)
            water = "Watered 💧" if extras["farm_watered"] else "Dry 🏜️"
            embed.description = f"Plot: **{crop.title()}**\nStatus: **Growing ({water})**\nTime Remaining: `{m}m {s}s`"

        embed.set_footer(text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)

    @farm_group.command(name="harvest")
    async def farm_harvest(self, ctx: commands.Context) -> None:
        """harvest işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.harvest [parametreler]`"""
        extras = await self.get_extras(ctx.guild.id, ctx.author.id)
        if not extras["farm_crop"]:
            return await ctx.send("❌ No crops growing!")

        crop = extras["farm_crop"]
        elapsed = time.time() - extras["farm_time"]
        if elapsed < CROP_GROW_TIMES[crop]:
            rem = CROP_GROW_TIMES[crop] - elapsed
            m, s = divmod(int(rem), 60)
            return await ctx.send(f"❌ Crops not fully grown yet! Wait **{m}m {s}s**.")

        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        await self.set_inventory_item(ctx.guild.id, ctx.author.id, crop, inv.get(crop, 0) + 1)
        await self.db.execute(
            """UPDATE economy_extras
               SET farm_crop=NULL, farm_time=0.0, farm_watered=0
               WHERE user_id=? AND guild_id=?""",
            str(ctx.author.id), str(ctx.guild.id),
        )
        await ctx.send(f"🌻 Harvested **1x {crop.title()}**! Sell with `{ctx.prefix}sell {crop}`.")

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_int(value: str) -> int | None:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _weighted_choice(items: list[tuple]) -> tuple[str, str]:
        roll = random.random()
        cumulative = 0.0
        key, name = items[0][0], items[0][1]
        for k, n, chance in items:
            cumulative += chance
            if roll <= cumulative:
                return k, n
        return key, name

    @staticmethod
    def _scratch_roll() -> tuple[int, str]:
        roll = random.random()
        if roll < 0.30:
            return 0, "😢 Better luck next scratch card!"
        if roll < 0.70:
            p = random.randint(100, 500)
            return p, f"🎉 You scratched and won **{p:,} coins**!"
        if roll < 0.95:
            p = random.randint(800, 2000)
            return p, f"💎 Nice! Rare match! Won **{p:,} coins**!"
        return 5000, "👑 **JACKPOT!** You scratched 3 crowns and won **5,000 coins**!"


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economy(bot))
