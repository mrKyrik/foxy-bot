import discord
from discord.ext import commands, tasks
import logging
import asyncio
from core.checks import kumiho_check

log = logging.getLogger("Commands.private_voice")

class RenameModal(discord.ui.Modal, title='Oda İsmini Değiştir'):
    name_input = discord.ui.TextInput(
        label='Yeni Oda İsmi',
        style=discord.TextStyle.short,
        placeholder='Örn: Sohbet Odası',
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.channel.edit(name=self.name_input.value)
            await interaction.client.db.execute("INSERT INTO private_voice_settings (user_id, room_name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET room_name=excluded.room_name", str(interaction.user.id), self.name_input.value)
            await interaction.response.send_message(f"Oda ismi `{self.name_input.value}` olarak değiştirildi.", ephemeral=True)
        except discord.HTTPException as e:
            if e.status == 429:
                await interaction.response.send_message("❌ Çok hızlı isim değiştirdiniz! Discord kanal ismi değiştirme limitine takıldınız (10 dakikada 2 kez). Lütfen bekleyin.", ephemeral=True)
            else:
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
        except discord.HTTPException as e:
            if e.status == 429:
                await interaction.response.send_message("❌ Limit aşımı! Lütfen işlemi tekrarlamadan önce biraz bekleyin.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ İşlem başarısız oldu.", ephemeral=True)

class MemberKickSelect(discord.ui.Select):
    def __init__(self, members):
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
        await interaction.client.db.execute("UPDATE private_voice_rooms SET owner_id=? WHERE channel_id=?", str(member_id), str(interaction.channel.id))
        await interaction.response.send_message(f"Oda sahipliği <@{member_id}> kullanıcısına devredildi.", ephemeral=True)

class WhitelistSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="✅ İzin Verilenleri (Whitelist) Seç", min_values=1, max_values=10, row=3, custom_id="pv_whitelist")

    async def callback(self, interaction: discord.Interaction):
        for user in self.values:
            await interaction.channel.set_permissions(user, connect=True, view_channel=True)
        await interaction.response.send_message(f"{len(self.values)} kullanıcıya odaya giriş izni verildi.", ephemeral=True)

class BanlistSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="⛔ Yasaklananları (Banlist) Seç", min_values=1, max_values=10, row=4, custom_id="pv_banlist")

    async def callback(self, interaction: discord.Interaction):
        for user in self.values:
            await interaction.channel.set_permissions(user, connect=False, view_channel=False)
            if isinstance(user, discord.Member) and user in interaction.channel.members:
                await user.move_to(None)
        await interaction.response.send_message(f"{len(self.values)} kullanıcı odadan yasaklandı.", ephemeral=True)


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
        role = interaction.guild.default_role
        perms = interaction.channel.overwrites_for(role)
        try:
            if perms.connect == False:
                perms.connect = None
                button.style = discord.ButtonStyle.danger
                button.label = "Odayı Kilitle"
                await interaction.channel.set_permissions(role, overwrite=perms)
                await interaction.response.edit_message(view=self)
                await interaction.followup.send("Oda kilidi açıldı.", ephemeral=True)
            else:
                perms.connect = False
                button.style = discord.ButtonStyle.success
                button.label = "Kilidi Aç"
                await interaction.channel.set_permissions(role, overwrite=perms)
                await interaction.response.edit_message(view=self)
                await interaction.followup.send("Oda kilitlendi.", ephemeral=True)
            await interaction.client.db.execute("INSERT INTO private_voice_settings (user_id, is_locked) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET is_locked=excluded.is_locked", str(interaction.user.id), 1 if perms.connect == False else 0)
        except discord.HTTPException:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Discord API limitine takıldınız. Lütfen biraz bekleyip tekrar deneyin.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Discord API limitine takıldınız. Lütfen biraz bekleyin.", ephemeral=True)

    @discord.ui.button(label="Odayı Gizle", style=discord.ButtonStyle.secondary, emoji="👻", row=0, custom_id="pv_hide")
    async def hide_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.default_role
        perms = interaction.channel.overwrites_for(role)
        if perms.view_channel == False:
            perms.view_channel = None
            button.style = discord.ButtonStyle.secondary
            button.label = "Odayı Gizle"
            await interaction.channel.set_permissions(role, overwrite=perms)
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("Oda artık herkese görünür.", ephemeral=True)
        else:
            perms.view_channel = False
            button.style = discord.ButtonStyle.success
            button.label = "Odayı Göster"
            await interaction.channel.set_permissions(role, overwrite=perms)
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("Oda gizlendi.", ephemeral=True)
        await interaction.client.db.execute("INSERT INTO private_voice_settings (user_id, is_hidden) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET is_hidden=excluded.is_hidden", str(interaction.user.id), 1 if perms.view_channel == False else 0)

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
    
    def __init__(self, bot):
        self.bot = bot
        self.cleanup_empty_rooms.start()

    def cog_unload(self):
        self.cleanup_empty_rooms.cancel()

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
        if not hub_channel or not category:
            category = await ctx.guild.create_category("🎙️ Özel Odalar", reason="Özel Ses Odası Kurulumu")
            hub_channel = await category.create_voice_channel("➕ Oda Oluştur", reason="Özel Ses Odası Kurulumu")
        
        await self.bot.db.execute("INSERT OR REPLACE INTO private_voice_hubs (guild_id, category_id, hub_id) VALUES (?, ?, ?)", 
                                  str(ctx.guild.id), str(category.id), str(hub_channel.id))
        
        embed = discord.Embed(
            title="✅ Özel Oda Sistemi Kuruldu",
            description=f"Başarıyla {category.mention} kategorisi ve {hub_channel.mention} kanalı oluşturuldu.\n\nKullanıcılar bu kanala girerek kendi geçici ses odalarını oluşturabilirler.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # 1. Odadan Çıkış (Oda Silme Kontrolü)
        if before.channel:
            row = await self.bot.db.fetchone("SELECT owner_id FROM private_voice_rooms WHERE channel_id=?", str(before.channel.id))
            if row:
                members_in_channel = [m for m in before.channel.members if m.id != member.id]
                if len(members_in_channel) == 0:
                    try:
                        await before.channel.delete(reason="Oda boşaldı")
                        await self.bot.db.execute("DELETE FROM private_voice_rooms WHERE channel_id=?", str(before.channel.id))
                    except discord.NotFound:
                        await self.bot.db.execute("DELETE FROM private_voice_rooms WHERE channel_id=?", str(before.channel.id))
                    except discord.HTTPException as e:
                        log.warning(f"Oda silinemedi (Discord Hatası): {e}")

        # 2. Odaya Giriş (Oda Oluşturma)
        if after.channel:
            hub_row = await self.bot.db.fetchone("SELECT category_id, hub_id FROM private_voice_hubs WHERE guild_id=?", str(member.guild.id))
            if hub_row:
                category_id, hub_id = hub_row
                if str(after.channel.id) == str(hub_id):
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
                        # (user_id, room_name, user_limit, bitrate, is_locked, is_hidden, whitelist, banlist)
                        room_name = settings[1] or room_name
                        user_limit = settings[2] or 0
                        bitrate = settings[3] or 64000
                        is_locked = bool(settings[4])
                        is_hidden = bool(settings[5])
                        
                    try:
                        category = member.guild.get_channel(int(category_id))
                        new_channel = await member.guild.create_voice_channel(
                            name=room_name,
                            category=category,
                            user_limit=user_limit,
                            bitrate=min(bitrate, member.guild.bitrate_limit),
                            reason="Özel Ses Odası Oluşturuldu"
                        )
                        
                        await self.bot.db.execute("INSERT INTO private_voice_rooms (channel_id, owner_id) VALUES (?, ?)", str(new_channel.id), str(member.id))
                        
                        try:
                            await member.move_to(new_channel)
                        except Exception as e:
                            log.warning(f"Kullanıcı yeni odaya taşınamadı (İzole edildi): {e}")
                            
                        # Kullanıcıya kendi odasında açıkça (explicit) yetki ver ki odayı kilitlediğinde kendisi de kilitli kalmasın
                        await new_channel.set_permissions(member, connect=True, view_channel=True)
                    
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
                        
                        # Önceki ayarları uygula (Kilit vs)
                        if is_locked or is_hidden:
                            role = member.guild.default_role
                            perms = new_channel.overwrites_for(role)
                            if is_locked:
                                perms.connect = False
                            if is_hidden:
                                perms.view_channel = False
                            await new_channel.set_permissions(role, overwrite=perms)
                            
                    except Exception as e:
                        log.error(f"Oda oluşturulurken hata: {e}")

async def setup(bot):
    await bot.add_cog(PrivateVoice(bot))
    bot.add_view(PrivateVoiceView())
