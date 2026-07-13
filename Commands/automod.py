"""
Commands/automod.py
-------------------
Sunucu bazlı otomatik moderasyon: antilink, antispam, antiprofanity.

Veri depolama: Data/automod.json (sunucu ayarları JSON'da kalır —
 bu bir yapılandırma dosyasıdır, SQL'e taşınmaz.)
Spam geçmişi bellekte tutulur (self.spam_history), bot restart'ta sıfırlanır.
"""

from core.checks import kumiho_check, kumiho_app_check
import datetime
import logging
import re
import time
from pathlib import Path

import discord
from discord.ext import commands, tasks

from core.utils import json_load, json_save

log = logging.getLogger(__name__)

DB_FILE = Path("Data/automod.json")
_DEFAULT = lambda: {"antilink": {}, "antispam": {}, "antiprofanity": {}, "whitelist": {}}


def _load() -> dict:
    data = json_load(DB_FILE)
    for key in ("antilink", "antispam", "antiprofanity", "antizalgo", "whitelist"):
        data.setdefault(key, {})
    return data


class AutoMod(commands.Cog):
    category = "Moderasyon"
    category_emoji = "🛡️"
    """
    State-of-the-art server-scoped auto-moderation spam, link, and profanity filtering.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.spam_history: dict[str, dict[str, list[float]]] = {}
        self.invite_regex = re.compile(
            r"(discord\.gg|discord\.com/invite|discordapp\.com/invite)/[a-zA-Z0-9\-]+",
            re.IGNORECASE,
        )
        self.link_regex = re.compile(
            r"https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}", re.IGNORECASE
        )
        self.bad_words = [
            "fuck", "shit", "bitch", "bastard", "asshole", "cunt", "dick",
        ]

    async def cog_load(self):
        self.cleanup_spam_history.start()

    async def cog_unload(self):
        self.cleanup_spam_history.cancel()

    @tasks.loop(minutes=5)
    async def cleanup_spam_history(self):
        now = time.time()
        for g_id, users in list(self.spam_history.items()):
            for u_id, times in list(users.items()):
                self.spam_history[g_id][u_id] = [t for t in times if now - t <= 4.0]
                if not self.spam_history[g_id][u_id]:
                    del self.spam_history[g_id][u_id]
            if not self.spam_history[g_id]:
                del self.spam_history[g_id]

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.content == after.content:
            return
        await self.on_message(after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        # Staff is exempt
        if message.author.guild_permissions.manage_messages:
            return

        data = _load()
        g_id = str(message.guild.id)
        u_id = str(message.author.id)

        # ── 1. ANTISPAM ──────────────────────────────────────────────
        if data["antispam"].get(g_id, False):
            now = time.time()
            self.spam_history.setdefault(g_id, {}).setdefault(u_id, [])
            self.spam_history[g_id][u_id].append(now)
            self.spam_history[g_id][u_id] = [
                t for t in self.spam_history[g_id][u_id] if now - t <= 4.0
            ]
            if len(self.spam_history[g_id][u_id]) >= 5:
                try:
                    await message.delete()
                except Exception:
                    pass
                try:
                    await message.author.timeout(
                        datetime.timedelta(minutes=10), reason="AutoMod: Spam"
                    )
                    await message.channel.send(
                        f"❌ {message.author.mention} has been muted for 10 minutes due to spamming."
                    )
                except Exception:
                    await message.channel.send(
                        f"❌ {message.author.mention}, please stop spamming!"
                    )
                return

        # ── 2. ANTILINK ──────────────────────────────────────────────
        if data["antilink"].get(g_id, False):
            content = message.content
            has_link = self.link_regex.search(content) or self.invite_regex.search(content)
            if has_link:
                whitelisted = False
                if not self.invite_regex.search(content):
                    m = self.link_regex.search(content)
                    if m:
                        domain = (
                            m.group(0)
                            .replace("http://", "")
                            .replace("https://", "")
                            .split("/")[0]
                            .lower()
                        )
                        for wd in data["whitelist"].get(g_id, []):
                            if wd in domain:
                                whitelisted = True
                                break
                if not whitelisted:
                    try:
                        await message.delete()
                        await message.channel.send(
                            f"❌ {message.author.mention}, links/invites are not allowed!",
                            delete_after=5,
                        )
                    except Exception:
                        pass
                    return

        # ── 3. ANTIPROFANITY ─────────────────────────────────────────
        if data["antiprofanity"].get(g_id, False):
            content_lower = message.content.lower()
            clean_content = re.sub(r'[\W_]+', '', content_lower)
            triggered = any(w in clean_content for w in self.bad_words)
            if triggered:
                try:
                    await message.delete()
                    await message.channel.send(
                        f"❌ {message.author.mention}, profanity is strictly forbidden!",
                        delete_after=5,
                    )
                except Exception:
                    pass
                return

        # ── 4. ANTIZALGO ─────────────────────────────────────────────
        if data.get("antizalgo", {}).get(g_id, False):
            if re.search(r'[\u0300-\u036f]{4,}', message.content):
                try:
                    await message.delete()
                    await message.channel.send(
                        f"❌ {message.author.mention}, zalgo text is not allowed!",
                        delete_after=5,
                    )
                except Exception:
                    pass
                return

    # ── Admin commands ────────────────────────────────────────────────

    @commands.group(name="automod", invoke_without_command=True)
    @kumiho_check("owner")
    async def automod_group(self, ctx: commands.Context) -> None:
        """Manage auto-moderation settings.
        
        Use this command to configure the auto-moderator modules for your server.
        
        **Usage:** `{prefix}automod`
        **Required Permission:** Server Owner or Administrator
        """
        p = ctx.prefix
        await ctx.send(
            "🤖 **Auto-Moderation Settings**\n"
            f"• `{p}automod antilink <enable|disable>` — Link/invite filter\n"
            f"• `{p}automod antispam <enable|disable>` — Spam mute\n"
            f"• `{p}automod antiprofanity <enable|disable>` — Profanity filter\n"
            f"• `{p}automod antizalgo <enable|disable>` — Zalgo text filter\n"
            f"• `{p}automod whitelist <add|remove> <domain>` — Link whitelist"
        )

    async def _toggle(self, ctx: commands.Context, key: str, action: str) -> None:
        if action.lower() not in ("enable", "disable"):
            return await ctx.send(f"Usage: `{ctx.prefix}automod {key} <enable|disable>`")
        data = _load()
        state = action.lower() == "enable"
        data[key][str(ctx.guild.id)] = state
        json_save(DB_FILE, data)
        state_text = "enabled" if state else "disabled"
        await ctx.send(f"✅ AutoMod **{key}** has been **{state_text}**.")

    @automod_group.command(name="antilink")
    @kumiho_check("owner")
    async def automod_antilink(self, ctx: commands.Context, action: str = None) -> None:
        """Enable or disable the anti-link filter.
        
        Prevents users from sending URLs or Discord invites. You can whitelist specific domains using the whitelist command.
        
        **Usage:** `{prefix}automod antilink <enable|disable>`
        **Required Permission:** Server Owner or Administrator
        **Example:** `{prefix}automod antilink enable`
        """
        if not action:
            return await ctx.send(f"Usage: `{ctx.prefix}automod antilink <enable|disable>`")
        await self._toggle(ctx, "antilink", action)

    @automod_group.command(name="antispam")
    @kumiho_check("owner")
    async def automod_antispam(self, ctx: commands.Context, action: str = None) -> None:
        """Enable or disable the anti-spam filter.
        
        Automatically deletes rapid duplicate messages and handles spammers.
        
        **Usage:** `{prefix}automod antispam <enable|disable>`
        **Required Permission:** Server Owner or Administrator
        **Example:** `{prefix}automod antispam enable`
        """
        if not action:
            return await ctx.send(f"Usage: `{ctx.prefix}automod antispam <enable|disable>`")
        await self._toggle(ctx, "antispam", action)

    @automod_group.command(name="antiprofanity")
    @kumiho_check("owner")
    async def automod_antiprofanity(self, ctx: commands.Context, action: str = None) -> None:
        """Enable or disable the anti-profanity filter.
        
        Detects and deletes messages containing inappropriate language or bad words.
        
        **Usage:** `{prefix}automod antiprofanity <enable|disable>`
        **Required Permission:** Server Owner or Administrator
        **Example:** `{prefix}automod antiprofanity enable`
        """
        if not action:
            return await ctx.send(f"Usage: `{ctx.prefix}automod antiprofanity <enable|disable>`")
        await self._toggle(ctx, "antiprofanity", action)

    @automod_group.command(name="antizalgo")
    @kumiho_check("owner")
    async def automod_antizalgo(self, ctx: commands.Context, action: str = None) -> None:
        """Enable or disable the anti-zalgo filter.
        
        Prevents the use of excessive zalgo (glitchy/spooky) text formatting.
        
        **Usage:** `{prefix}automod antizalgo <enable|disable>`
        **Required Permission:** Server Owner or Administrator
        **Example:** `{prefix}automod antizalgo enable`
        """
        if not action:
            return await ctx.send(f"Usage: `{ctx.prefix}automod antizalgo <enable|disable>`")
        await self._toggle(ctx, "antizalgo", action)

    @automod_group.group(name="whitelist", invoke_without_command=True)
    @kumiho_check("owner")
    async def whitelist_group(self, ctx: commands.Context) -> None:
        """Configure the link whitelist.
        
        Manage the list of allowed domains that bypass the anti-link filter.
        
        **Usage:** `{prefix}automod whitelist <add|remove> <domain>`
        **Required Permission:** Server Owner or Administrator
        """
        await ctx.send(
            f"Usage: `{ctx.prefix}automod whitelist <add|remove> <domain>` (e.g. google.com)"
        )

    @whitelist_group.command(name="add")
    @kumiho_check("owner")
    async def whitelist_add(self, ctx: commands.Context, domain: str = None) -> None:
        """Add a domain to the anti-link whitelist.
        
        Links containing this domain will not be deleted by the anti-link filter.
        
        **Usage:** `{prefix}automod whitelist add <domain>`
        **Required Permission:** Server Owner or Administrator
        **Example:** `{prefix}automod whitelist add google.com`
        """
        if not domain:
            return await ctx.send(f"Usage: `{ctx.prefix}automod whitelist add <domain>`")
        data = _load()
        g_id = str(ctx.guild.id)
        domain = domain.lower().strip()
        data["whitelist"].setdefault(g_id, [])
        if domain not in data["whitelist"][g_id]:
            data["whitelist"][g_id].append(domain)
            json_save(DB_FILE, data)
            await ctx.send(f"✅ Whitelisted domain `{domain}`.")
        else:
            await ctx.send(f"❌ `{domain}` is already whitelisted.")

    @whitelist_group.command(name="remove")
    @kumiho_check("owner")
    async def whitelist_remove(self, ctx: commands.Context, domain: str = None) -> None:
        """Remove a domain from the anti-link whitelist.
        
        Removes a previously allowed domain so that the anti-link filter will block it again.
        
        **Usage:** `{prefix}automod whitelist remove <domain>`
        **Required Permission:** Server Owner or Administrator
        **Example:** `{prefix}automod whitelist remove google.com`
        """
        if not domain:
            return await ctx.send(f"Usage: `{ctx.prefix}automod whitelist remove <domain>`")
        data = _load()
        g_id = str(ctx.guild.id)
        domain = domain.lower().strip()
        if g_id in data["whitelist"] and domain in data["whitelist"][g_id]:
            data["whitelist"][g_id].remove(domain)
            json_save(DB_FILE, data)
            await ctx.send(f"✅ Removed `{domain}` from the whitelist.")
        else:
            await ctx.send(f"❌ `{domain}` is not in the whitelist.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))
