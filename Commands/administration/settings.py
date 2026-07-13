from __future__ import annotations
import logging
import discord
from discord.ext import commands

from core.embed import EmbedBuilder

log = logging.getLogger(__name__)

class Settings(commands.Cog):
    category = "Yönetim ve Ayarlar"
    """Sunucu ayarları ve sistem yapılandırmaları."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def get_log_settings(self, guild_id: int):
        # Varsayılan değerlerle oluştur (Eğer yoksa)
        await self.bot.db.execute("INSERT OR IGNORE INTO log_settings (guild_id) VALUES (?)", str(guild_id))
        return await self.bot.db.fetchone("SELECT * FROM log_settings WHERE guild_id=?", str(guild_id))

    @commands.group(invoke_without_command=True)
    async def log(self, ctx: commands.Context) -> None:
        """log işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.ticket log <#channel>`"""
        row_db = await self.get_log_settings(ctx.guild.id)
        row = dict(row_db) if row_db else {}

        def ch(col: str) -> str:
            val = row.get(col)
            return f"<#{val}>" if val else "❌ Ayarlanmamış"

        def sw(col: str) -> str:
            return "🟢 Açık" if row.get(col, 0) else "🔴 Kapalı"

        embed = discord.Embed(
            title="📡 Discord Log Sistemi",
            description=(
                "Discord kanallarına embed log gönderme sistemi.\n"
                "Kanal seçmek için: `f.log set <tür> #kanal`\n"
                "Şalter açmak için: `f.log <tür> <olay> <on|off>`\n"
                "Web dashboard'dan da yönetilebilir."
            ),
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

        # ── Log Kanalları ──
        embed.add_field(
            name="📋 Log Kanalları",
            value=(
                f"📝 **Mesaj:** {ch('msg_channel')}\n"
                f"🎙️ **Ses:** {ch('ses_channel')}\n"
                f"🛡️ **Moderatör:** {ch('mod_channel')}\n"
                f"⚙️ **Sunucu:** {ch('sunucu_channel')}"
            ),
            inline=True
        )
        embed.add_field(
            name="​",  # boşluk
            value=(
                f"⚠️ **Uyarı:** {ch('uyari_channel')}\n"
                f"🎫 **Ticket:** {ch('ticket_channel')}\n"
                f"📋 **Başvuru:** {ch('basvuru_channel')}\n"
                f"💌 **Davet:** {ch('davet_channel')}\n"
                f"🎭 **Rol:** {ch('rol_channel')}"
            ),
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=False)

        # ── Şalterler ──
        embed.add_field(
            name="📝 Mesaj",
            value=f"Silinen: {sw('msg_delete_on')}\nDüzenlenen: {sw('msg_edit_on')}",
            inline=True
        )
        embed.add_field(
            name="🎙️ Ses",
            value=(
                f"Katıl/Çık: {sw('ses_join_on')}\n"
                f"Kanal Değiş: {sw('ses_switch_on')}\n"
                f"Kamera/Yayın: {sw('ses_stream_on')}"
            ),
            inline=True
        )
        embed.add_field(
            name="🛡️ Moderatör",
            value=(
                f"Rol İşl.: {sw('mod_role_on')}\n"
                f"Kanal İşl.: {sw('mod_channel_on')}\n"
                f"Msj Silme: {sw('mod_msg_on')}"
            ),
            inline=True
        )
        embed.add_field(
            name="⚙️ Sunucu",
            value=(
                f"Ayar: {sw('srv_update_on')}\n"
                f"Emoji: {sw('srv_emoji_on')}\n"
                f"Toplu Rol: {sw('srv_role_on')}\n"
                f"İzin: {sw('srv_perm_on')}"
            ),
            inline=True
        )
        embed.add_field(
            name="🔔 Diğer",
            value=(
                f"Uyarı Ekle: {sw('warn_add_on')}\n"
                f"Ticket Aç: {sw('ticket_create_on')}\n"
                f"Başvuru: {sw('app_create_on')}\n"
                f"Davet: {sw('invite_create_on')}\n"
                f"Rol Geçmişi: {sw('role_add_on')}"
            ),
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        embed.add_field(
            name="📖 Komut Referansı",
            value=(
                "```\n"
                "f.log set <tür> #kanal    → Kanal seç\n"
                "  türler: mesaj ses mod sunucu\n"
                "          uyari ticket basvuru davet rol\n\n"
                "f.log text   delete/edit   <on|off>\n"
                "f.log voice  join/switch/stream <on|off>\n"
                "f.log mod    role/channel/msg   <on|off>\n"
                "f.log server update/emoji/role/perm <on|off>\n"
                "f.log warn   add/remove    <on|off>\n"
                "f.log ticket create/close  <on|off>\n"
                "f.log app    create/accept/reject <on|off>\n"
                "f.log invite create/use    <on|off>\n"
                "f.log role   add/remove    <on|off>\n"
                "```"
            ),
            inline=False
        )
        embed.set_footer(text=f"💡 DB logları için: f.db | Sistem: Discord Embed Log")
        await ctx.send(embed=embed)


    @log.command(name="set")
    async def log_set(self, ctx: commands.Context, log_type: str, channel: discord.TextChannel) -> None:
        """Sistemdeki set ayarını yapılandırır. Kullanım: `f.set <parametre>`"""
        types = {
            "mesaj": "msg_channel", "ses": "ses_channel", "uyari": "uyari_channel",
            "ticket": "ticket_channel", "mod": "mod_channel", "basvuru": "basvuru_channel",
            "davet": "davet_channel", "sunucu": "sunucu_channel", "rol": "rol_channel"
        }
        log_type = log_type.lower()
        if log_type not in types:
            valid_types = ", ".join(types.keys())
            return await ctx.send(f"❌ Geçersiz log türü! Geçerli türler:\n`{valid_types}`")

        col = types[log_type]
        await self.bot.db.execute("INSERT OR IGNORE INTO log_settings (guild_id) VALUES (?)", str(ctx.guild.id))
        await self.bot.db.execute(f"UPDATE log_settings SET {col}=? WHERE guild_id=?", str(channel.id), str(ctx.guild.id))

        await ctx.send(f"✅ **{log_type.capitalize()} Log** kanalı başarıyla {channel.mention} olarak ayarlandı.")

    async def _toggle_log(self, ctx, column_name: str, state: str, log_name: str):
        state = state.lower()
        if state not in ["on", "off"]:
            return await ctx.send("❌ Geçersiz durum! Lütfen `on` veya `off` kullanın.")
        val = 1 if state == "on" else 0
        
        # Update log_settings (DC Embeds)
        await self.bot.db.execute("INSERT OR IGNORE INTO log_settings (guild_id) VALUES (?)", str(ctx.guild.id))
        await self.bot.db.execute(f"UPDATE log_settings SET {column_name}=? WHERE guild_id=?", val, str(ctx.guild.id))
        
        durum = "açıldı" if val == 1 else "kapatıldı"
        await ctx.send(f"✅ {log_name} kanal logları **{durum}**.")

    # TEXT
    @log.group(name="text", invoke_without_command=True)
    async def log_text(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.log text delete <on|off>` veya `f.log text edit <on|off>`")

    @log_text.command(name="delete")
    async def log_text_delete(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "msg_delete_on", state, "Silinen mesaj")

    @log_text.command(name="edit")
    async def log_text_edit(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "msg_edit_on", state, "Düzenlenen mesaj")

    # VOICE
    @log.group(name="voice", invoke_without_command=True)
    async def log_voice(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.log voice join/switch/stream <on|off>`")

    @log_voice.command(name="join")
    async def log_voice_join(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "ses_join_on", state, "Sese giriş/çıkış")

    @log_voice.command(name="switch")
    async def log_voice_switch(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "ses_switch_on", state, "Kanal değiştirme")

    @log_voice.command(name="stream")
    async def log_voice_stream(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "ses_stream_on", state, "Kamera/Yayın")

    # MOD
    @log.group(name="mod", invoke_without_command=True)
    async def log_mod(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.log mod role/channel/msg <on|off>`")

    @log_mod.command(name="role")
    async def log_mod_role(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "mod_role_on", state, "Yetkili rol verme/alma")

    @log_mod.command(name="channel")
    async def log_mod_channel(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "mod_channel_on", state, "Yetkili kanal oluşturma/silme")

    @log_mod.command(name="msg")
    async def log_mod_msg(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "mod_msg_on", state, "Yetkili başkasının mesajını silme")

    # SERVER
    @log.group(name="server", invoke_without_command=True)
    async def log_server(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.log server update/emoji/role/perm <on|off>`")

    @log_server.command(name="update")
    async def log_server_update(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "srv_update_on", state, "Sunucu ayar")

    @log_server.command(name="emoji")
    async def log_server_emoji(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "srv_emoji_on", state, "Emoji ekleme/çıkarma")

    @log_server.command(name="role")
    async def log_server_role(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "srv_role_on", state, "Sunucuda yeni rol oluşturma/silme")

    @log_server.command(name="perm")
    async def log_server_perm(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "srv_perm_on", state, "Kanal izinleri güncelleme")

    # WARN
    @log.group(name="warn", invoke_without_command=True)
    async def log_warn(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.log warn add/remove <on|off>`")

    @log_warn.command(name="add")
    async def log_warn_add(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "warn_add_on", state, "Uyarı ekleme")

    @log_warn.command(name="remove")
    async def log_warn_remove(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "warn_remove_on", state, "Uyarı silme")

    # TICKET
    @log.group(name="ticket", invoke_without_command=True)
    async def log_ticket(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.log ticket create/close <on|off>`")

    @log_ticket.command(name="create")
    async def log_ticket_create(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "ticket_create_on", state, "Ticket oluşturma")

    @log_ticket.command(name="close")
    async def log_ticket_close(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "ticket_close_on", state, "Ticket kapatma")

    # APP
    @log.group(name="app", invoke_without_command=True)
    async def log_app(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.log app create/accept/reject <on|off>`")

    @log_app.command(name="create")
    async def log_app_create(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "app_create_on", state, "Başvuru oluşturma")

    @log_app.command(name="accept")
    async def log_app_accept(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "app_accept_on", state, "Başvuru kabul")

    @log_app.command(name="reject")
    async def log_app_reject(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "app_reject_on", state, "Başvuru red")

    # INVITE
    @log.group(name="invite", invoke_without_command=True)
    async def log_invite(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.log invite create/use <on|off>`")

    @log_invite.command(name="create")
    async def log_invite_create(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "invite_create_on", state, "Davet oluşturma")

    @log_invite.command(name="use")
    async def log_invite_use(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "invite_use_on", state, "Davet kullanma")

    # ROLE
    @log.group(name="role", invoke_without_command=True)
    async def log_role(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.log role add/remove <on|off>`")

    @log_role.command(name="add")
    async def log_role_add(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "role_add_on", state, "Rol verilme")

    @log_role.command(name="remove")
    async def log_role_remove(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_log(ctx, "role_remove_on", state, "Rol alınma")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Settings(bot))
