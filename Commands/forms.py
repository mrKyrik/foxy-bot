from __future__ import annotations
from core.checks import kumiho_check, kumiho_app_check
import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import json

# ---------------------------------------------------------
# UI COMPONENTS
# ---------------------------------------------------------

class ReasonModal(discord.ui.Modal):
    def __init__(self, action: str, submitter_id: int, original_message: discord.Message, form_data: dict, selected_role_id: str = None, bot=None):
        super().__init__(title=f"{'Onay' if action == 'approve' else 'Red'} Sebebi")
        self.action = action
        self.submitter_id = submitter_id
        self.original_message = original_message
        self.form_data = form_data
        self.selected_role_id = selected_role_id
        self.bot = bot

        self.reason_input = discord.ui.TextInput(
            label="Sebep (Opsiyonel)",
            style=discord.TextStyle.paragraph,
            required=False,
            placeholder="Bir sebep belirtmek isterseniz buraya yazın..."
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        reason = self.reason_input.value or "Belirtilmedi"
        embed = self.original_message.embeds[0]
        
        if self.action == "approve":
            karar = f"✅ Onaylandı • {interaction.user.mention}"
            renk = discord.Color.green()
            dm_baslik = f"🎉 Form Başvurunuz Onaylandı: {self.form_data['title']}"
            
            form_type = self.form_data.get("form_type", 1)
                
            guild = interaction.guild
            user = guild.get_member(self.submitter_id) if guild else None

            if form_type == 2 and user and self.selected_role_id:
                role = guild.get_role(int(self.selected_role_id))
                if role:
                    try:
                        await user.add_roles(role, reason="Form Onaylandı")
                        embed.add_field(name="Sistem", value=f"{role.mention} rolü verildi.", inline=False)
                    except Exception as e:
                        embed.add_field(name="Sistem", value=f"Rol verilemedi: {e}", inline=False)
                        
            if form_type == 4:
                publish_channel_id = self.form_data.get("action_target")
                if publish_channel_id:
                    pub_channel = interaction.client.get_channel(int(publish_channel_id))
                    if pub_channel:
                        answers = []
                        for field in embed.fields:
                            if field.name not in ["Karar", "Sebep", "Sistem"]:
                                answers.append(field.value)
                        content = "\n\n".join(answers)
                        
                        pub_embed = discord.Embed(
                            description=f"📢 **{self.form_data['title']} ile bir itiraf!**\n\n{content}",
                            color=discord.Color.purple()
                        )
                        
                        pub_view = discord.ui.View()
                        pub_view.add_item(discord.ui.Button(
                            label="İtiraf Et",
                            style=discord.ButtonStyle.primary,
                            custom_id=f"trigger_btn_{self.form_data['form_id']}"
                        ))

                        try:
                            await pub_channel.send(embed=pub_embed, view=pub_view)
                            embed.add_field(name="Sistem", value=f"İçerik {pub_channel.mention} kanalında yayınlandı.", inline=False)
                        except Exception as e:
                            embed.add_field(name="Sistem", value=f"Yayınlama başarısız: {e}", inline=False)

        else:
            karar = f"❌ Reddedildi • {interaction.user.mention}"
            renk = discord.Color.red()
            dm_baslik = f"😔 Form Başvurunuz Reddedildi: {self.form_data['title']}"

        embed.color = renk
        embed.add_field(name="Karar", value=karar, inline=False)
        embed.add_field(name="Sebep", value=reason, inline=False)

        await self.original_message.edit(embed=embed, view=None)

        dm_user = interaction.client.get_user(self.submitter_id)
        if dm_user:
            dm_embed = discord.Embed(title=dm_baslik, color=renk)
            dm_embed.add_field(name="Sebep", value=reason, inline=False)
            try:
                await dm_user.send(embed=dm_embed)
            except discord.Forbidden:
                pass


class FormAdminSettingsView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Form Onay Yetkilisi Rolünü Seçin", min_values=1, max_values=1)
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        role = select.values[0]
        await self.bot.db.execute("INSERT OR REPLACE INTO form_admin_roles (guild_id, role_id) VALUES (?, ?)", str(interaction.guild_id), str(role.id))
        await interaction.response.send_message(f"✅ Form yönetici yetkisi {role.mention} rolüne verildi. Artık bu role sahip olanlar formları onaylayıp reddedebilecek.", ephemeral=True)



class AdminReviewView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def _check_permissions(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        role_data = await self.bot.db.fetchone("SELECT role_id FROM form_admin_roles WHERE guild_id=?", str(interaction.guild_id))
        if role_data:
            role_id = int(role_data[0])
            if any(r.id == role_id for r in interaction.user.roles):
                return True
        return False

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, custom_id="form_approve_adv")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check_permissions(interaction):
            return await interaction.response.send_message("Bunu yapmaya yetkiniz yok.", ephemeral=True)
            
        submitter_id, form_data, selected_role_id, publish_mode = await self._parse_state(interaction)
        if not form_data:
            return await interaction.response.send_message("Form veritabanında bulunamadı.", ephemeral=True)
            
        modal = ReasonModal("approve", submitter_id, interaction.message, form_data, selected_role_id, self.bot, publish_mode=publish_mode)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, custom_id="form_reject_adv")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check_permissions(interaction):
            return await interaction.response.send_message("Bunu yapmaya yetkiniz yok.", ephemeral=True)
            
        submitter_id, form_data, selected_role_id, _ = await self._parse_state(interaction)
        if not form_data:
            return await interaction.response.send_message("Form veritabanında bulunamadı.", ephemeral=True)
            
        modal = ReasonModal("reject", submitter_id, interaction.message, form_data, selected_role_id, self.bot)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🎫 Ticket Aç", style=discord.ButtonStyle.secondary, custom_id="form_ticket_adv")
    async def ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check_permissions(interaction):
            return await interaction.response.send_message("Bunu yapmaya yetkiniz yok.", ephemeral=True)
            
        submitter_id, form_data, _, _ = await self._parse_state(interaction)
            
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        submitter = guild.get_member(submitter_id)
        if not submitter:
            return await interaction.followup.send("Başvuran kullanıcı artık sunucuda değil.", ephemeral=True)
            
        category = discord.utils.get(guild.categories, name="TICKETLAR")
        if not category:
            try:
                category = await guild.create_category("TICKETLAR")
            except Exception as e:
                return await interaction.followup.send(f"Kategori oluşturulamadı: {e}", ephemeral=True)
                
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            submitter: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        try:
            # Ticket sayacını al ve artır
            ticket_settings = await self.bot.db.fetchone("SELECT ticket_counter FROM ticket_settings WHERE guild_id=?", str(guild.id))
            ticket_num = (ticket_settings[0] if ticket_settings else 0) + 1
            
            if ticket_settings is None:
                await self.bot.db.execute("INSERT INTO ticket_settings (guild_id, ticket_counter) VALUES (?, 1)", str(guild.id))
            else:
                await self.bot.db.execute("UPDATE ticket_settings SET ticket_counter=? WHERE guild_id=?", ticket_num, str(guild.id))
                
            channel_name = f"{ticket_num:03d}-{submitter.name}"
            ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
            
            embed = interaction.message.embeds[0]
            
            try:
                from Commands.tickets import TicketCloseView
                tickets_cog = self.bot.get_cog("Tickets")
                close_view = TicketCloseView(tickets_cog, submitter.id) if tickets_cog else None
            except ImportError:
                close_view = None

            await ticket_channel.send(f"{submitter.mention} | {interaction.user.mention}\nForm başvurusu hakkında görüşme kanalı:", embed=embed, view=close_view)
            
            button.disabled = True
            await interaction.message.edit(view=self)
            
            await interaction.followup.send(f"✅ Ticket kanalı açıldı: {ticket_channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Kanal açılamadı: {e}", ephemeral=True)

    @discord.ui.button(label="⚙️ Ayarlar", style=discord.ButtonStyle.secondary, custom_id="form_settings_adv")
    async def settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Sadece sunucu yöneticileri ayarları değiştirebilir.", ephemeral=True)
        
        view = FormAdminSettingsView(self.bot)
        await interaction.response.send_message("Lütfen form işlemlerini yapabilecek (onayla, reddet, ticket aç) yetkili rolünü seçin:", view=view, ephemeral=True)

    async def _parse_state(self, interaction: discord.Interaction):
        import re
        embed = interaction.message.embeds[0]
        
        submitter_match = re.search(r'\((\d+)\)', embed.description)
        submitter_id = int(submitter_match.group(1)) if submitter_match else 0
        
        form_id_match = re.search(r'Form ID: (\S+)', embed.footer.text)
        form_id = form_id_match.group(1) if form_id_match else None
        
        form_data_row = await self.bot.db.fetchone("SELECT * FROM custom_forms WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
        if not form_data_row:
            return submitter_id, None, None
            
        form_data = dict(form_data_row)
        
        selected_role_id = None
        if form_data.get("form_type") == 2:
            role_match = re.search(r'<@&(\d+)>', embed.description)
            if role_match:
                selected_role_id = role_match.group(1)
                
        mode_match = re.search(r'Mode: (\S+)', embed.footer.text)
        publish_mode = mode_match.group(1) if mode_match else "now"
                
        return submitter_id, form_data, selected_role_id, publish_mode


class DynamicFormModal(discord.ui.Modal):
    def __init__(self, form_data: dict, questions: list, bot_db, bot, selected_role_id: str = None, publish_mode: str = "now"):
        super().__init__(title=form_data["title"])
        self.form_data = form_data
        self.questions = questions
        self.bot_db = bot_db
        self.bot = bot
        self.selected_role_id = selected_role_id
        self.publish_mode = publish_mode
        self.inputs = []

        for q in questions:
            label = q["question_text"][:45]
            inp = discord.ui.TextInput(
                label=label,
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=1000
            )
            self.inputs.append(inp)
            self.add_item(inp)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        target_channel = interaction.client.get_channel(int(self.form_data["channel_id"]))
        
        embed = discord.Embed(
            title="Yeni Form Yanıtı",
            color=discord.Color.blue()
        )
        embed.description = f"**Gönderen:** {interaction.user.mention} ({interaction.user.id})\n**Form:** {self.form_data['title']}"
        
        if self.selected_role_id:
            role = guild.get_role(int(self.selected_role_id))
            if role:
                embed.description += f"\n**Seçilen Rol:** {role.mention}"
        
        for i, q in enumerate(self.questions):
            soru = q["question_text"]
            cevap = self.inputs[i].value
            embed.add_field(name=soru, value=cevap, inline=False)
            
        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        embed.set_footer(text=f"Form ID: {self.form_data['form_id']} • {now}")

        user_embed = embed.copy()
        form_type = self.form_data.get("form_type", 1)

        # Build detailed log text for DB
        answers_text = ""
        for i, q in enumerate(self.questions):
            answers_text += f"\n**{q['question_text']}**\n{self.inputs[i].value}\n"
        
        emoji = "📝"
        form_isim = "Başvuru Yapıldı"
        if form_type == 4:
            emoji = "🕵️"
            form_isim = "İtiraf Gönderildi"
        elif form_type == 2:
            emoji = "🛡️"
            form_isim = "Rol Başvurusu Yapıldı"
            
        log_text = f"{emoji} {form_isim}\n**Form:** {self.form_data['title']}\n{answers_text}"

        if form_type == 4 and self.form_data.get("auto_approve", 1) == 1:
            if self.publish_mode == "offline":
                user_embed.title = "Kumiho - İtirafınız Alındı (Çevrimdışı Bekliyor)"
                user_embed.color = discord.Color.orange()
                await interaction.response.send_message("İtirafınız kaydedildi. Siz Discord'da çevrimdışı olduğunuzda otomatik olarak paylaşılacaktır.", embed=user_embed, ephemeral=True)
            elif self.publish_mode == "random":
                user_embed.title = "Kumiho - İtirafınız Alındı (Rastgele Zaman Bekliyor)"
                user_embed.color = discord.Color.orange()
                await interaction.response.send_message("İtirafınız kaydedildi. Önümüzdeki 1 saat içinde rastgele bir zamanda paylaşılacaktır.", embed=user_embed, ephemeral=True)
            else:
                user_embed.title = "Kumiho Oto-Onay - Yanıtınız Alındı ve Yayınlandı"
                user_embed.color = discord.Color.green()
                await interaction.response.send_message("İtirafınız otomatik olarak onaylandı ve paylaşıldı!", embed=user_embed, ephemeral=True)
            
            publish_channel_id = self.form_data.get("action_target")
            if publish_channel_id:
                publish_channel = interaction.client.get_channel(int(publish_channel_id))
                if publish_channel:
                    answers = [inp.value for inp in self.inputs]
                    content = "\n\n".join(answers)
                    
                    publish_embed = discord.Embed(
                        description=f"📢 **{self.form_data['title']} ile bir itiraf!**\n\n{content}",
                        color=discord.Color.purple()
                    )
                    now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                    publish_embed.set_footer(text=f"Form ID: {self.form_data['form_id']} • {now_str}")
                    
                    if self.publish_mode == "now":
                        pub_view = discord.ui.View()
                        pub_view.add_item(discord.ui.Button(
                            label="İtiraf Et",
                            style=discord.ButtonStyle.primary,
                            custom_id=f"trigger_btn_{self.form_data['form_id']}"
                        ))
                        await publish_channel.send(embed=publish_embed, view=pub_view)
                    else:
                        import json
                        import time
                        import random
                        embed_dict = publish_embed.to_dict()
                        embed_json = json.dumps(embed_dict)
                        
                        publish_at = None
                        if self.publish_mode == "random":
                            delay_seconds = random.randint(60, 3600)
                            publish_at = time.time() + delay_seconds
                            
                        await self.bot_db.execute(
                            "INSERT INTO pending_offline_forms (guild_id, submitter_id, channel_id, embed_json, publish_mode, publish_at) VALUES (?, ?, ?, ?, ?, ?)",
                            str(guild.id), str(interaction.user.id), str(publish_channel_id), embed_json, self.publish_mode, publish_at
                        )
                        
            if target_channel:
                await target_channel.send(f"✅ Otomatik onaylanan form logu (Mod: {self.publish_mode}):", embed=embed)
        elif form_type == 2 and self.form_data.get("auto_approve", 1) == 1:
            if self.selected_role_id:
                role = guild.get_role(int(self.selected_role_id))
                if role:
                    try:
                        await interaction.user.add_roles(role, reason="Form Otomatik Onaylandı")
                        embed.add_field(name="Sistem", value=f"{role.mention} rolü başarıyla verildi (Oto Onay).", inline=False)
                        
                        user_embed.title = "Kumiho - Rol Başvurunuz Onaylandı"
                        user_embed.color = discord.Color.green()
                        user_embed.add_field(name="Sistem", value=f"{role.name} rolü hesabınıza tanımlandı.", inline=False)
                        
                        await interaction.response.send_message("Başvurunuz otomatik onaylandı ve rolünüz verildi!", embed=user_embed, ephemeral=True)
                        
                        if target_channel:
                            await target_channel.send("✅ Otomatik onaylanan rol formu logu:", embed=embed)
                            
                    except Exception as e:
                        embed.add_field(name="Sistem Hata", value=f"Rol verilemedi: {e}", inline=False)
                        user_embed.title = "Kumiho - Rol Verilirken Hata Oluştu"
                        user_embed.color = discord.Color.red()
                        await interaction.response.send_message(f"Başvurunuz alındı fakat rol verilirken hata oluştu: {e}", embed=user_embed, ephemeral=True)
                        if target_channel:
                            await target_channel.send("❌ Oto onay sırasında rol verme hatası:", embed=embed)
                else:
                    await interaction.response.send_message("Başvurunuz alındı ancak seçilen rol sunucuda bulunamadı.", ephemeral=True)
                    if target_channel:
                        await target_channel.send("❌ Oto onay başarısız: Rol bulunamadı.", embed=embed)
            else:
                await interaction.response.send_message("Başvurunuz alındı ancak rol seçilmemiş.", ephemeral=True)
        else:
            user_embed.title = "Yanıtınız Alındı - Admin Onayı Bekliyor"
            user_embed.color = discord.Color.orange()
            await interaction.response.send_message("Form başarıyla gönderildi! Admin onayından sonra işleme alınacaktır.", embed=user_embed, ephemeral=True)
            
            if target_channel:
                view = AdminReviewView(bot=self.bot)
                await target_channel.send(embed=embed, view=view)

        if hasattr(self.bot, "db"):
            await self.bot.db.log_db_event(
                guild_id=guild.id,
                event_type="app_create",
                setting_key=None,
                user_id=str(interaction.user.id),
                details={
                    "username": str(interaction.user.id),
                    "text": log_text
                },
                channel_id=str(channel_id) if channel_id else None
            )


import re

class DynamicFormRoleSelect(discord.ui.DynamicItem[discord.ui.Select], template=r'select_form_(?P<id>[a-zA-Z0-9_-]+)'):
    def __init__(self, form_id: str, form_data: dict, questions: list, roles: list[discord.Role], bot):
        self.form_id = form_id
        self.form_data = form_data
        self.questions = questions
        self.bot = bot
        options = [
            discord.SelectOption(label=r.name, value=str(r.id), description="Bu role başvurmak için seçin")
            for r in roles
        ]
        super().__init__(discord.ui.Select(
            placeholder="Başvuracağınız Rolü Seçin...", 
            min_values=1, 
            max_values=1, 
            options=options, 
            custom_id=f"select_form_{form_id}"
        ))

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Item, match: re.Match[str], /):
        form_id = match['id']
        bot = interaction.client
        form_data_row = await bot.db.fetchone("SELECT * FROM custom_forms WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
        if not form_data_row:
            return None
        form_data = dict(form_data_row)
        
        questions = await bot.db.fetchall("SELECT question_text FROM form_questions WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
        qs = [dict(q) for q in questions]
        
        roles_db = await bot.db.fetchall("SELECT role_id FROM form_roles WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
        roles = []
        for r_db in roles_db:
            r = interaction.guild.get_role(int(r_db["role_id"]))
            if r: roles.append(r)
            
        if not roles:
            return None
            
        return cls(form_id, form_data, qs, roles, bot)

    async def callback(self, interaction: discord.Interaction):
        selected_role_id = self.item.values[0]
        modal = DynamicFormModal(self.form_data, self.questions, self.bot.db, self.bot, selected_role_id=selected_role_id)
        await interaction.response.send_modal(modal)


class PublishModeView(discord.ui.View):
    def __init__(self, form_data: dict, questions: list, bot):
        super().__init__(timeout=300)
        self.form_data = form_data
        self.questions = questions
        self.bot = bot

    @discord.ui.button(label="Hemen Paylaş", style=discord.ButtonStyle.primary, custom_id="pub_now")
    async def btn_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DynamicFormModal(self.form_data, self.questions, self.bot.db, self.bot, publish_mode="now")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Çevrimdışı Olunca", style=discord.ButtonStyle.secondary, custom_id="pub_offline")
    async def btn_offline(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DynamicFormModal(self.form_data, self.questions, self.bot.db, self.bot, publish_mode="offline")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="1 Saat İçinde Rastgele", style=discord.ButtonStyle.secondary, custom_id="pub_random")
    async def btn_random(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DynamicFormModal(self.form_data, self.questions, self.bot.db, self.bot, publish_mode="random")
        await interaction.response.send_modal(modal)

    async def callback(self, interaction: discord.Interaction):
        pass # Not used directly on View


class DynamicFormTriggerButton(discord.ui.DynamicItem[discord.ui.Button], template=r'trigger_btn_(?P<id>[a-zA-Z0-9_-]+)'):
    def __init__(self, form_id: str, form_data: dict, questions: list, bot):
        self.form_id = form_id
        self.form_data = form_data
        self.questions = questions
        self.bot = bot
        super().__init__(discord.ui.Button(
            label="İtiraf Et" if form_data.get("form_type") == 4 else "Formu Doldur",
            style=discord.ButtonStyle.primary,
            custom_id=f"trigger_btn_{form_id}"
        ))

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Item, match: re.Match[str], /):
        form_id = match['id']
        bot = interaction.client
        form_data_row = await bot.db.fetchone("SELECT * FROM custom_forms WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
        if not form_data_row:
            return None
        form_data = dict(form_data_row)
        
        questions = await bot.db.fetchall("SELECT question_text FROM form_questions WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
        qs = [dict(q) for q in questions]
        
        return cls(form_id, form_data, qs, bot)

    async def callback(self, interaction: discord.Interaction):
        if self.form_data.get("form_type") == 4:
            view = PublishModeView(self.form_data, self.questions, self.bot)
            await interaction.response.send_message("İtirafınız ne zaman paylaşılsın? Bir seçenek belirleyin, ardından itiraf formunuz açılacaktır.", view=view, ephemeral=True)
        else:
            modal = DynamicFormModal(self.form_data, self.questions, self.bot.db, self.bot)
            await interaction.response.send_modal(modal)


class FormTriggerViewSelect(discord.ui.View):
    def __init__(self, form_data: dict, questions: list, roles: list[discord.Role], bot):
        super().__init__(timeout=None)
        self.add_item(DynamicFormRoleSelect(str(form_data['form_id']), form_data, questions, roles, bot))

class FormTriggerViewButton(discord.ui.View):
    def __init__(self, form_data: dict, questions: list, bot):
        super().__init__(timeout=None)
        self.add_item(DynamicFormTriggerButton(str(form_data['form_id']), form_data, questions, bot))

# ---------------------------------------------------------
# COG
# ---------------------------------------------------------

class FormsCog(commands.Cog):
    category = "Topluluk ve Etkileşim"
    category_emoji = "👥"
    def __init__(self, bot):
        self.bot = bot
        
    async def cog_load(self):
        if not self.web_actions_loop.is_running():
            self.web_actions_loop.start()

    async def cog_unload(self):
        self.web_actions_loop.cancel()

    @tasks.loop(seconds=5, reconnect=True)
    async def web_actions_loop(self):
        try:
            # Sadece summon_form eylemlerini çek
            actions = await self.bot.db.fetchall("SELECT * FROM web_actions WHERE status='pending' AND action_type='summon_form'")
            for action in actions:
                guild_id = action['guild_id']
                action_id = action['action_id']
                try:
                    payload = json.loads(action['payload'])
                    form_id = payload['form_id']
                    target_channel_id = payload['target_channel_id']
                    
                    guild = self.bot.get_guild(int(guild_id))
                    if not guild:
                        continue
                        
                    channel = guild.get_channel(int(target_channel_id))
                    if not channel:
                        continue
                    
                    form_data_row = await self.bot.db.fetchone("SELECT * FROM custom_forms WHERE form_id = ? AND guild_id = ?", form_id, guild_id)
                    if form_data_row:
                        form_data = dict(form_data_row)
                        form_type = form_data.get("form_type", 1)
                        questions = await self.bot.db.fetchall("SELECT question_text FROM form_questions WHERE form_id=? AND guild_id=?", form_id, guild_id)
                        qs = [dict(q) for q in questions]
                        
                        embed = discord.Embed(
                            title=form_data["title"],
                            description="Lütfen aşağıdaki arayüzü kullanarak form/başvuru işleminizi başlatın.",
                            color=discord.Color.blurple()
                        )
                        
                        if form_type == 2:
                            roles_db = await self.bot.db.fetchall("SELECT role_id FROM form_roles WHERE form_id=? AND guild_id=?", form_id, guild_id)
                            roles = []
                            for r_db in roles_db:
                                r = guild.get_role(int(r_db["role_id"]))
                                if r: roles.append(r)
                            
                            if not roles:
                                await channel.send(f"⚠️ **Sistem Uyarı**: `{form_data['title']}` formu için seçilen roller sunucuda bulunamadığı için form oluşturulamadı. Lütfen paneli kontrol edin.")
                                continue
                                
                            view = FormTriggerViewSelect(form_data, qs, roles, self.bot)
                        else:
                            view = FormTriggerViewButton(form_data, qs, self.bot)
                        
                        if isinstance(channel, discord.ForumChannel):
                            await channel.create_thread(name=form_data["title"], embed=embed, view=view)
                        else:
                            await channel.send(embed=embed, view=view)
                except Exception as e:
                    print(f"Web Action Hatası: {e}")
                finally:
                    # İşlendi olarak işaretle
                    await self.bot.db.execute("UPDATE web_actions SET status='completed' WHERE action_id=?", action_id)
        except Exception as e:
            pass

    @app_commands.command(name="form_olustur", description="Yeni bir özel form oluşturur")
    @kumiho_app_check("owner")
    @app_commands.choices(form_turu=[
        app_commands.Choice(name="Normal / Sadece Log", value=1),
        app_commands.Choice(name="Rol Seçimli Form", value=2),
        app_commands.Choice(name="Otomatik Yayın (İtiraf vb.)", value=4),
    ])
    async def form_olustur(
        self,
        interaction: discord.Interaction,
        form_id: str,
        baslik: str,
        form_turu: app_commands.Choice[int],
        soru_1: str,
        hedef_kanal: discord.TextChannel = None,
        soru_2: str = None,
        soru_3: str = None,
        soru_4: str = None,
        soru_5: str = None,
        hedef_roller: str = None,
        yayin_kanali: discord.TextChannel = None
    ):
        """Execute the form_olustur command.\n\n**Usage:** `{prefix}form_olustur`"""
        sorular = [{"question_text": soru_1}]
        if soru_2: sorular.append({"question_text": soru_2})
        if soru_3: sorular.append({"question_text": soru_3})
        if soru_4: sorular.append({"question_text": soru_4})
        if soru_5: sorular.append({"question_text": soru_5})
        
        mevcut = await self.bot.db.fetchone("SELECT form_id FROM custom_forms WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
        if mevcut:
            return await interaction.response.send_message(f"`{form_id}` ID'sine sahip bir form zaten var. Lütfen farklı bir ID seçin.", ephemeral=True)
            
        r_ids = []
        action_target = None
        
        if form_turu.value == 2:
            if not hedef_roller:
                return await interaction.response.send_message("Rol seçimli form için `hedef_roller` parametresine Rol ID'lerini aralarında virgül koyarak girmelisiniz.", ephemeral=True)
            import re
            r_ids = re.findall(r'\d+', hedef_roller)
            if not r_ids:
                return await interaction.response.send_message("Geçerli bir Rol ID bulunamadı. Lütfen sayısal ID'leri girin.", ephemeral=True)
            if len(r_ids) > 5:
                return await interaction.response.send_message("En fazla 5 rol ID'si belirtebilirsiniz.", ephemeral=True)
            
        if form_turu.value in [1, 2] and not hedef_kanal:
            return await interaction.response.send_message("Normal başvuru ve rol formları için bir Hedef/Log Kanalı seçmek zorunludur.", ephemeral=True)
            
        if form_turu.value == 4:
            if not yayin_kanali:
                return await interaction.response.send_message("Otomatik yayın formu için `yayin_kanali` belirtmelisiniz.", ephemeral=True)
            action_target = str(yayin_kanali.id)

        channel_id_str = str(hedef_kanal.id) if hedef_kanal else "0"

        # 1. Forma kayıt ekle
        await self.bot.db.execute(
            "INSERT INTO custom_forms (form_id, guild_id, title, channel_id, form_type, action_target) VALUES (?, ?, ?, ?, ?, ?)",
            form_id, str(interaction.guild_id), baslik[:45], channel_id_str, form_turu.value, action_target
        )
        
        # 2. Soruları ekle
        q_data = [(form_id, str(interaction.guild_id), q["question_text"]) for q in sorular]
        await self.bot.db.executemany("INSERT INTO form_questions (form_id, guild_id, question_text) VALUES (?, ?, ?)", q_data)
        
        # 3. Rolleri ekle
        if form_turu.value == 2 and r_ids:
            r_data = [(form_id, str(interaction.guild_id), rid) for rid in r_ids]
            await self.bot.db.executemany("INSERT INTO form_roles (form_id, guild_id, role_id) VALUES (?, ?, ?)", r_data)
        
        # Arayüze trigger ekle
        form_data = {
            "form_id": form_id, "guild_id": str(interaction.guild_id), "title": baslik[:45],
            "channel_id": channel_id_str, "form_type": form_turu.value, "action_target": action_target
        }
        
        if form_turu.value in [1, 4]:
            self.bot.add_view(FormTriggerViewButton(form_data, sorular, self.bot))
        
        await interaction.response.send_message(f"✅ `{baslik}` formu başarıyla oluşturuldu! Form ID: `{form_id}`\nFormu göndermek için `/form_mesaji_gonder` komutunu kullanın.", ephemeral=True)

    async def form_id_autocompletion(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        if not interaction.guild_id:
            return []
        forms = await self.bot.db.fetchall("SELECT form_id, title FROM custom_forms WHERE guild_id=?", str(interaction.guild_id))
        choices = []
        for f in forms:
            f_id = f["form_id"]
            f_title = f["title"]
            match_str = f"{f_id} - {f_title}"
            if current.lower() in match_str.lower():
                choices.append(app_commands.Choice(name=match_str[:100], value=f_id))
        return choices[:25]

    @app_commands.command(name="form_sil", description="Bir formu veritabanından siler")
    @kumiho_app_check("owner")
    @app_commands.autocomplete(form_id=form_id_autocompletion)
    async def form_sil(self, interaction: discord.Interaction, form_id: str):
        """Delete an existing custom form.
        
        Removes the form and its data from the database.
        
        **Usage:** `/form_sil <form_id>`
        **Required Permission:** Server Owner or Administrator
        """
        mevcut = await self.bot.db.fetchone("SELECT form_id FROM custom_forms WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
        if not mevcut:
            return await interaction.response.send_message("Böyle bir form bulunamadı.", ephemeral=True)
            
        await self.bot.db.execute("DELETE FROM custom_forms WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
        await interaction.response.send_message(f"🗑️ `{form_id}` ID'li form silindi.", ephemeral=True)

    @app_commands.command(name="form_mesaji_gonder", description="Kullanıcıların formu doldurması için butonu veya menüyü gönderir")
    @kumiho_app_check("owner")
    @app_commands.autocomplete(form_id=form_id_autocompletion)
    async def form_mesaji_gonder(self, interaction: discord.Interaction, form_id: str):
        """Send the form trigger message to a channel.
        
        This command posts a message with a button that users can click to fill out the form.
        
        **Usage:** `/form_mesaji_gonder <form_id>`
        **Required Permission:** Server Owner or Administrator
        """
        form_data_row = await self.bot.db.fetchone(
            "SELECT * FROM custom_forms WHERE form_id = ? AND guild_id = ?",
            form_id, str(interaction.guild_id)
        )
        
        if not form_data_row:
            return await interaction.response.send_message("Böyle bir form bulunamadı. Önce `/form_olustur` ile form oluşturun.", ephemeral=True)
            
        form_data = dict(form_data_row)
        form_type = form_data.get("form_type", 1)
        
        questions = await self.bot.db.fetchall("SELECT question_text FROM form_questions WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
        qs = [dict(q) for q in questions]
        
        embed = discord.Embed(
            title=form_data["title"],
            description="Lütfen aşağıdaki arayüzü kullanarak form/başvuru işleminizi başlatın.",
            color=discord.Color.blurple()
        )
        
        if form_type == 2:
            roles_db = await self.bot.db.fetchall("SELECT role_id FROM form_roles WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
            roles = []
            for r_db in roles_db:
                r = interaction.guild.get_role(int(r_db["role_id"]))
                if r: roles.append(r)
                
            if not roles:
                return await interaction.response.send_message("Formda belirtilen roller sunucuda bulunamadı.", ephemeral=True)
                
            view = FormTriggerViewSelect(form_data, qs, roles, self.bot)
        else:
            view = FormTriggerViewButton(form_data, qs, self.bot)
        
        if isinstance(interaction.channel, discord.ForumChannel):
            await interaction.channel.create_thread(name=form_data["title"], embed=embed, view=view)
        else:
            await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("Form mesajı gönderildi!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(FormsCog(bot))
