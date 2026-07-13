from __future__ import annotations
"""
Commands/tickets.py
--------------------
Sunucu bazlı, veritabanı entegreli ve modal tabanlı modern destek bileti (ticket) sistemi.
"""

from core.checks import kumiho_check, kumiho_app_check
import asyncio
import io
import logging
import os
import datetime
import base64

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

async def generate_html_transcript(channel, bot):
    # A simple but clean HTML template
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Transcript: {channel.name}</title>
        <style>
            body {{ background-color: #36393f; color: #dcddde; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; }}
            .message {{ display: flex; margin-bottom: 20px; }}
            .avatar {{ width: 40px; height: 40px; border-radius: 50%; margin-right: 15px; object-fit: cover; }}
            .content {{ display: flex; flex-direction: column; }}
            .header {{ display: flex; align-items: baseline; }}
            .username {{ font-weight: 600; color: #fff; margin-right: 10px; font-size: 1.1em; }}
            .timestamp {{ font-size: 0.8em; color: #72767d; }}
            .text {{ margin-top: 5px; line-height: 1.4; word-wrap: break-word; }}
            .attachment {{ margin-top: 5px; max-width: 400px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h2>Ticket Transcript: {channel.name}</h2>
        <hr style="border: 1px solid #42464D; margin-bottom: 20px;">
    """
    
    try:
        async for m in channel.history(limit=1000, oldest_first=True):
            msg_time = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = m.clean_content.replace('\n', '<br>')
            avatar_url = m.author.display_avatar.url if m.author.display_avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
            
            attachments_html = ""
            for a in m.attachments:
                if a.content_type and a.content_type.startswith("image/"):
                    try:
                        img_bytes = await a.read()
                        b64 = base64.b64encode(img_bytes).decode('utf-8')
                        attachments_html += f'<br><img src="data:{a.content_type};base64,{b64}" class="attachment">'
                    except Exception:
                        attachments_html += f'<br><a href="{a.url}" style="color: #00aff4;">[Resim İndirilemedi]</a>'
                else:
                    attachments_html += f'<br><a href="{a.url}" style="color: #00aff4;">[Attachment: {a.filename}]</a>'
            
            html += f"""
            <div class="message">
                <img src="{avatar_url}" class="avatar">
                <div class="content">
                    <div class="header">
                        <span class="username">{m.author.display_name}</span>
                        <span class="timestamp">{msg_time}</span>
                    </div>
                    <div class="text">{content}{attachments_html}</div>
                </div>
            </div>
            """
    except Exception:
        pass

    html += "</body></html>"
    return html


class TicketReasonModal(discord.ui.Modal, title='Destek Talebi Aç'):
    reason = discord.ui.TextInput(
        label='Lütfen iletişime geçme sebebinizi belirtin',
        style=discord.TextStyle.paragraph,
        placeholder='Örn: Üyeliğim hakkında bir sorun yaşıyorum...',
        required=True,
        max_length=1000
    )

    def __init__(self, cog, guild, category, support_roles, support_users, admin_roles, ticket_counter):
        super().__init__()
        self.cog = cog
        self.guild = guild
        self.category = category
        self.support_roles = support_roles
        self.support_users = support_users
        self.admin_roles = admin_roles
        self.ticket_counter = ticket_counter

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        g_id = str(self.guild.id)
        
        # Check active tickets
        active = await self.cog.bot.db.fetchall("SELECT ticket_id FROM active_tickets WHERE guild_id=? AND owner_id=? AND status='open'", g_id, str(user.id))
        if len(active) >= 3:
            return await interaction.response.send_message("❌ Aynı anda en fazla 3 aktif bilet açabilirsiniz.", ephemeral=True)
            
        ticket_num = self.ticket_counter + 1
        ticket_id = f"{ticket_num:03d}-{user.name}"
        
        # Update counter
        await self.cog.bot.db.execute("UPDATE ticket_settings SET ticket_counter=? WHERE guild_id=?", ticket_num, g_id)
        
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            self.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }

        for role in self.support_roles:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            
        for member in self.support_users:
            overwrites[member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            
        for role in self.admin_roles:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            ticket_channel = await self.guild.create_text_channel(
                name=ticket_id,
                category=self.category,
                overwrites=overwrites,
                topic=str(user.id), # keeping user ID in topic as fallback
                reason=f"Ticket opened by {user.name}"
            )
        except Exception as e:
            return await interaction.response.send_message(f"❌ Kanal oluşturulurken hata oluştu: {e}", ephemeral=True)

        await self.cog.bot.db.execute(
            "INSERT INTO active_tickets (ticket_id, guild_id, channel_id, owner_id, reason, status) VALUES (?, ?, ?, ?, ?, ?)",
            ticket_id, g_id, str(ticket_channel.id), str(user.id), self.reason.value, 'open'
        )

        if hasattr(self.cog.bot, "db"):
            await self.cog.bot.db.log_db_event(
                guild_id=g_id,
                event_type="ticket_create",
                setting_key="ticket_create_on",
                user_id=str(user.id),
                details={
                    "username": str(user.id),
                    "text": f"Bilet Açıldı\nKategori: {self.category.name if self.category else 'Yok'}\nSebep: {self.reason.value}"
                },
                channel_id=str(ticket_channel.id)
            )

        await interaction.response.send_message(f"✅ Biletiniz başarıyla açıldı: {ticket_channel.mention}", ephemeral=True)

        mentions = " ".join([r.mention for r in self.support_roles] + [m.mention for m in self.support_users])
        if not mentions:
            mentions = "Yetkililer"
            
        embed = discord.Embed(
            title=f"🎟️ Destek Talebi: {ticket_id}",
            description=(
                f"Merhaba {user.mention}, destek sistemine hoş geldiniz!\n"
                f"Yetkili ekibimiz ({mentions}) en kısa sürede sizinle ilgilenecektir.\n\n"
                f"**Belirtilen Sebep:**\n```{self.reason.value}```\n\n"
                "Talebiniz çözüme ulaştığında aşağıdaki butonu kullanarak kapatabilirsiniz."
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Sadece yetkililer ve bilet sahibi bu kanalı görebilir.")
        close_view = TicketCloseView(self.cog, ticket_id)
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=close_view)


class TicketCloseView(discord.ui.View):
    def __init__(self, cog: "Tickets", ticket_id: str = None) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.ticket_id = ticket_id

    @discord.ui.button(
        label="🙋‍♂️ Sahiplen",
        style=discord.ButtonStyle.primary,
        custom_id="claim_ticket_btn",
    )
    async def claim_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        channel = interaction.channel
        guild = interaction.guild
        g_id = str(guild.id)
        
        # Check if already claimed
        active = await self.cog.bot.db.fetchone("SELECT * FROM active_tickets WHERE channel_id=?", str(channel.id))
        if not active:
            return await interaction.followup.send("❌ Bilet veritabanında bulunamadı.", ephemeral=True)
        
        if active["claimed_by"]:
            return await interaction.followup.send(f"❌ Bu bilet zaten <@{active['claimed_by']}> tarafından sahiplenilmiş.", ephemeral=True)

        settings = await self.cog.bot.db.fetchone("SELECT support_role_id, support_user_ids FROM ticket_settings WHERE guild_id=?", g_id)
        
        is_support = False
        support_roles_list = []
        support_users_list = []
        if settings:
            if "support_user_ids" in settings.keys() and settings["support_user_ids"]:
                try:
                    import json
                    parsed_u = json.loads(settings["support_user_ids"])
                    if isinstance(parsed_u, list):
                        support_users_list = parsed_u
                        if str(interaction.user.id) in parsed_u:
                            is_support = True
                except Exception: pass
            if "support_role_id" in settings.keys() and settings["support_role_id"]:
                try:
                    import json
                    parsed_r = json.loads(settings["support_role_id"])
                    if isinstance(parsed_r, list):
                        support_roles_list = parsed_r
                        for r_id in parsed_r:
                            role = guild.get_role(int(r_id))
                            if role and role in interaction.user.roles:
                                is_support = True
                    else:
                        support_roles_list = [settings["support_role_id"]]
                        role = guild.get_role(int(settings["support_role_id"]))
                        if role and role in interaction.user.roles: is_support = True
                except Exception:
                    support_roles_list = [settings["support_role_id"]]
                    role = guild.get_role(int(settings["support_role_id"]))
                    if role and role in interaction.user.roles: is_support = True
        
        is_admin = interaction.user.guild_permissions.administrator
        
        if not (is_support or is_admin):
            return await interaction.followup.send("❌ Bu bileti sahiplenme yetkiniz yok.", ephemeral=True)
            
        # İzinleri güncelle: Destek rollerinin ve kullanıcıların odadaki yetkisini sıfırla
        for r_id in support_roles_list:
            role = guild.get_role(int(r_id))
            if role: await channel.set_permissions(role, overwrite=None)
        for u_id in support_users_list:
            user_obj = guild.get_member(int(u_id))
            if user_obj: await channel.set_permissions(user_obj, overwrite=None)
            
        await channel.set_permissions(interaction.user, view_channel=True, send_messages=True, read_message_history=True)
        
        # DB güncelle
        await self.cog.bot.db.execute("UPDATE active_tickets SET claimed_by=? WHERE ticket_id=? AND guild_id=?", str(interaction.user.id), active["ticket_id"], g_id)
        
        if hasattr(self.cog.bot, "db"):
            await self.cog.bot.db.log_db_event(
                guild_id=g_id,
                event_type="ticket_claim",
                setting_key="ticket_create_on", # Using ticket_create_on as the toggle for simplicity
                user_id=str(interaction.user.id),
                details={
                    "username": str(interaction.user.id),
                    "text": f"Bilet Sahiplenildi\nBilet ID: {active['ticket_id']}\nSahiplenen: {interaction.user.mention}"
                },
                channel_id=str(channel.id)
            )
        
        button.disabled = True
        button.style = discord.ButtonStyle.secondary
        button.label = "Sahiplenildi"
        await interaction.message.edit(view=self)
        
        await channel.send(f"🛡️ **Bu bilet {interaction.user.mention} tarafından sahiplenildi!**\nArtık sadece bilet sahibi, işlemi üstlenen yetkili ve üst düzey yöneticiler burayı görebilir.")

    @discord.ui.button(
        label="Ticketi Kapat",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="close_ticket_btn",
    )
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        confirm_view = TicketConfirmCloseView(self.cog)
        await interaction.response.send_message(
            "⚠️ Bu bileti kapatmak istediğinize emin misiniz?",
            view=confirm_view,
            ephemeral=False,
        )


class TicketConfirmCloseView(discord.ui.View):
    def __init__(self, cog: "Tickets") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Evet, Kapat",
        style=discord.ButtonStyle.danger,
        custom_id="confirm_close_btn",
    )
    async def confirm_close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()

        channel = interaction.channel
        guild = interaction.guild
        g_id = str(guild.id)
        
        active_ticket = await self.cog.bot.db.fetchone("SELECT * FROM active_tickets WHERE channel_id=?", str(channel.id))
        
        html_content = await generate_html_transcript(channel, self.cog.bot)
        
        owner_id = None
        ticket_id = channel.name
        if active_ticket:
            owner_id = int(active_ticket["owner_id"])
            ticket_id = active_ticket["ticket_id"]
        elif channel.topic and channel.topic.isdigit():
            owner_id = int(channel.topic)
            
        owner = guild.get_member(owner_id) if owner_id else None

        # DM Owner
        if owner:
            try:
                embed_dm = discord.Embed(
                    title="🎫 Bilet Kapatıldı",
                    description=f"**{guild.name}** sunucusundaki `{ticket_id}` numaralı biletiniz kapatıldı. Görüşme kaydı ektedir.",
                    color=discord.Color.red(),
                )
                transcript_file = discord.File(
                    io.BytesIO(html_content.encode("utf-8")), 
                    filename=f"transcript-{ticket_id}.html"
                )
                await owner.send(embed=embed_dm, file=transcript_file)
            except Exception:
                pass

        # Log channel
        settings = await self.cog.bot.db.fetchone("SELECT log_channel_id FROM ticket_settings WHERE guild_id=?", g_id)
        if settings and settings["log_channel_id"]:
            log_chan = guild.get_channel(int(settings["log_channel_id"]))
            if log_chan:
                try:
                    embed_log = discord.Embed(
                        title="📋 Ticket Transkript",
                        description=(
                            f"Bilet `{ticket_id}` kapatıldı.\n"
                            f"Açan Kişi: <@{owner_id}>\n"
                            f"Kapatan: {interaction.user.mention}"
                        ),
                        color=discord.Color.dark_gray(),
                    )
                    transcript_file = discord.File(
                        io.BytesIO(html_content.encode("utf-8")), 
                        filename=f"transcript-{ticket_id}.html"
                    )
                    await log_chan.send(embed=embed_log, file=transcript_file)
                except Exception:
                    pass

        # Update DB status
        if active_ticket:
            await self.cog.bot.db.execute("UPDATE active_tickets SET status='closed' WHERE ticket_id=? AND guild_id=?", ticket_id, g_id)

        if hasattr(self.cog.bot, "db"):
            await self.cog.bot.db.log_db_event(
                guild_id=g_id,
                event_type="ticket_close",
                setting_key="ticket_close_on",
                user_id=str(interaction.user.id),
                details={
                    "username": str(interaction.user.id),
                    "text": f"Bilet Kapatıldı\nBilet ID: {ticket_id}\nAçan: <@{owner_id}>" if owner_id else f"Bilet Kapatıldı\nBilet ID: {ticket_id}"
                },
                channel_id=str(channel.id)
            )

        await channel.send("🔒 Kanal 5 saniye içinde siliniyor...")
        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user.name}")
        except Exception:
            pass

    @discord.ui.button(
        label="İptal",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel_close_btn",
    )
    async def cancel_close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.message.delete()


class TicketOpenView(discord.ui.View):
    def __init__(self, cog: "Tickets") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Ticket Aç",
        style=discord.ButtonStyle.blurple,
        emoji="🎟️",
        custom_id="open_ticket_btn",
    )
    async def open_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        guild = interaction.guild
        g_id = str(guild.id)
        
        settings = await self.cog.bot.db.fetchone("SELECT * FROM ticket_settings WHERE guild_id=?", g_id)
        if not settings:
            return await interaction.response.send_message("❌ Ticket sistemi bu sunucuda henüz ayarlanmamış.", ephemeral=True)
            
        category_id = settings["category_id"]
        category = guild.get_channel(int(category_id)) if category_id else None
        
        support_roles = []
        if settings and settings["support_role_id"]:
            try:
                import json
                parsed = json.loads(settings["support_role_id"])
                if isinstance(parsed, list):
                    for r_id in parsed:
                        role = guild.get_role(int(r_id))
                        if role: support_roles.append(role)
                else:
                    role = guild.get_role(int(settings["support_role_id"]))
                    if role: support_roles.append(role)
            except Exception:
                role = guild.get_role(int(settings["support_role_id"]))
                if role: support_roles.append(role)

        support_users = []
        if "support_user_ids" in settings.keys() and settings["support_user_ids"]:
            try:
                import json
                parsed = json.loads(settings["support_user_ids"])
                if isinstance(parsed, list):
                    for u_id in parsed:
                        member = guild.get_member(int(u_id))
                        if member: support_users.append(member)
            except Exception:
                pass
        
        # Fetch admin roles
        admin_roles = []
        if settings and "admin_role_id" in settings.keys() and settings["admin_role_id"]:
            try:
                import json
                parsed = json.loads(settings["admin_role_id"])
                if isinstance(parsed, list):
                    for r_id in parsed:
                        role = guild.get_role(int(r_id))
                        if role: admin_roles.append(role)
                else:
                    role = guild.get_role(int(settings["admin_role_id"]))
                    if role: admin_roles.append(role)
            except Exception:
                role = guild.get_role(int(settings["admin_role_id"]))
                if role: admin_roles.append(role)
        
        ticket_counter = settings["ticket_counter"] or 0

        modal = TicketReasonModal(self.cog, guild, category, support_roles, support_users, admin_roles, ticket_counter)
        await interaction.response.send_modal(modal)


class Tickets(commands.Cog):
    category = "Topluluk ve Etkileşim"
    category_emoji = "👥"
    """
    State-of-the-art server-scoped button ticket support system.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.cleanup_task.start()

    def cog_unload(self) -> None:
        self.cleanup_task.cancel()

    @discord.ext.tasks.loop(minutes=30)
    async def cleanup_task(self):
        # Hayalet odaları temizle
        try:
            closed_tickets = await self.bot.db.fetchall("SELECT channel_id, guild_id, ticket_id FROM active_tickets WHERE status='closed'")
            for t in closed_tickets:
                guild = self.bot.get_guild(int(t["guild_id"]))
                if guild:
                    chan = guild.get_channel(int(t["channel_id"]))
                    if chan:
                        try:
                            await chan.delete(reason="Cleanup of ghost ticket channel")
                        except discord.NotFound:
                            pass
                        except Exception as e:
                            log.error(f"Failed to delete ghost channel {chan.id}: {e}")
                # Remove from db to not check again
                await self.bot.db.execute("DELETE FROM active_tickets WHERE ticket_id=? AND guild_id=?", t["ticket_id"], t["guild_id"])
        except Exception as e:
            log.error(f"Ticket cleanup error: {e}")

    @cleanup_task.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

    @commands.group(name="ticket", invoke_without_command=True)
    @kumiho_check("owner")
    async def ticket_group(self, ctx: commands.Context) -> None:
        """Setup the ticket system.\n\n**Usage:** `{prefix}ticket`"""
        p = ctx.prefix
        await ctx.send(
            "🎫 **Ticketing System**\n"
            f"• `{p}ticket setup` — Destek panelini gönderir\n"
            "*(Not: Tüm ticket ayarları artık Web Arayüzü / Dashboard üzerinden yapılmaktadır.)*\n"
            f"• `{p}ticket add <@user>` — Ticketa kullanıcı ekler\n"
            f"• `{p}ticket remove <@user>` — Ticketdan kullanıcı çıkarır"
        )

    @ticket_group.command(name="setup")
    @kumiho_check("owner")
    async def ticket_setup(self, ctx: commands.Context) -> None:
        """Run the setup process.\n\n**Usage:** `{prefix}setup`"""
        g_id = str(ctx.guild.id)
        settings = await self.bot.db.fetchone("SELECT panel_title, panel_desc FROM ticket_settings WHERE guild_id=?", g_id)
        
        title = settings["panel_title"] if settings and settings["panel_title"] else "🎟️ Destek Merkezi"
        desc = settings["panel_desc"] if settings and settings["panel_desc"] else "Sorunuz mu var? Destek ekibimizle iletişime geçmek için butona tıklayın."
        
        embed = discord.Embed(
            title=title,
            description=desc,
            color=discord.Color.blurple(),
        )
        view = TicketOpenView(self)
        await ctx.send(embed=embed, view=view)

    @ticket_group.command(name="add")
    @kumiho_check("owner")
    async def ticket_add(
        self, ctx: commands.Context, member: discord.Member = None
    ) -> None:
        """Adds a member to an existing ticket. Usage: `f.ticket add <@user>`"""
        if not member:
            return await ctx.send(f"Kullanım: `{ctx.prefix}ticket add <@user>`")
        if not ctx.channel.name.startswith("ticket-"):
            return await ctx.send("❌ Bu komut sadece ticket kanallarında kullanılabilir!")
            
        active_ticket = await self.bot.db.fetchone("SELECT owner_id FROM active_tickets WHERE channel_id=?", str(ctx.channel.id))
        owner_id = int(active_ticket["owner_id"]) if active_ticket else (int(ctx.channel.topic) if ctx.channel.topic and ctx.channel.topic.isdigit() else 0)
        
        is_owner = ctx.author.id == owner_id
        is_admin = ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_channels
        
        settings = await self.bot.db.fetchone("SELECT support_role_id, support_user_ids FROM ticket_settings WHERE guild_id=?", str(ctx.guild.id))
        is_support = False
        if settings:
            if "support_user_ids" in settings.keys() and settings["support_user_ids"]:
                try:
                    import json
                    parsed_u = json.loads(settings["support_user_ids"])
                    if isinstance(parsed_u, list) and str(ctx.author.id) in parsed_u:
                        is_support = True
                except Exception: pass
            if not is_support and "support_role_id" in settings.keys() and settings["support_role_id"]:
                try:
                    import json
                    parsed_r = json.loads(settings["support_role_id"])
                    if isinstance(parsed_r, list):
                        for r_id in parsed_r:
                            role = ctx.guild.get_role(int(r_id))
                            if role and role in ctx.author.roles:
                                is_support = True
                                break
                    else:
                        role = ctx.guild.get_role(int(settings["support_role_id"]))
                        if role and role in ctx.author.roles: is_support = True
                except Exception:
                    role = ctx.guild.get_role(int(settings["support_role_id"]))
                    if role and role in ctx.author.roles: is_support = True
                
        if not (is_owner or is_admin or is_support):
            return await ctx.send("❌ Bu işlemi yapabilmek için bilet sahibi veya yetkili olmalısınız.")
            
        await ctx.channel.set_permissions(
            member, view_channel=True, send_messages=True, read_message_history=True
        )
        await ctx.send(f"✅ {member.mention} bu bilete eklendi.")

    @ticket_group.command(name="remove")
    @kumiho_check("owner")
    async def ticket_remove(
        self, ctx: commands.Context, member: discord.Member = None
    ) -> None:
        """Removes a member from a ticket channel. Usage: `f.ticket remove <@user>`"""
        if not member:
            return await ctx.send(f"Kullanım: `{ctx.prefix}ticket remove <@user>`")
        if not ctx.channel.name.startswith("ticket-"):
            return await ctx.send("❌ Bu komut sadece ticket kanallarında kullanılabilir!")
            
        active_ticket = await self.bot.db.fetchone("SELECT owner_id FROM active_tickets WHERE channel_id=?", str(ctx.channel.id))
        owner_id = int(active_ticket["owner_id"]) if active_ticket else (int(ctx.channel.topic) if ctx.channel.topic and ctx.channel.topic.isdigit() else 0)
        
        is_owner = ctx.author.id == owner_id
        is_admin = ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_channels
        
        settings = await self.bot.db.fetchone("SELECT support_role_id, support_user_ids FROM ticket_settings WHERE guild_id=?", str(ctx.guild.id))
        is_support = False
        if settings:
            if "support_user_ids" in settings.keys() and settings["support_user_ids"]:
                try:
                    import json
                    parsed_u = json.loads(settings["support_user_ids"])
                    if isinstance(parsed_u, list) and str(ctx.author.id) in parsed_u:
                        is_support = True
                except Exception: pass
            if not is_support and "support_role_id" in settings.keys() and settings["support_role_id"]:
                try:
                    import json
                    parsed_r = json.loads(settings["support_role_id"])
                    if isinstance(parsed_r, list):
                        for r_id in parsed_r:
                            role = ctx.guild.get_role(int(r_id))
                            if role and role in ctx.author.roles:
                                is_support = True
                                break
                    else:
                        role = ctx.guild.get_role(int(settings["support_role_id"]))
                        if role and role in ctx.author.roles: is_support = True
                except Exception:
                    role = ctx.guild.get_role(int(settings["support_role_id"]))
                    if role and role in ctx.author.roles: is_support = True
                
        if not (is_owner or is_admin or is_support):
            return await ctx.send("❌ Bu işlemi yapabilmek için bilet sahibi veya yetkili olmalısınız.")
            
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.send(f"✅ {member.mention} bu biletten çıkarıldı.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))
