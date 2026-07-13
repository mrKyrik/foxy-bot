from __future__ import annotations
import discord
from discord.ext import commands, tasks
import logging
import asyncio
from core.checks import kumiho_check

log = logging.getLogger("Commands.private_voice")

import time

# {channel_id: [timestamp1, timestamp2]} - rename cooldown tracker
_rename_history: dict[int, list[float]] = {}

class AdminActionView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        
    @discord.ui.button(label="Odayı Zorla Sil", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def force_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            await channel.delete(reason=f"{interaction.user} tarafından zorla silindi.")
            await interaction.response.send_message("✅ Oda başarıyla silindi.", ephemeral=True)
        else:
            await interaction.response.send_message("Oda zaten silinmiş.", ephemeral=True)

class AdminVoicePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📊 Oda Durumunu Çek", style=discord.ButtonStyle.primary, custom_id="admin_voice_panel_btn")
    async def open_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("Bu paneli görüntüleme yetkiniz yok.", ephemeral=True)
            
        row = await interaction.client.db.fetchone("SELECT channel_id FROM private_voice_rooms WHERE log_message_id=?", str(interaction.message.id))
        if not row:
            return await interaction.response.send_message("❌ Veritabanı kaydı bulunamadı. Oda silinmiş olabilir.", ephemeral=True)
            
        channel = interaction.guild.get_channel(int(row[0]))
        if not channel:
            return await interaction.response.send_message("❌ Bu oda artık mevcut değil (Discord üzerinden silinmiş).", ephemeral=True)
            
        embed = discord.Embed(title=f"📊 Oda Analizi: {channel.name}", color=discord.Color.blue())
        members = channel.members
        m_list = []
        for m in members:
            status = []
            if m.voice:
                if m.voice.self_video: status.append("📹")
                if m.voice.self_stream: status.append("📺")
                if m.voice.self_mute: status.append("🔇")
                if m.voice.self_deaf: status.append("🎧")
            m_list.append(f"• {m.mention} {''.join(status)}")
            
        embed.add_field(name="👥 Kişi Sayısı", value=f"{len(members)} / {channel.user_limit if channel.user_limit > 0 else '∞'}", inline=True)
        embed.add_field(name="📻 Bit Hızı", value=f"{channel.bitrate//1000} kbps", inline=True)
        embed.add_field(name="👀 İçerideki Kullanıcılar", value="\n".join(m_list) if m_list else "Oda boş", inline=False)
        
        view = AdminActionView(channel.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class RenameModal(discord.ui.Modal, title='Oda İsmini Değiştir'):
    name_input = discord.ui.TextInput(
        label='Yeni Oda İsmi',
        style=discord.TextStyle.short,
        placeholder='Örn: Sohbet Odası',
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel_id = interaction.channel.id
        now = time.monotonic()
        window = 600  # 10 dakika
        history = _rename_history.get(channel_id, [])
        # 10 dakika dışına çıkan kayıtları temizle
        history = [t for t in history if now - t < window]
        if len(history) >= 2:
            remaining = int(window - (now - history[0]))
            mins, secs = divmod(remaining, 60)
            return await interaction.response.send_message(
                f"❌ Discord isim değiştirme limitine ulaştınız (10 dakikada 2 kez). "
                f"**{mins} dakika {secs} saniye** sonra tekrar deneyin.",
                ephemeral=True
            )
        history.append(now)
        _rename_history[channel_id] = history
        try:
            await interaction.channel.edit(name=self.name_input.value)
            await interaction.client.db.execute("INSERT INTO private_voice_settings (user_id, room_name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET room_name=excluded.room_name", str(interaction.user.id), self.name_input.value)
            await interaction.response.send_message(f"Oda ismi `{self.name_input.value}` olarak değiştirildi.", ephemeral=True)
            cog = interaction.client.get_cog("PrivateVoice")
            if cog: await cog.log_oda_update(interaction, f"Oda ismi değiştirildi: {self.name_input.value}")
        except discord.HTTPException as e:
            # Cooldown kaydını geri al çünkü işlem başarısız oldu
            history.pop()
            _rename_history[channel_id] = history
            await interaction.response.send_message("❌ İşlem başarısız oldu. Lütfen tekrar deneyin.", ephemeral=True)

class LimitModal(discord.ui.Modal, title='Oda Kişi Limiti'):
    limit_input = discord.ui.TextInput(
        label='Kişi Limiti (0-99)',
        style=discord.TextStyle.short,
        placeholder='Sınırsız için 0 yazın',
        required=True,
        max_length=2
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            limit = int(self.limit_input.value)
            if limit < 0 or limit > 99:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message("Lütfen 0 ile 99 arasında geçerli bir sayı girin.", ephemeral=True)
            
        try:
            await interaction.channel.edit(user_limit=limit)
            await interaction.client.db.execute("INSERT INTO private_voice_settings (user_id, user_limit) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET user_limit=excluded.user_limit", str(interaction.user.id), limit)
            await interaction.response.send_message(f"Oda kişi limiti `{limit}` olarak ayarlandı." if limit > 0 else "Oda kişi limiti kaldırıldı (Sınırsız).", ephemeral=True)
            cog = interaction.client.get_cog("PrivateVoice")
            if cog: await cog.log_oda_update(interaction, f"Oda limiti ayarlandı: {limit if limit > 0 else 'Sınırsız'}")
        except Exception as e:
            if getattr(e, 'status', None) == 429:
                await interaction.response.send_message("❌ Discord API limitine takıldınız. Odaların isimleri en fazla 10 dakikada 2 kez değiştirilebilir!", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ İşlem başarısız oldu: {type(e).__name__} - {str(e)}", ephemeral=True)

class MemberKickSelect(discord.ui.Select):
    def __init__(self, members):
        self.category = "Eğlence ve Araçlar"
        options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in members][:25]
        super().__init__(placeholder="Atılacak üyeyi seçin...", options=options, custom_id="pv_kick_select")

    async def callback(self, interaction: discord.Interaction):
        member_id = int(self.values[0])
        member = interaction.guild.get_member(member_id)
        if member and member in interaction.channel.members:
            await member.move_to(None)
            await interaction.response.send_message(f"{member.mention} odadan atıldı.", ephemeral=True)
        else:
            await interaction.response.send_message("Üye odada bulunamadı.", ephemeral=True)

class MemberTransferSelect(discord.ui.Select):
    def __init__(self, members):
        options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in members][:25]
        super().__init__(placeholder="Devredilecek üyeyi seçin...", options=options, custom_id="pv_transfer_select")

    async def callback(self, interaction: discord.Interaction):
        member_id = int(self.values[0])
        new_owner = interaction.guild.get_member(member_id)
        old_owner = interaction.user
        # DB'yi güncelle
        await interaction.client.db.execute("UPDATE private_voice_rooms SET owner_id=? WHERE channel_id=?", str(member_id), str(interaction.channel.id))
        # Eski sahibin özel kanalda bağlanma yetkisini sıradan kullanıcı seviyesine indir
        old_overwrite = interaction.channel.overwrites_for(old_owner)
        old_overwrite.connect = None
        old_overwrite.view_channel = None
        await interaction.channel.set_permissions(old_owner, overwrite=old_overwrite if old_overwrite.is_empty() is False else None)
        # Yeni sahibin kanalda kilitliyken bile girebilmesi için yetki ver
        if new_owner:
            await interaction.channel.set_permissions(new_owner, connect=True, view_channel=True)
        await interaction.response.send_message(f"Oda sahipliği <@{member_id}> kullanıcısına devredildi.", ephemeral=True)

class WhitelistSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="✅ İzin Verilenleri (Whitelist) Seç", min_values=1, max_values=10, row=3, custom_id="pv_whitelist")

    async def callback(self, interaction: discord.Interaction):
        # Tüm yetki güncellemelerini tek seferde paketleyip gönder (Bulk - Rate Limit koruması)
        overwrites = dict(interaction.channel.overwrites)
        for user in self.values:
            ow = overwrites.get(user, discord.PermissionOverwrite())
            ow.connect = True
            ow.view_channel = True
            overwrites[user] = ow
        await interaction.channel.edit(overwrites=overwrites)
        await interaction.response.send_message(f"✅ {len(self.values)} kullanıcıya odaya giriş izni verildi.", ephemeral=True)

class BanlistSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="⛔ Yasaklananları (Banlist) Seç", min_values=1, max_values=10, row=4, custom_id="pv_banlist")

    async def callback(self, interaction: discord.Interaction):
        # Tüm yetki güncellemelerini tek seferde paketleyip gönder (Bulk - Rate Limit koruması)
        overwrites = dict(interaction.channel.overwrites)
        to_kick = []
        for user in self.values:
            ow = overwrites.get(user, discord.PermissionOverwrite())
            ow.connect = False
            ow.view_channel = False
            overwrites[user] = ow
            if isinstance(user, discord.Member) and user in interaction.channel.members:
                to_kick.append(user)
        await interaction.channel.edit(overwrites=overwrites)
        # Yasaklanan kullanıcıları kick et
        for member in to_kick:
            try:
                await member.move_to(None)
            except Exception:
                pass
        await interaction.response.send_message(f"⛔ {len(self.values)} kullanıcı odadan yasaklandı.", ephemeral=True)


class PrivateVoiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(WhitelistSelect())
        self.add_item(BanlistSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        row = await interaction.client.db.fetchone("SELECT owner_id FROM private_voice_rooms WHERE channel_id=?", str(interaction.channel.id))
        if row and str(row[0]) == str(interaction.user.id):
            return True
        await interaction.response.send_message("Bu odayı yönetme yetkiniz yok!", ephemeral=True)
        return False

    @discord.ui.button(label="Odayı Kilitle", style=discord.ButtonStyle.danger, emoji="🔒", row=0, custom_id="pv_lock")
    async def lock_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        role = interaction.guild.default_role
        perms = interaction.channel.overwrites_for(role)
        try:
            if perms.connect == False:
                perms.connect = None
                button.style = discord.ButtonStyle.danger
                button.label = "Odayı Kilitle"
                await interaction.channel.set_permissions(role, overwrite=perms)
                await interaction.edit_original_response(view=self)
                await interaction.followup.send("Oda kilidi açıldı.", ephemeral=True)
            else:
                perms.connect = False
                button.style = discord.ButtonStyle.success
                button.label = "Kilidi Aç"
                await interaction.channel.set_permissions(role, overwrite=perms)
                await interaction.edit_original_response(view=self)
                await interaction.followup.send("Oda kilitlendi.", ephemeral=True)
            await interaction.client.db.execute("INSERT INTO private_voice_settings (user_id, is_locked) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET is_locked=excluded.is_locked", str(interaction.user.id), 1 if perms.connect == False else 0)
            cog = interaction.client.get_cog("PrivateVoice")
            if cog: await cog.log_oda_update(interaction, "Oda kilitlendi" if perms.connect == False else "Oda kilidi açıldı")
        except Exception as e:
            err_msg = f"❌ Bir hata oluştu: {type(e).__name__} - {str(e)}"
            if getattr(e, 'status', None) == 429:
                err_msg = "❌ Discord API limitine takıldınız. Lütfen biraz bekleyin."
            if not interaction.response.is_done():
                await interaction.response.send_message(err_msg, ephemeral=True)
            else:
                await interaction.followup.send(err_msg, ephemeral=True)

    @discord.ui.button(label="Odayı Gizle", style=discord.ButtonStyle.secondary, emoji="👻", row=0, custom_id="pv_hide")
    async def hide_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        role = interaction.guild.default_role
        perms = interaction.channel.overwrites_for(role)
        try:
            if perms.view_channel == False:
                perms.view_channel = None
                button.style = discord.ButtonStyle.secondary
                button.label = "Odayı Gizle"
                await interaction.channel.set_permissions(role, overwrite=perms)
                await interaction.edit_original_response(view=self)
                await interaction.followup.send("Oda artık herkese görünür.", ephemeral=True)
            else:
                perms.view_channel = False
                button.style = discord.ButtonStyle.success
                button.label = "Odayı Göster"
                await interaction.channel.set_permissions(role, overwrite=perms)
                await interaction.edit_original_response(view=self)
                await interaction.followup.send("Oda gizlendi.", ephemeral=True)
            await interaction.client.db.execute("INSERT INTO private_voice_settings (user_id, is_hidden) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET is_hidden=excluded.is_hidden", str(interaction.user.id), 1 if perms.view_channel == False else 0)
            cog = interaction.client.get_cog("PrivateVoice")
            if cog: await cog.log_oda_update(interaction, "Oda gizlendi" if perms.view_channel == False else "Oda görünür yapıldı")
        except Exception as e:
            err_msg = f"❌ Bir hata oluştu: {type(e).__name__} - {str(e)}"
            if getattr(e, 'status', None) == 429:
                err_msg = "❌ Discord API limitine takıldınız. Lütfen biraz bekleyin."
            if not interaction.response.is_done():
                await interaction.response.send_message(err_msg, ephemeral=True)
            else:
                await interaction.followup.send(err_msg, ephemeral=True)

    @discord.ui.button(label="İsim Değiştir", style=discord.ButtonStyle.primary, emoji="✏️", row=1, custom_id="pv_rename")
    async def rename_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RenameModal())

    @discord.ui.button(label="Kişi Limiti", style=discord.ButtonStyle.secondary, emoji="👥", row=1, custom_id="pv_limit")
    async def limit_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LimitModal())

    @discord.ui.button(label="Ses Kalitesi (64kbps)", style=discord.ButtonStyle.secondary, emoji="📊", row=1, custom_id="pv_bitrate")
    async def bitrate_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_bitrate = interaction.channel.bitrate
        max_bitrate = interaction.guild.bitrate_limit
        next_bitrate = current_bitrate + 32000
        if next_bitrate > max_bitrate:
            next_bitrate = 64000
            
        await interaction.channel.edit(bitrate=next_bitrate)
        button.label = f"Ses Kalitesi ({next_bitrate//1000}kbps)"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"Ses kalitesi {next_bitrate//1000}kbps olarak ayarlandı.", ephemeral=True)
        await interaction.client.db.execute("INSERT INTO private_voice_settings (user_id, bitrate) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET bitrate=excluded.bitrate", str(interaction.user.id), next_bitrate)
        cog = interaction.client.get_cog("PrivateVoice")
        if cog: await cog.log_oda_update(interaction, f"Ses kalitesi değiştirildi: {next_bitrate//1000}kbps")

    @discord.ui.button(label="Üye Çıkar", style=discord.ButtonStyle.danger, emoji="👢", row=2, custom_id="pv_kick")
    async def kick_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        members = [m for m in interaction.channel.members if m.id != interaction.user.id]
        if not members:
            return await interaction.response.send_message("Odada çıkarılacak başka üye yok.", ephemeral=True)
            
        view = discord.ui.View()
        view.add_item(MemberKickSelect(members))
        await interaction.response.send_message("Odadan kimi çıkarmak istiyorsunuz?", view=view, ephemeral=True)

    @discord.ui.button(label="Odayı Devret", style=discord.ButtonStyle.primary, emoji="👑", row=2, custom_id="pv_transfer")
    async def transfer_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        members = [m for m in interaction.channel.members if m.id != interaction.user.id]
        if not members:
            return await interaction.response.send_message("Odada devredecek başka üye yok.", ephemeral=True)
            
        view = discord.ui.View()
        view.add_item(MemberTransferSelect(members))
        await interaction.response.send_message("Odayı kime devretmek istiyorsunuz?", view=view, ephemeral=True)


class PrivateVoice(commands.Cog):
    category = "Eğlence ve Araçlar"
    category_emoji = "🛠️"
    
    def __init__(self, bot):
        self.bot = bot
        self.cleanup_empty_rooms.start()
        self.creation_locks = set()

    async def cog_load(self):
        pass

    def cog_unload(self):
        self.cleanup_empty_rooms.cancel()

    async def get_log_settings(self, guild: discord.Guild) -> tuple[discord.TextChannel | None, dict | None]:
        row = await self.bot.db.fetchone("SELECT oda_channel, oda_create_on, oda_delete_on, oda_update_on FROM log_settings WHERE guild_id=?", str(guild.id))
        settings = dict(row) if row else None
        if not settings or not settings.get("oda_channel"): return None, None
        try: 
            channel = guild.get_channel(int(settings["oda_channel"])) or await guild.fetch_channel(int(settings["oda_channel"]))
            return channel, settings
        except: return None, None

    async def log_oda_update(self, interaction: discord.Interaction, action: str):
        log_channel, settings = await self.get_log_settings(interaction.guild)
        db_details = {
            "username": interaction.user.name,
            "avatar_url": interaction.user.display_avatar.url if interaction.user.display_avatar else None,
            "text": f"Oda güncellendi: {interaction.channel.name}\nİşlem: {action}"
        }
        await self.bot.db.log_db_event(interaction.guild.id, "oda_update", "oda_update_on", str(interaction.user.id), db_details, channel_id=str(interaction.channel.id))
        
        if log_channel and settings and settings.get("oda_update_on"):
            row = await self.bot.db.fetchone("SELECT log_message_id FROM private_voice_rooms WHERE channel_id=?", str(interaction.channel.id))
            if not row or not row[0]: return
            
            try:
                msg = await log_channel.fetch_message(int(row[0]))
                embed = msg.embeds[0] if msg.embeds else None
                if not embed or len(embed.fields) < 2: return
                
                # Ayarlar geçmişi field'ı ilk sırada (0. index)
                history_field = embed.fields[0]
                lines = history_field.value.split("\n")
                t_str = f"<t:{int(discord.utils.utcnow().timestamp())}:t>"
                lines.append(f"`[{t_str}]` ⚙️ {action}")
                
                # Embed karakter sınırını aşmamak için son 10 logu tut
                if len(lines) > 10:
                    lines = lines[-10:]
                
                embed.set_field_at(0, name="Oda Ayarları Geçmişi", value="\n".join(lines), inline=False)
                await msg.edit(embed=embed)
            except discord.NotFound:
                pass
            except Exception as e:
                log.error(f"Master Embed güncellenemedi (oda_update): {e}")

    @tasks.loop(minutes=5)
    async def cleanup_empty_rooms(self):
        if not hasattr(self.bot, 'db'): return
        try:
            # 1. DB'de olan odaları kontrol et
            rooms = await self.bot.db.fetchall("SELECT channel_id FROM private_voice_rooms")
            for row in rooms:
                channel_id = int(row[0])
                channel = self.bot.get_channel(channel_id)
                if channel:
                    if len(channel.members) == 0:
                        try:
                            await channel.delete(reason="Sistem Taraması: Boş oda silindi")
                            await self.bot.db.execute("DELETE FROM private_voice_rooms WHERE channel_id=?", str(channel_id))
                        except Exception:
                            pass
                else:
                    await self.bot.db.execute("DELETE FROM private_voice_rooms WHERE channel_id=?", str(channel_id))
            
            # 2. Yetim odaları (DB'de olmayan ama kategoride olan) temizle
            hubs = await self.bot.db.fetchall("SELECT category_id, hub_id FROM private_voice_hubs")
            for row in hubs:
                category_id, hub_id = str(row[0]), str(row[1])
                category = self.bot.get_channel(int(category_id))
                if category:
                    for channel in category.voice_channels:
                        if str(channel.id) != hub_id:
                            if len(channel.members) == 0:
                                try:
                                    await channel.delete(reason="Sistem Taraması: Boş oda silindi (Yetim)")
                                    await self.bot.db.execute("DELETE FROM private_voice_rooms WHERE channel_id=?", str(channel.id))
                                except Exception as e:
                                    log.warning(f"Oda silinemedi: {e}")
        except Exception as e:
            log.error(f"Boş oda temizliği sırasında hata: {e}")

    @cleanup_empty_rooms.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

    @commands.command(name="oda-kurulum")
    @kumiho_check(default_access="owner")
    async def oda_kurulum(self, ctx, hub_channel: discord.VoiceChannel = None, category: discord.CategoryChannel = None):
        """Setup the private voice channels system.\n\n**Usage:** `{prefix}oda-kurulum`"""
        if not hub_channel or not category:
            category = await ctx.guild.create_category("🎙️ Özel Odalar", reason="Özel Ses Odası Kurulumu")
            hub_channel = await category.create_voice_channel("➕ Oda Oluştur", reason="Özel Ses Odası Kurulumu")
        
        try:
            await self.bot.db.execute("INSERT OR REPLACE INTO private_voice_hubs (guild_id, category_id, hub_id) VALUES (?, ?, ?)", 
                                      str(ctx.guild.id), str(category.id), str(hub_channel.id))
            
            embed = discord.Embed(
                title="✅ Özel Oda Sistemi Kuruldu",
                description=f"Başarıyla {category.mention} kategorisi ve {hub_channel.mention} kanalı oluşturuldu.\n\nKullanıcılar bu kanala girerek kendi geçici ses odalarını oluşturabilirler.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            log.error(f"oda-kurulum komutunda hata: {e}")
            await ctx.send(f"❌ Veritabanı hatası oluştu: `{e}`")

    async def update_live_data(self, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if not channel: return
        
        members_data = []
        for m in channel.members:
            if not m.voice: continue
            members_data.append({
                "id": str(m.id),
                "name": m.display_name,
                "avatar": m.display_avatar.url if m.display_avatar else None,
                "video": m.voice.self_video,
                "stream": m.voice.self_stream,
                "mute": m.voice.self_mute,
                "deaf": m.voice.self_deaf
            })
        
        live_info = {
            "user_limit": channel.user_limit,
            "bitrate": channel.bitrate,
            "members": members_data
        }
        
        import json
        await self.bot.db.execute("UPDATE private_voice_rooms SET live_data=? WHERE channel_id=?", json.dumps(live_info), str(channel_id))

    async def append_master_embed_timeline(self, channel_id: int, action_type: str, text: str):
        row = await self.bot.db.fetchone("SELECT log_message_id FROM private_voice_rooms WHERE channel_id=?", str(channel_id))
        if not row or not row[0]: return
        
        channel = self.bot.get_channel(channel_id)
        if not channel: return
        
        log_channel, settings = await self.get_log_settings(channel.guild)
        if not log_channel: return
        
        try:
            msg = await log_channel.fetch_message(int(row[0]))
            embed = msg.embeds[0] if msg.embeds else None
            if not embed or len(embed.fields) < 2: return
            
            field_idx = 0 if action_type == "settings" else 1
            field_name = embed.fields[field_idx].name
            lines = embed.fields[field_idx].value.split("\n")
            
            t_str = f"<t:{int(discord.utils.utcnow().timestamp())}:t>"
            lines.append(f"`[{t_str}]` {text}")
            
            if len(lines) > 10:
                lines = lines[-10:]
                
            embed.set_field_at(field_idx, name=field_name, value="\n".join(lines), inline=False)
            
            view = AdminVoicePanelView()
            if action_type == "delete":
                embed.color = discord.Color.red()
                view = None
                
            await msg.edit(embed=embed, view=view)
        except:
            pass

    async def log_participant_event(self, guild_id: int, user: discord.Member, channel_id: int, action_text: str):
        db_details = {
            "username": user.name,
            "avatar_url": user.display_avatar.url if user.display_avatar else None,
            "text": action_text
        }
        # oda_update_on ayarını referans alıyoruz
        await self.bot.db.log_db_event(guild_id, "oda_participant", "oda_update_on", str(user.id), db_details, channel_id=str(channel_id))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Durum değişiklikleri (Aynı odada kamera/yayın açma kapama vb.)
        if before.channel and after.channel and before.channel.id == after.channel.id:
            row = await self.bot.db.fetchone("SELECT channel_id FROM private_voice_rooms WHERE channel_id=?", str(after.channel.id))
            if row:
                if before.self_video != after.self_video:
                    action = "📹 Kamerasını açtı." if after.self_video else "📵 Kamerasını kapattı."
                    await self.append_master_embed_timeline(after.channel.id, "participants", f"{member.mention} {action}")
                    await self.log_participant_event(member.guild.id, member, after.channel.id, action)
                if before.self_stream != after.self_stream:
                    action = "📺 Ekran yayını açtı." if after.self_stream else "🚫 Yayını kapattı."
                    await self.append_master_embed_timeline(after.channel.id, "participants", f"{member.mention} {action}")
                    await self.log_participant_event(member.guild.id, member, after.channel.id, action)
            return

        # 1. Odadan Çıkış (Oda Silme Kontrolü)
        if before.channel:
            row = await self.bot.db.fetchone("SELECT owner_id FROM private_voice_rooms WHERE channel_id=?", str(before.channel.id))
            if row:
                members_in_channel = [m for m in before.channel.members if m.id != member.id]
                
                # Odadan çıkış logu
                if after.channel is None or after.channel.id != before.channel.id:
                    action = "🚪 Odadan ayrıldı."
                    await self.append_master_embed_timeline(before.channel.id, "participants", f"🚪 {member.mention} odadan ayrıldı.")
                    await self.log_participant_event(member.guild.id, member, before.channel.id, action)
                
                if len(members_in_channel) == 0:
                    try:
                        owner_id = int(row[0])
                        channel_name = before.channel.name
                        channel_id_str = str(before.channel.id)
                        
                        await self.append_master_embed_timeline(before.channel.id, "delete", f"🛑 Oda kapatıldı.")
                        
                        await before.channel.delete(reason="Oda boşaldı")
                        await self.bot.db.execute("DELETE FROM private_voice_rooms WHERE channel_id=?", channel_id_str)
                        
                        # Klasik Log Event (Dashboard için)
                        db_details = {
                            "username": member.name,
                            "avatar_url": member.display_avatar.url if member.display_avatar else None,
                            "text": f"Oda silindi: {channel_name}"
                        }
                        await self.bot.db.log_db_event(member.guild.id, "oda_delete", "oda_delete_on", str(member.id), db_details, channel_id=channel_id_str)
                    except discord.NotFound:
                        await self.bot.db.execute("DELETE FROM private_voice_rooms WHERE channel_id=?", str(before.channel.id))
                    except discord.HTTPException as e:
                        log.warning(f"Oda silinemedi (Discord Hatası): {e}")

        # 2. Odaya Giriş (Timeline ekleme ve Oda Oluşturma)
        if after.channel:
            # Mevcut odaya giriş yaptıysa logla
            if before.channel is None or before.channel.id != after.channel.id:
                row = await self.bot.db.fetchone("SELECT owner_id FROM private_voice_rooms WHERE channel_id=?", str(after.channel.id))
                if row and str(row[0]) != str(member.id): # Kuran kişiyi 'Odaya girdi' diye iki kere yazmamak için
                    action = "📥 Odaya katıldı."
                    await self.append_master_embed_timeline(after.channel.id, "participants", f"📥 {member.mention} odaya katıldı.")
                    await self.log_participant_event(member.guild.id, member, after.channel.id, action)
            hub_row = await self.bot.db.fetchone("SELECT category_id, hub_id FROM private_voice_hubs WHERE guild_id=?", str(member.guild.id))
            if hub_row:
                category_id, hub_id = hub_row
                if str(after.channel.id) == str(hub_id):
                    # Kilit Sistemi (Spam Engelleme)
                    if member.id in self.creation_locks:
                        return
                    self.creation_locks.add(member.id)
                    
                    try:
                        # KULLANICININ ZATEN ODASI VAR MI KONTROL ET
                        old_room_row = await self.bot.db.fetchone("SELECT channel_id FROM private_voice_rooms WHERE owner_id=?", str(member.id))
                        if old_room_row:
                            old_room_id = int(old_room_row[0])
                            old_room = member.guild.get_channel(old_room_id)
                            if old_room:
                                try:
                                    await member.move_to(old_room)
                                except Exception:
                                    pass
                                return  # Kullanıcıyı eski odasına taşı ve yeni oda açmayı iptal et!
                            else:
                                # Oda discord'dan silinmiş ama DB'de kalmışsa temizle
                                await self.bot.db.execute("DELETE FROM private_voice_rooms WHERE channel_id=?", str(old_room_id))
                                
                        # Kullanıcının geçmiş ayarlarını çek
                        settings = await self.bot.db.fetchone("SELECT * FROM private_voice_settings WHERE user_id=?", str(member.id))
                        
                        room_name = f"{member.display_name}'in Odası"
                        user_limit = 0
                        bitrate = 64000
                        is_locked = False
                        is_hidden = False
                        
                        if settings:
                            room_name = settings[1] or room_name
                            user_limit = settings[2] or 0
                            bitrate = settings[3] or 64000
                            is_locked = bool(settings[4])
                            is_hidden = bool(settings[5])
                            
                        try:
                            category = member.guild.get_channel(int(category_id))
                            
                            # Kategori yetkilerini taban (base) olarak al, böylece bot'un veya diğer rollerin yetkileri kaybolmaz
                            overwrites = dict(category.overwrites) if category else {}
                            
                            # Bot için gerekli yetkileri garantiye al (view_channel kör olmamak için çok kritik!)
                            bot_ow = overwrites.get(member.guild.me, discord.PermissionOverwrite())
                            bot_ow.update(view_channel=True, connect=True)
                            overwrites[member.guild.me] = bot_ow

                            # Oda sahibi (member) için yetkiler
                            member_ow = overwrites.get(member, discord.PermissionOverwrite())
                            member_ow.update(view_channel=True, connect=True)
                            overwrites[member] = member_ow

                            # Kilit veya gizlilik ayarları varsa @everyone yetkisini güncelle
                            if is_locked or is_hidden:
                                ev_ow = overwrites.get(member.guild.default_role, discord.PermissionOverwrite())
                                if is_locked: ev_ow.connect = False
                                if is_hidden: ev_ow.view_channel = False
                                overwrites[member.guild.default_role] = ev_ow

                            new_channel = await member.guild.create_voice_channel(
                                name=room_name,
                                category=category,
                                user_limit=user_limit,
                                bitrate=min(bitrate, member.guild.bitrate_limit),
                                overwrites=overwrites,
                                reason="Özel Ses Odası Oluşturuldu"
                            )
                            
                            await self.bot.db.execute("INSERT INTO private_voice_rooms (channel_id, owner_id) VALUES (?, ?)", str(new_channel.id), str(member.id))
                            
                            # Log Event & Master Embed
                            log_channel, settings = await self.get_log_settings(member.guild)
                            if log_channel and settings and settings.get("oda_create_on"):
                                embed = discord.Embed(
                                    title=f"🎙️ Özel Ses Odası: {room_name}",
                                    color=discord.Color.green(),
                                    timestamp=discord.utils.utcnow()
                                )
                                embed.set_author(name=member.display_name, icon_url=member.display_avatar.url if member.display_avatar else None)
                                
                                # Timelines
                                t_str = f"<t:{int(discord.utils.utcnow().timestamp())}:t>"
                                embed.add_field(name="Oda Ayarları Geçmişi", value=f"`[{t_str}]` ✨ Odayı kurdu.", inline=False)
                                embed.add_field(name="Katılımcı Hareketleri", value=f"`[{t_str}]` 🏃 Odaya girdi.", inline=False)
                                embed.set_footer(text=f"Oda ID: {new_channel.id}")
                                
                                try: 
                                    msg = await log_channel.send(embed=embed, view=AdminVoicePanelView())
                                    await self.bot.db.execute("UPDATE private_voice_rooms SET log_message_id=? WHERE channel_id=?", str(msg.id), str(new_channel.id))
                                except Exception as e: 
                                    log.error(f"Master Embed gönderilemedi: {e}")
                            
                            try:
                                await member.move_to(new_channel)
                            except Exception as e:
                                log.warning(f"Kullanıcı yeni odaya taşınamadı (İzole edildi/DC yedi): {e}")
                                # Hayalet odayı anında temizle!
                                await new_channel.delete(reason="Kullanıcı odaya girmediği için iptal edildi.")
                                await self.bot.db.execute("DELETE FROM private_voice_rooms WHERE channel_id=?", str(new_channel.id))
                                return
                        
                            # Kontrol Panelini Gönder
                            view = PrivateVoiceView()
                            
                            # Ses Kalitesi butonunu güncelle
                            for child in view.children:
                                if isinstance(child, discord.ui.Button) and child.custom_id == "pv_bitrate":
                                    child.label = f"Ses Kalitesi ({new_channel.bitrate//1000}kbps)"
                                elif isinstance(child, discord.ui.Button) and child.custom_id == "pv_lock" and is_locked:
                                    child.style = discord.ButtonStyle.success
                                    child.label = "Kilidi Aç"
                                elif isinstance(child, discord.ui.Button) and child.custom_id == "pv_hide" and is_hidden:
                                    child.style = discord.ButtonStyle.success
                                    child.label = "Odayı Göster"

                            embed = discord.Embed(
                                title="🎛️ Oda Kontrol Paneli",
                                description=f"Hoş geldin, {member.mention}! Odanı aşağıdaki butonları kullanarak yönetebilirsin. Değişiklikler kaydedilecek ve odayı bir sonraki açışında geçerli olacaktır.",
                                color=discord.Color.dark_theme()
                            )
                            
                            # API'nin kanal metin altyapısını hazırlaması için kısa gecikme
                            await asyncio.sleep(0.5)
                            try:
                                await new_channel.send(embed=embed, view=view)
                            except Exception as e:
                                log.error(f"Kontrol paneli gönderilemedi: {e}")
                            # Eski ayar blokları create_voice_channel içine taşındı.
                        except discord.HTTPException as e:
                            if e.status == 400 and e.code == 50024: # Cannot create channel, max limit
                                log.warning(f"Kategori oda limiti doldu: {member.guild.id}")
                                try:
                                    await member.send("❌ Özel oda oluşturulamadı! Kategori tamamen dolu (Maks. 50 Oda). Lütfen daha sonra tekrar deneyin.")
                                except discord.Forbidden:
                                    pass
                                try:
                                    await member.move_to(None) # Hub'dan çıkar
                                except Exception:
                                    pass
                            else:
                                log.error(f"Oda oluşturulurken HTTP hatası: {e}")
                        except Exception as e:
                            log.error(f"Oda oluşturulurken hata: {e}")
                    
                    finally:
                        self.creation_locks.discard(member.id)

async def setup(bot):
    await bot.add_cog(PrivateVoice(bot))

