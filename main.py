"""
main.py
-------
Azalea Discord Bot — Ana giriş noktası

Başlatma sırası:
  1. Logging sistemi kur  (core.logger)
  2. Veritabanlarını başlat (core.database)
  3. Cog'ları yükle
  4. Bot'u başlat

Anti-crash:
  asyncio event loop exception handler, sys.excepthook ve threading.excepthook
  ile üç katmanlı çökme koruması sağlanmıştır.
"""

import asyncio
import logging
import os
import sys
import threading

import discord
from discord.ext import commands
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Ortam değişkenleri
# ---------------------------------------------------------------------------
load_dotenv()

TOKEN = os.getenv("TOKEN") or os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN env variable is not set! Please configure it in .env")
STATUS = os.getenv("STATUS", "f.help")
MY_TWITCH = os.getenv("MY_TWITCH_ACCOUNT", "")
OWNER_IDS_RAW = os.getenv("OWNER_ID", "")

# ---------------------------------------------------------------------------
# Core altyapı
# ---------------------------------------------------------------------------
from core.logger import setup_logging
from core.database import Database

setup_logging()
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Discord intents
# ---------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.presences = True
intents.voice_states = True
intents.invites = True

# ---------------------------------------------------------------------------
# Help sistemi — Interactive dropdown menü
# ---------------------------------------------------------------------------

class HelpPagesView(discord.ui.View):
    def __init__(self, help_command, mapping, emoji_mapping):
        super().__init__(timeout=120)
        self.help_command = help_command
        self.mapping = mapping
        self.message = None
        self.current_embeds = []
        self.index = 0
        self.emoji_mapping = emoji_mapping

        self.prev_btn = discord.ui.Button(
            label="⬅️ Prev", style=discord.ButtonStyle.gray, disabled=True
        )
        self.page_btn = discord.ui.Button(
            label="Page 1/1", style=discord.ButtonStyle.gray, disabled=True
        )
        self.next_btn = discord.ui.Button(
            label="➡️ Next", style=discord.ButtonStyle.gray, disabled=True
        )

        self.prev_btn.callback = self.prev_page
        self.next_btn.callback = self.next_page

        self.build_dropdown()

    def build_dropdown(self):
        options = []
        for cog, command_list in self.mapping.items():
            if not command_list:
                continue

            cog_name = cog.qualified_name if cog else "General"
            cog_desc = (
                cog.description[:100]
                if cog and cog.description
                else "Commands without a specific category."
            )

            emoji = self.emoji_mapping.get(cog_name, None)

            options.append(
                discord.SelectOption(
                    label=cog_name,
                    description=cog_desc,
                    value=cog_name,
                    emoji=emoji,
                )
            )

        self.clear_items()

        select_menu = discord.ui.Select(
            placeholder="Select a category to view commands...",
            min_values=1,
            max_values=1,
            options=options,
        )
        select_menu.callback = self.help_select_callback
        self.add_item(select_menu)

        self.add_item(self.prev_btn)
        self.add_item(self.page_btn)
        self.add_item(self.next_btn)

    def update_buttons(self):
        total_pages = len(self.current_embeds)

        if total_pages <= 1:
            self.prev_btn.disabled = True
            self.next_btn.disabled = True
            self.page_btn.label = f"Page 1/{max(total_pages, 1)}"
        else:
            self.prev_btn.disabled = self.index == 0
            self.next_btn.disabled = self.index == total_pages - 1
            self.page_btn.label = f"Page {self.index + 1}/{total_pages}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.help_command.context.author.id:
            await interaction.response.send_message(
                f"Only {self.help_command.context.author.mention} can interact with this help menu.",
                ephemeral=True,
            )
            return False
        return True

    async def help_select_callback(self, interaction: discord.Interaction):
        # Discord'a hemen "geldim" deği gönder — 3 sn timeout'u engeller
        await interaction.response.defer()

        selected_cog_name = interaction.data["values"][0]
        selected_cog = None
        selected_commands = []

        for cog, command_list in self.mapping.items():
            name = cog.qualified_name if cog else "General"
            if name == selected_cog_name:
                selected_cog = cog
                try:
                    selected_commands = await self.help_command.filter_commands(
                        command_list, sort=True
                    )
                except Exception:
                    selected_commands = list(command_list)
                break

        embed_desc = (
            selected_cog.description
            if selected_cog and selected_cog.description
            else "General utility commands."
        )

        self.current_embeds = []
        self.index = 0

        if not selected_commands:
            emoji = self.emoji_mapping.get(selected_cog_name, None)
            embed = discord.Embed(
                title=f"{emoji} {selected_cog_name} {emoji}",
                description=f"**{embed_desc}**\n\n*No accessible commands found.*",
                color=discord.Color.blue(),
            )
            embed.set_footer(text="Use f.help [command] for precise argument rules.")
            self.current_embeds.append(embed)
        else:
            chunks = [
                selected_commands[i : i + 5]
                for i in range(0, len(selected_commands), 5)
            ]

            for idx, chunk in enumerate(chunks):
                emoji = self.emoji_mapping.get(selected_cog_name, None)
                embed = discord.Embed(
                    title=f"{emoji} {selected_cog_name} {emoji}",
                    description=f"**{embed_desc}**\n\n**Command List:**",
                    color=discord.Color.blue(),
                )
                embed.set_footer(text="Use f.help [command] for precise argument rules.")

                for command in chunk:
                    signature = self.help_command.get_command_signature(command)
                    embed.add_field(
                        name=f"`{signature}`",
                        value=command.short_doc or "No summary description provided.",
                        inline=False,
                    )

                self.current_embeds.append(embed)

        self.update_buttons()
        # defer() sonrası edit_message yerine followup.edit_message kullanılır
        await interaction.edit_original_response(
            embed=self.current_embeds[self.index], view=self
        )

    async def prev_page(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.index > 0:
            self.index -= 1
        self.update_buttons()
        try:
            await interaction.edit_original_response(
                embed=self.current_embeds[self.index], view=self
            )
        except discord.HTTPException:
            pass

    async def next_page(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.index < len(self.current_embeds) - 1:
            self.index += 1
        self.update_buttons()
        try:
            await interaction.edit_original_response(
                embed=self.current_embeds[self.index], view=self
            )
        except discord.HTTPException:
            pass

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.HTTPException:
                pass


class MyHelp(commands.DefaultHelpCommand):
    """Interactive dropdown help menüsü."""

    def __init__(self):
        super().__init__(
            command_attrs={
                "help": "Shows the main command interface or detailed info on a single command.",
                "aliases": ["h"],
            }
        )
        self.emoji_mapping = {
            "Help": "❓",
            "Moderation": "🛡️",
            "Fun": "🎉",
            "General": "📜",
            "Utils": "🛠️",
            "Economy": "🪙",
            "Owner": "👑",
            "Nsfw": "🔞",
            "Leveling": "📈",
            "Giveaways": "🎁",
            "Tickets": "🎫",
            "Suggestions": "💡",
            "Automod": "🤖",
            "Permissions": "🔐",
            "Settings": "⚙️",
        }

    async def command_callback(self, ctx, *, command=None):
        if command:
            parts = command.split()

            cog_match = False
            for cog_name in ctx.bot.cogs:
                if cog_name.lower() == parts[0].lower():
                    command = cog_name
                    cog_match = True
                    break

            if not cog_match:
                current_obj = ctx.bot
                resolved_path = []

                for part in parts:
                    if hasattr(current_obj, "get_command"):
                        target_cmd = current_obj.get_command(part)
                        if target_cmd:
                            current_obj = target_cmd
                            resolved_path.append(target_cmd.name)
                        else:
                            break
                    else:
                        break

                if resolved_path:
                    command = " ".join(resolved_path)

        return await super().command_callback(ctx, command=command)

    async def send_bot_help(self, mapping):
        valid_mapping = {}

        is_admin_or_owner = False
        ctx = self.context
        if ctx.guild:
            is_admin_or_owner = (
                ctx.author.guild_permissions.administrator
                or ctx.author.id == ctx.guild.owner_id
            )

        is_bot_owner = await ctx.bot.is_owner(ctx.author)
        owners_env = OWNER_IDS_RAW.split(",")
        if str(ctx.author.id) in [o.strip() for o in owners_env if o.strip()]:
            is_bot_owner = True

        has_owner_access = is_admin_or_owner or is_bot_owner

        for cog, cmd_list in mapping.items():
            filtered = await self.filter_commands(cmd_list)
            if filtered:
                cog_name = cog.qualified_name if cog else "General"
                if cog_name == "Owner" and not has_owner_access:
                    continue
                valid_mapping[cog] = cmd_list

        emoji = self.emoji_mapping.get("Help", None)
        embed_landing = discord.Embed(
            title=f"{emoji} Interactive Help Center {emoji}",
            description=(
                "Welcome! Use the selection box menu below to seamlessly flip through "
                "available toolsets and modules.\n\n"
                "**Quick Navigation:**\n"
                f"Skip this menu entirely at any time using explicitly: `{self.context.clean_prefix}help [command]`"
            ),
            color=discord.Color.blurple(),
        )

        view = HelpPagesView(self, valid_mapping, self.emoji_mapping)
        destination = self.get_destination()
        view.message = await destination.send(embed=embed_landing, view=view)

    async def send_cog_help(self, cog):
        if cog.qualified_name == "Owner":
            is_admin_or_owner = False
            ctx = self.context
            if ctx.guild:
                is_admin_or_owner = (
                    ctx.author.guild_permissions.administrator
                    or ctx.author.id == ctx.guild.owner_id
                )

            is_bot_owner = await ctx.bot.is_owner(ctx.author)
            owners_env = OWNER_IDS_RAW.split(",")
            if str(ctx.author.id) in [o.strip() for o in owners_env if o.strip()]:
                is_bot_owner = True

            has_owner_access = is_admin_or_owner or is_bot_owner
            if not has_owner_access:
                return await self.get_destination().send(
                    "❌ Only authorized administrators/owners can view this category."
                )

        filtered = await self.filter_commands(cog.get_commands(), sort=True)

        emoji = self.emoji_mapping.get(cog.qualified_name, None)
        embed = discord.Embed(
            title=f"{emoji} {cog.qualified_name} {emoji}",
            description=f"**{cog.description}**" or "*No category description specified.*",
            color=discord.Color.blue(),
        )

        for command in filtered:
            embed.add_field(
                name=f"`{self.get_command_signature(command)}`",
                value=command.short_doc or "No description.",
                inline=False,
            )

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        filtered = await self.filter_commands(group.commands, sort=True)
        description = group.help or "No comprehensive description provided."

        emoji = self.emoji_mapping.get(group.cog_name, None)
        embed = discord.Embed(
            title=f"{emoji} {group.name.upper()} {emoji}",
            description=description,
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="Base Group Signature",
            value=f"```json\n{self.get_command_signature(group)}```",
            inline=False,
        )

        if filtered:
            subcommand_list = ""
            for sub_cmd in filtered:
                subcommand_list += f"`{group.name} {sub_cmd.name}` - {sub_cmd.short_doc or 'No description.'}\n"

            embed.add_field(
                name="Available Subcommands",
                value=subcommand_list,
                inline=False,
            )

        if group.aliases:
            embed.add_field(
                name="Shortcut Aliases",
                value=" ".join(f"`{a}`" for a in group.aliases),
                inline=False,
            )

        embed.set_footer(
            text="Type f.help <command> [subcommand] for detailed parameter instructions."
        )
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        description = command.help or "No comprehensive description provided."

        emoji = self.emoji_mapping.get(command.cog_name, None)
        embed = discord.Embed(
            title=f"{emoji} {command.name} {emoji}",
            description=description,
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Syntax Format",
            value=f"```\n{self.get_command_signature(command)}```",
            inline=False,
        )
        embed.set_footer(
            text="Parameters Notation: <required_argument> | [optional_argument]"
        )

        if command.aliases:
            embed.add_field(
                name="Shortcut Aliases",
                value=" ".join(f"`{a}`" for a in command.aliases),
                inline=False,
            )

        await self.get_destination().send(embed=embed)


# ---------------------------------------------------------------------------
# Bot instance
# ---------------------------------------------------------------------------
bot = commands.Bot(
    command_prefix="f.",
    intents=intents,
    help_command=MyHelp(),
)


# ---------------------------------------------------------------------------
# Cog yükleyici
# ---------------------------------------------------------------------------
async def load_cogs() -> None:
    """
    Commands/ ve Events/ altındaki tüm .py dosyalarını cog olarak yükler.
    Administration alt paketini de ayrıca yükler.
    """
    # Commands/ — düz .py dosyaları
    # Not: legacy Commands/moderation.py artık administration/moderation.py ile değiştirildi
    _SKIP = {"moderation"}  # eski modular cog'lar — administration/ altındaki ile çakışır
    for filename in os.listdir("./Commands"):
        if filename.endswith(".py") and not filename.startswith("_"):
            module = filename[:-3]
            if module in _SKIP:
                log.debug("Cog atlandı (legacy): Commands.%s", module)
                continue
            try:
                await bot.load_extension(f"Commands.{module}")
                log.debug("Cog yüklendi: Commands.%s", module)
            except Exception as e:
                log.error("Cog yüklenemedi: Commands.%s — %s", module, e)

    # Commands/administration/ — alt paket
    admin_dir = "./Commands/administration"
    if os.path.isdir(admin_dir):
        for filename in os.listdir(admin_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                module = filename[:-3]
                try:
                    await bot.load_extension(f"Commands.administration.{module}")
                    log.debug("Cog yüklendi: Commands.administration.%s", module)
                except Exception as e:
                    log.error(
                        "Cog yüklenemedi: Commands.administration.%s — %s", module, e
                    )

    # Events/
    for filename in os.listdir("./Events"):
        if filename.endswith(".py") and not filename.startswith("_"):
            try:
                await bot.load_extension(f"Events.{filename[:-3]}")
                log.debug("Cog yüklendi: Events.%s", filename[:-3])
            except Exception as e:
                log.error("Cog yüklenemedi: Events.%s — %s", filename[:-3], e)


# ---------------------------------------------------------------------------
# Bot olayları
# ---------------------------------------------------------------------------
@bot.event
async def on_ready():
    local_status = f"{STATUS} | in {len(bot.guilds)} servers"

    log.info("=" * 40)
    log.info("Bot hazır: %s", bot.user.name)
    log.info("Sunucu sayısı: %d", len(bot.guilds))
    log.info("=" * 40)

    # Önbellek Senkronizasyonu (ID'leri isimlerle eşleştirmek için)
    log.info("Önbellek senkronizasyonu başlatılıyor...")
    for guild in bot.guilds:
        for role in guild.roles:
            await bot.db.update_role_cache(str(guild.id), str(role.id), role.name)
        for channel in guild.channels:
            await bot.db.update_channel_cache(str(channel.id), channel.name)
        for member in guild.members:
            avatar = member.display_avatar.url if member.display_avatar else None
            await bot.db.update_user_cache(str(member.id), member.name, avatar)
    log.info("Önbellek senkronizasyonu tamamlandı.")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.streaming,
            name=local_status,
            url=MY_TWITCH or "https://twitch.tv/placeholder",
            state="LUMINAlabs",
        )
    )
    log.info("Presence ayarlandı: %s", local_status)

    # Owner'a başlangıç DM'i gönder
    for owner_id_str in OWNER_IDS_RAW.split(","):
        owner_id_str = owner_id_str.strip()
        if not owner_id_str:
            continue
        try:
            owner_user = await bot.fetch_user(int(owner_id_str))
            await owner_user.send("✅ Bot başlatıldı — uyandım!")
            log.info("Owner DM gönderildi: %s", owner_id_str)
        except Exception as e:
            log.warning("Owner DM gönderilemedi (%s): %s", owner_id_str, e)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Komut bulunamadı!")
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Eksik argüman: `{error.param.name}`")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Geçersiz argüman. Kullanım için `f.help <komut>` yaz.")
        return
    if isinstance(error, commands.CheckFailure):
        log.warning("Komut yetki hatası [%s]: %s", ctx.command, error)
        try:
            from Commands.administration.permission_check import send_denied
            await send_denied(ctx, str(error))
        except Exception as e:
            log.error("send_denied cagrilamadi: %s", e)
        return

    log.error("Komut hatası [%s]: %s", ctx.command, error, exc_info=error)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Bot ban kontrolü — SQL
    if bot.db and bot.db.user_db:
        try:
            row = await bot.db.fetchone(
                "SELECT 1 FROM bot_bans WHERE user_id=?",
                str(message.author.id),
            )
            if row:
                return  # Banlı kullanıcıyı tamamen yoksay
        except Exception:
            pass

    await bot.process_commands(message)


# ---------------------------------------------------------------------------
# Anti-crash hook'ları (üç katmanlı)
# ---------------------------------------------------------------------------
def handle_crash(loop, context):
    """asyncio event loop exception handler."""
    exception = context.get("exception")
    message = context.get("message", "Unhandled asyncio loop exception")
    log.critical("ANTICRASH (ASYNCIO): %s", message, exc_info=exception)


def handle_sys_crash(exctype, value, tb):
    """sys.excepthook — yakalanmamış sistem istisnası."""
    log.critical("ANTICRASH (SYSTEM)", exc_info=(exctype, value, tb))


def handle_thread_crash(args):
    """threading.excepthook — thread istisnası."""
    log.critical(
        "ANTICRASH (THREAD)",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


sys.excepthook = handle_sys_crash
threading.excepthook = handle_thread_crash


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------
async def main():
    
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(handle_crash)

    # Veritabanını başlat ve bot'a bağla
    bot.db = Database()
    await bot.db.init()

    async with bot:
        try:
            await load_cogs()
            await bot.start(TOKEN)
        finally:
            if hasattr(bot, "db") and bot.db:
                await bot.db.close()


if __name__ == "__main__":
    asyncio.run(main())

