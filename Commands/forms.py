from core.checks import kumiho_check, kumiho_app_check
import discord
from discord.ext import commands
from discord import app_commands
import datetime

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
                    pub_channel = guild.get_channel(int(publish_channel_id))
                    if pub_channel:
                        pub_embed = discord.Embed(title=self.form_data['title'], color=discord.Color.gold())
                        for field in embed.fields:
                            if field.name not in ["Karar", "Sebep", "Sistem"]:
                                pub_embed.add_field(name=field.name, value=field.value, inline=False)
                        try:
                            await pub_channel.send(embed=pub_embed)
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


class AdminReviewView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, custom_id="form_approve_adv")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Bunu yapmaya yetkiniz yok.", ephemeral=True)
            
        submitter_id, form_data, selected_role_id = await self._parse_state(interaction)
        if not form_data:
            return await interaction.response.send_message("Form veritabanında bulunamadı.", ephemeral=True)
            
        modal = ReasonModal("approve", submitter_id, interaction.message, form_data, selected_role_id, self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, custom_id="form_reject_adv")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Bunu yapmaya yetkiniz yok.", ephemeral=True)
            
        submitter_id, form_data, selected_role_id = await self._parse_state(interaction)
        if not form_data:
            return await interaction.response.send_message("Form veritabanında bulunamadı.", ephemeral=True)
            
        modal = ReasonModal("reject", submitter_id, interaction.message, form_data, selected_role_id, self.bot)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🎫 Ticket Aç", style=discord.ButtonStyle.secondary, custom_id="form_ticket_adv")
    async def ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Bunu yapmaya yetkiniz yok.", ephemeral=True)
            
        submitter_id, form_data, _ = await self._parse_state(interaction)
            
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
            channel_name = f"ticket-{submitter.name}"
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
                
        return submitter_id, form_data, selected_role_id


class DynamicFormModal(discord.ui.Modal):
    def __init__(self, form_data: dict, questions: list, bot_db, bot, selected_role_id: str = None):
        super().__init__(title=form_data["title"])
        self.form_data = form_data
        self.questions = questions
        self.bot_db = bot_db
        self.bot = bot
        self.selected_role_id = selected_role_id
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
        await interaction.response.send_message("Form başarıyla gönderildi! Teşekkür ederiz.", ephemeral=True)
        
        guild = interaction.guild
        channel_id = int(self.form_data["channel_id"])
        target_channel = guild.get_channel(channel_id)
        
        if not target_channel:
            return

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

        view = AdminReviewView(bot=self.bot)
        await target_channel.send(embed=embed, view=view)


class FormRoleSelect(discord.ui.Select):
    def __init__(self, form_data: dict, questions: list, roles: list[discord.Role], bot):
        self.form_data = form_data
        self.questions = questions
        self.bot = bot
        options = [
            discord.SelectOption(label=r.name, value=str(r.id), description="Bu role başvurmak için seçin")
            for r in roles
        ]
        super().__init__(placeholder="Başvuracağınız Rolü Seçin...", min_values=1, max_values=1, options=options, custom_id=f"select_form_{form_data['form_id']}")

    async def callback(self, interaction: discord.Interaction):
        selected_role_id = self.values[0]
        modal = DynamicFormModal(self.form_data, self.questions, self.bot.db, self.bot, selected_role_id=selected_role_id)
        await interaction.response.send_modal(modal)

class FormTriggerViewSelect(discord.ui.View):
    def __init__(self, form_data: dict, questions: list, roles: list[discord.Role], bot):
        super().__init__(timeout=None)
        self.add_item(FormRoleSelect(form_data, questions, roles, bot))

class FormTriggerViewButton(discord.ui.View):
    def __init__(self, form_data: dict, questions: list, bot):
        super().__init__(timeout=None)
        self.form_data = form_data
        self.questions = questions
        self.bot = bot
        
        btn = discord.ui.Button(
            label="Formu Doldur",
            style=discord.ButtonStyle.primary,
            custom_id=f"trigger_btn_{form_data['form_id']}"
        )
        btn.callback = self.button_callback
        self.add_item(btn)
        
    async def button_callback(self, interaction: discord.Interaction):
        modal = DynamicFormModal(self.form_data, self.questions, self.bot.db, self.bot)
        await interaction.response.send_modal(modal)

# ---------------------------------------------------------
# COG
# ---------------------------------------------------------

class FormsCog(commands.Cog):
    category = "Topluluk ve Etkileşim"
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            self.bot.add_view(AdminReviewView(self.bot))
            
            forms = await self.bot.db.fetchall("SELECT * FROM custom_forms")
            for f in forms:
                form_data = dict(f)
                form_type = form_data.get("form_type", 1)
                
                questions = await self.bot.db.fetchall("SELECT question_text FROM form_questions WHERE form_id=? AND guild_id=?", form_data["form_id"], form_data["guild_id"])
                qs = [dict(q) for q in questions]
                
                if form_type in [1, 4]:
                    self.bot.add_view(FormTriggerViewButton(form_data, qs, self.bot))
                elif form_type == 2:
                    roles_db = await self.bot.db.fetchall("SELECT role_id FROM form_roles WHERE form_id=? AND guild_id=?", form_data["form_id"], form_data["guild_id"])
                    role_ids = [r["role_id"] for r in roles_db]
                    
                    guild = self.bot.get_guild(int(form_data["guild_id"]))
                    if guild:
                        roles = [guild.get_role(int(r)) for r in role_ids if guild.get_role(int(r))]
                        if roles:
                            self.bot.add_view(FormTriggerViewSelect(form_data, qs, roles, self.bot))
        except Exception as e:
            print(f"Form views yuklenirken hata: {e}")

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
        hedef_kanal: discord.TextChannel,
        form_turu: app_commands.Choice[int],
        soru_1: str,
        soru_2: str = None,
        soru_3: str = None,
        soru_4: str = None,
        soru_5: str = None,
        hedef_roller: str = None,
        yayin_kanali: discord.TextChannel = None
    ):
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
            
        if form_turu.value == 4:
            if not yayin_kanali:
                return await interaction.response.send_message("Otomatik yayın formu için `yayin_kanali` belirtmelisiniz.", ephemeral=True)
            action_target = str(yayin_kanali.id)

        # 1. Forma kayıt ekle
        await self.bot.db.execute(
            "INSERT INTO custom_forms (form_id, guild_id, title, channel_id, form_type, action_target) VALUES (?, ?, ?, ?, ?, ?)",
            form_id, str(interaction.guild_id), baslik[:45], str(hedef_kanal.id), form_turu.value, action_target
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
            "channel_id": str(hedef_kanal.id), "form_type": form_turu.value, "action_target": action_target
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
        mevcut = await self.bot.db.fetchone("SELECT form_id FROM custom_forms WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
        if not mevcut:
            return await interaction.response.send_message("Böyle bir form bulunamadı.", ephemeral=True)
            
        await self.bot.db.execute("DELETE FROM custom_forms WHERE form_id=? AND guild_id=?", form_id, str(interaction.guild_id))
        await interaction.response.send_message(f"🗑️ `{form_id}` ID'li form silindi.", ephemeral=True)

    @app_commands.command(name="form_mesaji_gonder", description="Kullanıcıların formu doldurması için butonu veya menüyü gönderir")
    @kumiho_app_check("owner")
    @app_commands.autocomplete(form_id=form_id_autocompletion)
    async def form_mesaji_gonder(self, interaction: discord.Interaction, form_id: str):
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
        
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("Form mesajı gönderildi!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(FormsCog(bot))
