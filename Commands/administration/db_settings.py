import logging
import discord
from discord.ext import commands


log = logging.getLogger(__name__)

class DBSettings(commands.Cog):
    """Veritabanı (DB) Log kayıt sistemi ayarları."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def db(self, ctx: commands.Context) -> None:
        """Veritabanı log sistemi paneli. Web dashboard için kayıt şalterlerinin durumunu gösterir."""
        await self.bot.db.execute("INSERT OR IGNORE INTO db_log_settings (guild_id) VALUES (?)", str(ctx.guild.id))
        row = await self.bot.db.fetchone("SELECT * FROM db_log_settings WHERE guild_id=?", str(ctx.guild.id))
        row = dict(row) if row else {}

        def sw(col: str) -> str:
            return "🟢 Açık" if row.get(col, 0) else "🔴 Kapalı"

        embed = discord.Embed(
            title="🗄️ Veritabanı Log Sistemi",
            description=(
                "Web dashboard için olayları SQLite'a kaydeden şalterler.\n"
                "Bu sistem **Discord kanalı log sisteminden bağımsızdır**.\n"
                "Şalter açmak için: `f.db <tür> <olay> <on|off>`\n"
                "Kayıtları görmek için: `f.dblog <tür>`"
            ),
            color=discord.Color.og_blurple(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

        # ── Şalter durumları ──
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
                f"Yayın: {sw('ses_stream_on')}\n"
                f"Kamera: {sw('ses_camera_on')}"
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
            name="⚠️ Uyarı & Ticket",
            value=(
                f"Uyarı Ekle: {sw('warn_add_on')}\n"
                f"Uyarı Sil: {sw('warn_remove_on')}\n"
                f"Ticket Aç: {sw('ticket_create_on')}\n"
                f"Ticket Kapat: {sw('ticket_close_on')}"
            ),
            inline=True
        )
        embed.add_field(
            name="📋 Başvuru & Davet & Rol",
            value=(
                f"Başvuru: {sw('app_create_on')}\n"
                f"Onay/Red: {sw('app_accept_on')} / {sw('app_reject_on')}\n"
                f"Davet Oluştur: {sw('invite_create_on')}\n"
                f"Davet Kullan: {sw('invite_use_on')}\n"
                f"Rol Ekle/Çıkar: {sw('role_add_on')} / {sw('role_remove_on')}"
            ),
            inline=True
        )
        embed.add_field(
            name="📖 Komut Referansı",
            value=(
                "```\n"
                "f.db text   delete/edit          <on|off>\n"
                "f.db voice  join/switch/stream   <on|off>\n"
                "f.db mod    role/channel/msg     <on|off>\n"
                "f.db server update/emoji/role/perm <on|off>\n"
                "f.db warn   add/remove           <on|off>\n"
                "f.db ticket create/close         <on|off>\n"
                "f.db app    create/accept/reject <on|off>\n"
                "f.db invite create/use           <on|off>\n"
                "f.db role   add/remove           <on|off>\n\n"
                "f.dblog <tür> [@kullanıcı] [limit]\n"
                "  → Kayıtlı logları Discord'da göster\n"
                "```"
            ),
            inline=False
        )
        embed.set_footer(text="💡 Discord embed logları için: f.log | Sistem: DB Arşiv Log")
        await ctx.send(embed=embed)


    async def _toggle_db_log(self, ctx, column_name: str, state: str, log_name: str):
        state = state.lower()
        if state not in ["on", "off"]:
            return await ctx.send("❌ Geçersiz durum! Lütfen `on` veya `off` kullanın.")
        val = 1 if state == "on" else 0
        
        await self.bot.db.execute("INSERT OR IGNORE INTO db_log_settings (guild_id) VALUES (?)", str(ctx.guild.id))
        await self.bot.db.execute(f"UPDATE db_log_settings SET {column_name}=? WHERE guild_id=?", val, str(ctx.guild.id))
        
        durum = "açıldı" if val == 1 else "kapatıldı"
        await ctx.send(f"✅ {log_name} DB logları **{durum}**.")

    # TEXT
    @db.group(name="text", invoke_without_command=True)
    async def db_text(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.db text delete <on|off>` veya `f.db text edit <on|off>`")

    @db_text.command(name="delete")
    async def db_text_delete(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "msg_delete_on", state, "Silinen mesaj")

    @db_text.command(name="edit")
    async def db_text_edit(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "msg_edit_on", state, "Düzenlenen mesaj")

    # VOICE
    @db.group(name="voice", invoke_without_command=True)
    async def db_voice(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.db voice join/switch/stream <on|off>`")

    @db_voice.command(name="join")
    async def db_voice_join(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "ses_join_on", state, "Sese giriş/çıkış")

    @db_voice.command(name="switch")
    async def db_voice_switch(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "ses_switch_on", state, "Kanal değiştirme")

    @db_voice.command(name="stream")
    async def db_voice_stream(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "ses_stream_on", state, "Kamera/Yayın")

    # MOD
    @db.group(name="mod", invoke_without_command=True)
    async def db_mod(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.db mod role/channel/msg <on|off>`")

    @db_mod.command(name="role")
    async def db_mod_role(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "mod_role_on", state, "Yetkili rol verme/alma")

    @db_mod.command(name="channel")
    async def db_mod_channel(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "mod_channel_on", state, "Yetkili kanal oluşturma/silme")

    @db_mod.command(name="msg")
    async def db_mod_msg(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "mod_msg_on", state, "Yetkili başkasının mesajını silme")

    # SERVER
    @db.group(name="server", invoke_without_command=True)
    async def db_server(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.db server update/emoji/role/perm <on|off>`")

    @db_server.command(name="update")
    async def db_server_update(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "srv_update_on", state, "Sunucu ayar")

    @db_server.command(name="emoji")
    async def db_server_emoji(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "srv_emoji_on", state, "Emoji ekleme/çıkarma")

    @db_server.command(name="role")
    async def db_server_role(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "srv_role_on", state, "Sunucuda yeni rol oluşturma/silme")

    @db_server.command(name="perm")
    async def db_server_perm(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "srv_perm_on", state, "Kanal izinleri güncelleme")

    # WARN
    @db.group(name="warn", invoke_without_command=True)
    async def db_warn(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.db warn add/remove <on|off>`")

    @db_warn.command(name="add")
    async def db_warn_add(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "warn_add_on", state, "Uyarı ekleme")

    @db_warn.command(name="remove")
    async def db_warn_remove(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "warn_remove_on", state, "Uyarı silme")

    # TICKET
    @db.group(name="ticket", invoke_without_command=True)
    async def db_ticket(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.db ticket create/close <on|off>`")

    @db_ticket.command(name="create")
    async def db_ticket_create(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "ticket_create_on", state, "Ticket oluşturma")

    @db_ticket.command(name="close")
    async def db_ticket_close(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "ticket_close_on", state, "Ticket kapatma")

    # APP
    @db.group(name="app", invoke_without_command=True)
    async def db_app(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.db app create/accept/reject <on|off>`")

    @db_app.command(name="create")
    async def db_app_create(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "app_create_on", state, "Başvuru oluşturma")

    @db_app.command(name="accept")
    async def db_app_accept(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "app_accept_on", state, "Başvuru kabul")

    @db_app.command(name="reject")
    async def db_app_reject(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "app_reject_on", state, "Başvuru red")

    # INVITE
    @db.group(name="invite", invoke_without_command=True)
    async def db_invite(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.db invite create/use <on|off>`")

    @db_invite.command(name="create")
    async def db_invite_create(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "invite_create_on", state, "Davet oluşturma")

    @db_invite.command(name="use")
    async def db_invite_use(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "invite_use_on", state, "Davet kullanma")

    # ROLE
    @db.group(name="role", invoke_without_command=True)
    async def db_role(self, ctx: commands.Context) -> None:
        await ctx.send("Kullanım: `f.db role add/remove <on|off>`")

    @db_role.command(name="add")
    async def db_role_add(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "role_add_on", state, "Rol verilme")

    @db_role.command(name="remove")
    async def db_role_remove(self, ctx: commands.Context, state: str) -> None:
        await self._toggle_db_log(ctx, "role_remove_on", state, "Rol alınma")

    # DBLOG Command
    @commands.command(name="dblog")
    async def dblog(self, ctx: commands.Context, event_type: str = None, user: discord.Member = None, limit: int = 10):
        """
        Veritabanına kaydedilen logları listeler.
        Kullanım: f.dblog <event_type> [@kullanici] [limit]
        """
        if not event_type:
            types = [
                "msg_delete", "msg_edit", 
                "ses_join", "ses_switch", "ses_stream", 
                "mod_role", "mod_channel", "mod_msg", 
                "srv_update", "srv_emoji", "srv_role", "srv_perm",
                "warn_add", "warn_remove", "ticket_create", "ticket_close",
                "app_create", "app_accept", "app_reject",
                "invite_create", "invite_use", "role_add", "role_remove"
            ]
            return await ctx.send(f"ℹ️ **Lütfen bir log türü belirtin.** \n**Geçerli türler:** `{', '.join(types)}`\n\nKullanım: `f.dblog <tür> [@kullanici] [sayi]`")
        
        if user:
            query = "SELECT log_id, user_id, details, timestamp FROM db_event_logs WHERE guild_id = ? AND event_type = ? AND user_id = ? ORDER BY timestamp DESC LIMIT ?"
            params = [str(ctx.guild.id), event_type, str(user.id), limit]
        else:
            query = "SELECT log_id, user_id, details, timestamp FROM db_event_logs WHERE guild_id = ? AND event_type = ? ORDER BY timestamp DESC LIMIT ?"
            params = [str(ctx.guild.id), event_type, limit]
            
        rows = await self.bot.db.fetchall(query, *params)
        
        if not rows:
            return await ctx.send("❌ Bu kritere uygun log bulunamadı.")
            
        embed = discord.Embed(
            title=f"🗄️ DB Log Kayıtları: {event_type}",
            color=discord.Color.orange()
        )
        for row in rows:
            log_id, u_id, details, ts = row
            usr = f"<@{u_id}>" if u_id else "Bilinmiyor"
            
            # Kısaltılmış metin
            if len(details) > 800:
                details = details[:800] + "..."
                
            embed.add_field(name=f"Log ID: {log_id} | {ts}", value=f"Kullanıcı: {usr}\nDetay: {details}", inline=False)
            
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DBSettings(bot))
