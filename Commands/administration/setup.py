from __future__ import annotations
import discord
from discord.ext import commands
import logging
import asyncio
from core.checks import kumiho_check

log = logging.getLogger(__name__)

LOG_CATEGORIES = {
    "text": {"title": "📝 Mesaj Log Ayarları", "toggles": {"msg_delete_on": "Silinen Mesaj", "msg_edit_on": "Düzenlenen Mesaj"}},
    "voice": {"title": "🎙️ Ses Log Ayarları", "toggles": {"ses_join_on": "Sese Katıl/Çık", "ses_switch_on": "Kanal Değiş", "ses_stream_on": "Kamera/Yayın"}},
    "mod": {"title": "🛡️ Moderatör Log Ayarları", "toggles": {"mod_role_on": "Rol Verme/Alma", "mod_channel_on": "Kanal İşlemleri", "mod_msg_on": "Mesaj Silme"}},
    "server": {"title": "⚙️ Sunucu Log Ayarları", "toggles": {"srv_update_on": "Sunucu Ayar", "srv_emoji_on": "Emoji Ekle/Çıkar", "srv_role_on": "Toplu Rol", "srv_perm_on": "İzinler"}},
    "warn": {"title": "⚠️ Uyarı Log Ayarları", "toggles": {"warn_add_on": "Uyarı Ekleme", "warn_remove_on": "Uyarı Silme"}},
    "ticket": {"title": "🎫 Ticket Log Ayarları", "toggles": {"ticket_create_on": "Ticket Açma", "ticket_close_on": "Ticket Kapatma"}},
    "app": {"title": "📋 Başvuru Log Ayarları", "toggles": {"app_create_on": "Başvuru Yapma", "app_accept_on": "Başvuru Kabul", "app_reject_on": "Başvuru Red"}},
    "invite": {"title": "💌 Davet Log Ayarları", "toggles": {"invite_create_on": "Davet Oluşturma", "invite_use_on": "Davet Kullanma"}},
    "role": {"title": "🎭 Rol Log Ayarları", "toggles": {"role_add_on": "Rol Verme", "role_remove_on": "Rol Alma"}}
}

class LogToggleView(discord.ui.View):
    def __init__(self, bot: commands.Bot, category_key: str, current_row: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.category_key = category_key
        
        cat_data = LOG_CATEGORIES[category_key]["toggles"]
        for col_name, label in cat_data.items():
            state = current_row.get(col_name, 0)
            btn = discord.ui.Button(
                label=f"{label} ({'AÇIK' if state else 'KAPALI'})", 
                style=discord.ButtonStyle.success if state else discord.ButtonStyle.danger,
                custom_id=col_name
            )
            btn.callback = self.make_callback(btn, col_name, state)
            self.add_item(btn)
            
        back_btn = discord.ui.Button(label="🔙 Log Paneline Dön", style=discord.ButtonStyle.secondary, row=4)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)

    def make_callback(self, button, col_name, state):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer()
            new_state = 0 if state == 1 else 1
            await self.bot.db.execute(f"UPDATE log_settings SET {col_name}=? WHERE guild_id=?", new_state, str(interaction.guild.id))
            try:
                await self.bot.db.execute(f"UPDATE db_log_settings SET {col_name}=? WHERE guild_id=?", new_state, str(interaction.guild.id))
            except: pass
            
            row_db = await self.bot.db.fetchone("SELECT * FROM log_settings WHERE guild_id=?", str(interaction.guild.id))
            new_view = LogToggleView(self.bot, self.category_key, dict(row_db) if row_db else {})
            await interaction.edit_original_response(view=new_view)
        return callback
        
    async def back_callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📝 Log Sistemi Kurulumu",
            description="**Hızlı Kurulum** ile tüm kanalları otomatik açabilir veya **Detaylı Ayarlar** menüsünden tekli şalterleri yönetebilirsiniz.",
            color=discord.Color.blurple()
        )
        await interaction.response.edit_message(embed=embed, view=LogSetupView(self.bot))


class LogDetailedSettingsDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(label="Mesaj Log", description="Silinen ve düzenlenen mesaj logları", emoji="📝", value="text"),
            discord.SelectOption(label="Ses Log", description="Odaya giriş, çıkış ve yayın logları", emoji="🎙️", value="voice"),
            discord.SelectOption(label="Moderasyon Log", description="Yetkili işlemleri logları", emoji="🛡️", value="mod"),
            discord.SelectOption(label="Sunucu Log", description="Rol, izin ve sunucu ayar logları", emoji="⚙️", value="server"),
            discord.SelectOption(label="Uyarı Log", description="Uyarı ekleme/kaldırma logları", emoji="⚠️", value="warn"),
            discord.SelectOption(label="Ticket Log", description="Destek talebi açma/kapatma logları", emoji="🎫", value="ticket"),
            discord.SelectOption(label="Başvuru Log", description="Form onaylama/reddetme logları", emoji="📋", value="app"),
            discord.SelectOption(label="Davet Log", description="Davet oluşturma/kullanma logları", emoji="💌", value="invite"),
            discord.SelectOption(label="Rol Log", description="Kullanıcı rol alma/verme logları", emoji="🎭", value="role"),
        ]
        super().__init__(placeholder="⚙️ Hangi log şalterini yönetmek istersiniz?", min_values=1, max_values=1, options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        await interaction.response.defer()
        
        row_db = await self.bot.db.fetchone("SELECT * FROM log_settings WHERE guild_id=?", str(interaction.guild.id))
        if not row_db:
            await self.bot.db.execute("INSERT OR IGNORE INTO log_settings (guild_id) VALUES (?)", str(interaction.guild.id))
            row_db = {}
            
        view = LogToggleView(self.bot, val, dict(row_db) if row_db else {})
        
        embed = discord.Embed(
            title=LOG_CATEGORIES[val]["title"],
            description="Aşağıdaki butonlara tıklayarak ilgili logları açıp kapatabilirsiniz.",
            color=discord.Color.blurple()
        )
        await interaction.edit_original_response(embed=embed, view=view)


class LogSetupView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(LogDetailedSettingsDropdown(bot))

    @discord.ui.button(label="✨ Hızlı Kurulum", style=discord.ButtonStyle.success, emoji="✨", row=1)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        guild = interaction.guild
        
        # Kategoriyi kur
        category = await guild.create_category("Kumiho Loglar", reason="Log Hızlı Kurulum")
        # Kategoriyi sadece yöneticilere aç
        await category.set_permissions(guild.default_role, view_channel=False)
        
        # Kanal İsimleri (Enojili)
        channel_data = {
            "msg_channel": ("📝-mesaj-log", "Mesaj silme/düzenleme"),
            "ses_channel": ("🎙️-ses-log", "Sese giriş/çıkış"),
            "mod_channel": ("🛡️-mod-log", "Yetkili işlemleri"),
            "sunucu_channel": ("⚙️-sunucu-log", "Sunucu ayarları"),
            "uyari_channel": ("⚠️-uyarı-log", "Uyarı geçmişi"),
            "ticket_channel": ("🎫-ticket-log", "Destek talepleri"),
            "basvuru_channel": ("📋-başvuru-log", "Form kayıtları"),
            "davet_channel": ("💌-davet-log", "Davet takip"),
            "rol_channel": ("🎭-rol-log", "Rol geçmişi")
        }
        
        created_channels = {}
        for db_col, (ch_name, topic) in channel_data.items():
            ch = await guild.create_text_channel(name=ch_name, category=category, topic=topic)
            created_channels[db_col] = str(ch.id)
            await asyncio.sleep(0.5)  # Rate limit koruması
            
        # Veritabanına kaydet
        await self.bot.db.execute("INSERT OR IGNORE INTO log_settings (guild_id) VALUES (?)", str(guild.id))
        
        for col, ch_id in created_channels.items():
            await self.bot.db.execute(f"UPDATE log_settings SET {col}=? WHERE guild_id=?", ch_id, str(guild.id))
            
        # Tüm şalterleri aç
        toggles = [
            "msg_delete_on", "msg_edit_on", "ses_join_on", "ses_switch_on", "ses_stream_on",
            "mod_role_on", "mod_channel_on", "mod_msg_on", "srv_update_on", "srv_emoji_on",
            "srv_role_on", "srv_perm_on", "warn_add_on", "warn_remove_on", "ticket_create_on",
            "ticket_close_on", "app_create_on", "app_accept_on", "app_reject_on", "invite_create_on",
            "invite_use_on", "role_add_on", "role_remove_on"
        ]
        
        for toggle in toggles:
            await self.bot.db.execute(f"UPDATE log_settings SET {toggle}=1 WHERE guild_id=?", str(guild.id))
            
            # Dashboard logları senkronizasyonu
            try:
                await self.bot.db.execute("INSERT OR IGNORE INTO db_log_settings (guild_id) VALUES (?)", str(guild.id))
                await self.bot.db.execute(f"UPDATE db_log_settings SET {toggle}=1 WHERE guild_id=?", str(guild.id))
            except: pass
            
        embed = discord.Embed(
            title="📝 Log Sistemi",
            description="✅ Hızlı kurulum tamamlandı! Tüm emojili log kanalları başarıyla oluşturuldu ve tüm log şalterleri açıldı.",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="🗑️ Fabrika Ayarları", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def reset_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.bot.db.execute("DELETE FROM log_settings WHERE guild_id=?", str(interaction.guild.id))
        await self.bot.db.execute("DELETE FROM db_log_settings WHERE guild_id=?", str(interaction.guild.id))
        
        embed = discord.Embed(
            title="📝 Log Sistemi",
            description="🗑️ Tüm log ayarları ve veritabanı kayıtları sıfırlandı.",
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="🔙 Ana Menüye Dön", style=discord.ButtonStyle.secondary, emoji="🔙", row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚙️ Kumiho Sistem Kurulum Menüsü",
            description="Lütfen aşağıdaki menüden yapılandırmak istediğiniz sistemi seçin.",
            color=discord.Color.blurple()
        )
        await interaction.response.edit_message(embed=embed, view=SetupMainView(self.bot))


class TicketSetupView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(TicketDetailedSettingsDropdown(bot))

    @discord.ui.button(label="✨ Hızlı Kurulum", style=discord.ButtonStyle.success, emoji="✨", row=1)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        guild = interaction.guild
        
        category = await guild.create_category("🎫 Ticket Sistemi", reason="Ticket Hızlı Kurulum")
        # Ticket kategorisini üyelerin görmesine gerek yok, ticketlar özel olacak
        await category.set_permissions(guild.default_role, view_channel=False)
        log_channel = await guild.create_text_channel(name="📁・ticket-log", category=category)
        
        await self.bot.db.execute("INSERT OR IGNORE INTO ticket_settings (guild_id) VALUES (?)", str(guild.id))
        await self.bot.db.execute("UPDATE ticket_settings SET category_id=?, log_channel_id=? WHERE guild_id=?", 
                                  str(category.id), str(log_channel.id), str(guild.id))
                                  
        embed = discord.Embed(
            title="🎫 Ticket Sistemi",
            description="✅ Hızlı kurulum tamamlandı!\n\nTicket kategorisi ve log kanalı oluşturuldu. Panel kurulumu için `f.ticket setup` komutunu kullanabilir veya detaylı ayarlardan paneli gönderebilirsiniz.",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="🗑️ Fabrika Ayarlarına Dön", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def reset_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.bot.db.execute("DELETE FROM ticket_settings WHERE guild_id=?", str(interaction.guild.id))
        embed = discord.Embed(
            title="🗑️ Ticket Sistemi Sıfırlandı",
            description="Tüm ticket ayarları veritabanından silindi. (Discord kanalları silinmedi, gerekirse manuel silebilirsiniz.)",
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=embed, view=None)

class TicketDetailedSettingsDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(label="Destek Paneli Gönder", description="Ticket açma panelini bulunduğunuz kanala atar", emoji="📩", value="send_panel"),
            discord.SelectOption(label="Web Dashboard Ayarları", description="Gelişmiş ayarlar web panelindedir", emoji="🌐", value="web"),
        ]
        super().__init__(placeholder="⚙️ Detaylı Ayarlar (Ticket)...", min_values=1, max_values=1, options=options, row=2)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        await interaction.response.defer()
        if val == "send_panel":
            from Commands.tickets import TicketOpenView
            settings = await self.bot.db.fetchone("SELECT panel_title, panel_desc FROM ticket_settings WHERE guild_id=?", str(interaction.guild.id))
            title = settings["panel_title"] if settings and settings["panel_title"] else "🎟️ Destek Merkezi"
            desc = settings["panel_desc"] if settings and settings["panel_desc"] else "Sorunuz mu var? Destek ekibimizle iletişime geçmek için butona tıklayın."
            
            embed = discord.Embed(
                title=title,
                description=desc,
                color=discord.Color.blurple(),
            )
            # Ticket cog has TicketOpenView, it takes cog as argument.
            # We can pass dummy cog or get the actual cog
            tickets_cog = self.bot.get_cog("Tickets")
            if tickets_cog:
                view = TicketOpenView(tickets_cog)
                await interaction.channel.send(embed=embed, view=view)
                await interaction.edit_original_response(content="✅ Ticket paneli bu kanala gönderildi!", embed=None, view=None)
            else:
                await interaction.edit_original_response(content="❌ Tickets modülü yüklenmemiş!", embed=None, view=None)
        elif sys_type == "form":
            embed.title = "📋 Başvuru Sistemi Kurulumu"
            embed.description = "Yetkili alım ve destek başvuru formlarını kurabilirsiniz."
            view = FormSetupView(self.bot)
            await interaction.edit_original_response(embed=embed, view=view)
        elif sys_type == "suggestion":
            embed.title = "💡 Öneri Sistemi Kurulumu"
            embed.description = "Üyelerin fikirlerini belirteceği öneri kanalını kurabilirsiniz."
            view = SuggestionSetupView(self.bot)
            await interaction.edit_original_response(embed=embed, view=view)
        elif sys_type == "automod":
            embed.title = "🛡️ Otomoderasyon Sistemi Kurulumu"
            embed.description = "Spam, küfür ve reklam korumalarını yapılandırabilirsiniz."
            view = AutoModSetupView(self.bot)
            await interaction.edit_original_response(embed=embed, view=view)
        elif sys_type == "forum":
            embed.title = "💬 Forum Sistemi Kurulumu"
            embed.description = "Sunucu forumunu (Soru-Cevap vb.) tek tuşla kurabilirsiniz."
            view = ForumSetupView(self.bot)
            await interaction.edit_original_response(embed=embed, view=view)
        elif sys_type == "giveaway":
            embed.title = "🎉 Çekiliş Sistemi Kurulumu"
            embed.description = "Çekiliş kanalı ve altyapısını kurabilirsiniz."
            view = GiveawaySetupView(self.bot)
            await interaction.edit_original_response(embed=embed, view=view)
        elif sys_type == "web":
            embed = discord.Embed(
                title="🌐 Web Dashboard",
                description="Destek rolü, transcript gibi gelişmiş ayarları Web Dashboard üzerinden yapabilirsiniz.",
                color=discord.Color.blurple()
            )
            await interaction.edit_original_response(embed=embed, view=None)


class VoiceSetupView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(VoiceDetailedSettingsDropdown(bot))

    @discord.ui.button(label="✨ Hızlı Kurulum", style=discord.ButtonStyle.success, emoji="✨", row=1)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        guild = interaction.guild
        
        category = await guild.create_category("🎙️ Özel Odalar", reason="Özel Ses Hızlı Kurulum")
        hub_channel = await guild.create_voice_channel(name="➕ Oda Oluştur", category=category)
        
        await self.bot.db.execute("INSERT OR REPLACE INTO private_voice_hubs (guild_id, hub_id, category_id) VALUES (?, ?, ?)", 
                                  str(guild.id), str(hub_channel.id), str(category.id))
                                  
        embed = discord.Embed(
            title="🎙️ Özel Ses Odaları",
            description="✅ Hızlı kurulum tamamlandı!\n\nKullanıcılar `➕ Oda Oluştur` kanalına katıldığında otomatik olarak kendilerine ait yönetilebilir odalar açılacaktır.",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="🗑️ Fabrika Ayarlarına Dön", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def reset_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.bot.db.execute("DELETE FROM private_voice_hubs WHERE guild_id=?", str(interaction.guild.id))
        embed = discord.Embed(
            title="🗑️ Özel Ses Sistemi Sıfırlandı",
            description="Özel ses odası (hub) bağlantısı veritabanından silindi.",
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class VoiceDetailedSettingsDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(label="Web Dashboard Ayarları", description="Gelişmiş ayarlar web panelindedir", emoji="🌐", value="web"),
        ]
        super().__init__(placeholder="⚙️ Detaylı Ayarlar (Özel Ses)...", min_values=1, max_values=1, options=options, row=2)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="🌐 Web Dashboard",
            description="Özel oda varsayılan limiti, varsayılan bitrate gibi ince ayarları Web Dashboard üzerinden yapabilirsiniz.",
            color=discord.Color.blurple()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class LevelSetupView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(LevelDetailedSettingsDropdown(bot))

    @discord.ui.button(label="✨ Hızlı Kurulum", style=discord.ButtonStyle.success, emoji="✨", row=1)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        guild = interaction.guild
        
        level_channel = await guild.create_text_channel(name="🎉・seviye-atlama", reason="Seviye Hızlı Kurulum")
        
        await self.bot.db.execute(
            "INSERT INTO level_settings (guild_id, level_channel_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET level_channel_id=excluded.level_channel_id",
            str(guild.id), str(level_channel.id)
        )
                                  
        embed = discord.Embed(
            title="📈 Seviye (Leveling) Sistemi",
            description="✅ Hızlı kurulum tamamlandı!\n\nSeviye atlama bildirim kanalı oluşturuldu. Kullanıcılar mesaj yazdıkça veya seste durdukça XP kazanacaklar.",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="🗑️ Fabrika Ayarlarına Dön", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def reset_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.bot.db.execute("DELETE FROM level_settings WHERE guild_id=?", str(interaction.guild.id))
        await self.bot.db.execute("DELETE FROM level_rewards WHERE guild_id=?", str(interaction.guild.id))
        await self.bot.db.execute("DELETE FROM level_ignores WHERE guild_id=?", str(interaction.guild.id))
        
        embed = discord.Embed(
            title="🗑️ Seviye Sistemi Sıfırlandı",
            description="Seviye genel ayarları, rol ödülleri ve engellenen kanallar veritabanından tamamen silindi. (Üyelerin kazandığı mevcut XP'ler silinmez).",
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class LevelDetailedSettingsDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(label="Web Dashboard Ayarları", description="Gelişmiş ayarlar web panelindedir", emoji="🌐", value="web"),
        ]
        super().__init__(placeholder="⚙️ Detaylı Ayarlar (Seviye)...", min_values=1, max_values=1, options=options, row=2)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="🌐 Web Dashboard",
            description="Özel rol çarpanları (XP boost), kazanım oranları ve rol ödüllerini Web Dashboard üzerinden detaylıca yapılandırabilirsiniz.",
            color=discord.Color.blurple()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class FormSetupView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(FormDetailedSettingsDropdown(bot))

    @discord.ui.button(label="✨ Hızlı Kurulum", style=discord.ButtonStyle.success, emoji="✨", row=1)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        guild = interaction.guild
        
        category = await guild.create_category("📋 Başvurular", reason="Form Hızlı Kurulum")
        log_channel = await guild.create_text_channel(name="gizli-başvuru-log", category=category)
        
        form_id = "yetkili-alim-1"
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO custom_forms (form_id, guild_id, title, channel_id, form_type, auto_approve) VALUES (?, ?, ?, ?, ?, ?)",
            form_id, str(guild.id), "Yetkili Alım Formu", str(log_channel.id), 1, 1
        )
        
        embed = discord.Embed(
            title="📋 Başvuru (Form) Sistemi",
            description=f"✅ Hızlı kurulum tamamlandı!\n\nBaşvuruların düşeceği log kanalı: {log_channel.mention}. Yetkili başvuru formu aktif edildi.",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="🗑️ Fabrika Ayarlarına Dön", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def reset_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.bot.db.execute("DELETE FROM custom_forms WHERE guild_id=?", str(interaction.guild.id))
        
        embed = discord.Embed(
            title="🗑️ Form Sistemi Sıfırlandı",
            description="Tüm başvuru formları (yetkili alım, kayıt vb.) veritabanından silindi.",
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class FormDetailedSettingsDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(label="Web Dashboard Ayarları", description="Gelişmiş ayarlar web panelindedir", emoji="🌐", value="web"),
        ]
        super().__init__(placeholder="⚙️ Detaylı Ayarlar (Form)...", min_values=1, max_values=1, options=options, row=2)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="🌐 Web Dashboard",
            description="Form sorularını özelleştirme ve çoklu form panelleri oluşturma gibi detaylı ayarları Web Dashboard üzerinden yapabilirsiniz.",
            color=discord.Color.blurple()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class SuggestionSetupView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(SuggestionDetailedSettingsDropdown(bot))

    @discord.ui.button(label="✨ Hızlı Kurulum", style=discord.ButtonStyle.success, emoji="✨", row=1)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        guild = interaction.guild
        
        channel = await guild.create_text_channel(name="💡・öneriler", reason="Öneri Hızlı Kurulum")
        
        await self.bot.db.execute(
            "INSERT INTO suggestion_config (guild_id, channel_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id",
            str(guild.id), str(channel.id)
        )
        
        embed = discord.Embed(
            title="💡 Öneri Sistemi",
            description=f"✅ Hızlı kurulum tamamlandı!\n\nÖneriler {channel.mention} kanalına düşecek. Üyeler komut kullanarak öneri iletebilir.",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="🗑️ Fabrika Ayarlarına Dön", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def reset_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.bot.db.execute("DELETE FROM suggestion_config WHERE guild_id=?", str(interaction.guild.id))
        
        embed = discord.Embed(
            title="🗑️ Öneri Sistemi Sıfırlandı",
            description="Öneri kanalı ayarı silindi. Yeni öneri alınmayacak.",
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class SuggestionDetailedSettingsDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(label="Web Dashboard Ayarları", description="Gelişmiş ayarlar web panelindedir", emoji="🌐", value="web"),
        ]
        super().__init__(placeholder="⚙️ Detaylı Ayarlar (Öneri)...", min_values=1, max_values=1, options=options, row=2)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="🌐 Web Dashboard",
            description="Öneri kabul/ret mesajları, oto-yanıtlar ve emojileri özelleştirmek için Web Dashboard'u kullanabilirsiniz.",
            color=discord.Color.blurple()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class AutoModDetailedSettingsDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(label="Küfür Koruması", emoji="🤬", value="profanity"),
            discord.SelectOption(label="Link Koruması", emoji="🔗", value="link"),
            discord.SelectOption(label="Spam Koruması", emoji="🛡️", value="spam"),
        ]
        super().__init__(placeholder="⚙️ Detaylı Ayarlar (OtoMod Aç/Kapat)...", min_values=1, max_values=1, options=options, row=2)
        self.bot = bot

    def _update_automod_status(self, guild_id: str, key: str, status: bool):
        from core.utils import json_load, json_save
        from pathlib import Path
        db_file = Path("Data/automod.json")
        data = json_load(db_file)
        
        if key not in data:
            data[key] = {}
            
        data[key][guild_id] = status
        json_save(db_file, data)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild_id = str(interaction.guild.id)
        selected = self.values[0]
        
        from core.utils import json_load
        from pathlib import Path
        db_file = Path("Data/automod.json")
        data = json_load(db_file)
        
        # Determine current status to toggle
        target_key = ""
        if selected == "profanity": target_key = "antiprofanity"
        elif selected == "link": target_key = "antilink"
        elif selected == "spam": target_key = "antispam"
        
        current_status = False
        if target_key in data and guild_id in data[target_key]:
            current_status = data[target_key][guild_id]
            
        new_status = not current_status
        self._update_automod_status(guild_id, target_key, new_status)
        
        durum_text = "🟢 Aktif" if new_status else "🔴 Devre Dışı"
        
        embed = discord.Embed(
            title="🛡️ Otomoderasyon Detaylı Ayar",
            description=f"Seçilen koruma: **{selected.capitalize()}**\nYeni Durum: **{durum_text}**",
            color=discord.Color.green() if new_status else discord.Color.red()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class AutoModSetupView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(AutoModDetailedSettingsDropdown(bot))

    @discord.ui.button(label="✨ Hızlı Kurulum (Max Güvenlik)", style=discord.ButtonStyle.success, emoji="🛡️", row=1)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        guild_id = str(interaction.guild.id)
        
        from core.utils import json_load, json_save
        from pathlib import Path
        db_file = Path("Data/automod.json")
        data = json_load(db_file)
        
        for k in ["antilink", "antispam", "antiprofanity"]:
            if k not in data:
                data[k] = {}
            data[k][guild_id] = True
            
        json_save(db_file, data)
        
        embed = discord.Embed(
            title="🛡️ Otomoderasyon Sistemi",
            description="✅ Maksimum güvenlik aktifleştirildi!\n\nKüfür, reklam (link) ve spam korumaları açıldı.",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="🗑️ Korumaları Kapat", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def reset_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        guild_id = str(interaction.guild.id)
        
        from core.utils import json_load, json_save
        from pathlib import Path
        db_file = Path("Data/automod.json")
        data = json_load(db_file)
        
        for k in ["antilink", "antispam", "antiprofanity"]:
            if k in data and guild_id in data[k]:
                data[k][guild_id] = False
                
        json_save(db_file, data)
        
        embed = discord.Embed(
            title="🛡️ Otomoderasyon Kapatıldı",
            description="Tüm korumalar devre dışı bırakıldı.",
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class ForumSetupView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(ForumDetailedSettingsDropdown(bot))

    @discord.ui.button(label="✨ Hızlı Kurulum", style=discord.ButtonStyle.success, emoji="✨", row=1)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        guild = interaction.guild
        
        forum_channel = await guild.create_forum_channel(name="💬・sunucu-forumu", reason="Forum Hızlı Kurulum")
        
        embed = discord.Embed(
            title="💬 Forum Sistemleri",
            description=f"✅ Hızlı kurulum tamamlandı!\n\nForum kanalı oluşturuldu: {forum_channel.mention}. Üyeleriniz artık burada konular (post) açabilir.",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class ForumDetailedSettingsDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(label="Web Dashboard Ayarları", description="Gelişmiş ayarlar web panelindedir", emoji="🌐", value="web"),
        ]
        super().__init__(placeholder="⚙️ Detaylı Ayarlar (Forum)...", min_values=1, max_values=1, options=options, row=2)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="🌐 Web Dashboard",
            description="Otomatik etiket (tag) zorunlulukları ve konu kilitlenme ayarları gibi detayları Web Dashboard üzerinden yapılandırabilirsiniz.",
            color=discord.Color.blurple()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class GiveawaySetupView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(GiveawayDetailedSettingsDropdown(bot))

    @discord.ui.button(label="✨ Hızlı Kurulum", style=discord.ButtonStyle.success, emoji="✨", row=1)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        guild = interaction.guild
        
        channel = await guild.create_text_channel(name="🎉・çekilişler", reason="Çekiliş Hızlı Kurulum")
        
        embed = discord.Embed(
            title="🎉 Çekiliş Sistemi",
            description=f"✅ Hızlı kurulum tamamlandı!\n\nÇekilişler için {channel.mention} kanalı oluşturuldu. Çekiliş başlatmak için `f.giveaway` komutlarını kullanabilirsiniz.",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class GiveawayDetailedSettingsDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(label="Web Dashboard Ayarları", description="Gelişmiş ayarlar web panelindedir", emoji="🌐", value="web"),
        ]
        super().__init__(placeholder="⚙️ Detaylı Ayarlar (Çekiliş)...", min_values=1, max_values=1, options=options, row=2)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="🌐 Web Dashboard",
            description="Çekiliş yöneticisi rolleri (Giveaway Manager) ve çekilişe katılması yasaklanan rolleri (Blacklist) Web Dashboard üzerinden ayarlayabilirsiniz.",
            color=discord.Color.blurple()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class SetupDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(label="Log Sistemi", description="Log kanalları ve şalter ayarları", emoji="📝", value="log"),
            discord.SelectOption(label="Ticket Sistemi", description="Destek talebi sistemi ayarları", emoji="🎫", value="ticket"),
            discord.SelectOption(label="Özel Ses Odaları", description="Kullanıcı ses odası oluşturma sistemi", emoji="🎙️", value="voice"),
            discord.SelectOption(label="Seviye Sistemi", description="XP ve rol ödül sistemi", emoji="📈", value="level"),
            discord.SelectOption(label="Başvuru Sistemi", description="Form ve yetkili başvuru sistemi", emoji="📋", value="app"),
            discord.SelectOption(label="Öneri Sistemi", description="Öneri alma ve oylama sistemi", emoji="💡", value="suggestion"),
            discord.SelectOption(label="Otomoderasyon", description="Küfür, spam, link filtreleri", emoji="🛡️", value="automod"),
            discord.SelectOption(label="Forum Sistemleri", description="Sunucu forumları kurulumu", emoji="💬", value="forum"),
            discord.SelectOption(label="Çekiliş Sistemi", description="Çekiliş yöneticisi ayarları", emoji="🎉", value="giveaway"),
        ]
        super().__init__(placeholder="🛠️ Bir Sistem Seçin...", min_values=1, max_values=1, options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        sys_type = self.values[0]
        
        if sys_type == "log":
            embed = discord.Embed(
                title="📝 Log Sistemi Kurulumu",
                description="**Hızlı Kurulum** ile tüm kanalları otomatik açabilir veya **Detaylı Ayarlar** menüsünden tekli şalterleri yönetebilirsiniz.",
                color=discord.Color.blurple()
            )
            await interaction.response.edit_message(embed=embed, view=LogSetupView(self.bot))
        else:
            await interaction.response.send_message(f"Bu modül ({sys_type}) yapım aşamasındadır!", ephemeral=True)


class SetupMainView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(SetupDropdown(bot))


class SetupSystem(commands.Cog):
    category = "Yönetim ve Ayarlar"
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="setup")
    @kumiho_check("owner")
    async def setup_cmd(self, ctx: commands.Context) -> None:
        """Kumiho Bot Sistem Kurulum ve Yönetim Paneli"""
        embed = discord.Embed(
            title="⚙️ Kumiho Sistem Kurulum Menüsü",
            description="Lütfen aşağıdaki menüden yapılandırmak istediğiniz sistemi seçin.",
            color=discord.Color.blurple()
        )
        view = SetupMainView(self.bot)
        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetupSystem(bot))
