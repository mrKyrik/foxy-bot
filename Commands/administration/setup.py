from __future__ import annotations
import discord
from discord.ext import commands
import logging
import asyncio
from core.checks import kumiho_check

log = logging.getLogger(__name__)

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
        # Tekil şalter yönetim mantığı daha sonra eklenecek, şimdilik sadece bilgilendirme yapıyoruz.
        await interaction.response.send_message(f"Seçilen sistem: {val} - Bu özellik çok yakında tam entegre edilecek.", ephemeral=True)


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
