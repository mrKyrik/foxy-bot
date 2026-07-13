from __future__ import annotations
import logging
import discord
import time
from discord.ext import commands

log = logging.getLogger(__name__)

class VoiceEvents(commands.Cog):
    """Sese giriş/çıkış, kanal değiştirme ve süre hesaplamalarını yapıp loglar."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.sessions = {} # {member_id: join_timestamp}

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if getattr(self, "voice_synced", False):
            return
        self.voice_synced = True

        log.info("Ses kanalları taranıyor ve senkronize ediliyor...")
        events = []
        for guild in self.bot.guilds:
            # Şalter kontrolü
            if hasattr(self.bot, "db"):
                db_row = await self.bot.db.fetchone("SELECT * FROM db_log_settings WHERE guild_id=?", str(guild.id))
                if db_row and dict(db_row).get("ses_join_on") == 0:
                    continue

            for channel in guild.voice_channels:
                for member in channel.members:
                    if member.bot: continue
                    self.sessions[member.id] = time.time()
                    
                    if hasattr(self.bot, "db"):
                        await self.bot.db.update_user_cache(str(member.id), member.name, member.display_avatar.url)
                        await self.bot.db.update_channel_cache(str(guild.id), str(channel.id), channel.name)

                    details = {
                        "username": str(member.name),
                        "avatar_url": member.display_avatar.url if member.display_avatar else None,
                        "text": f"Kanala Katıldı (Senkronizasyon): <#{channel.id}>"
                    }
                    events.append((
                        guild.id,
                        "ses_join",
                        str(member.id),
                        details,
                        str(channel.id)
                    ))
                    
        if events and hasattr(self.bot.db, "log_db_events_bulk"):
            await self.bot.db.log_db_events_bulk(events)
            log.info(f"{len(events)} üyenin ses durumu senkronize edildi.")

    async def get_log_settings(self, guild: discord.Guild) -> tuple[discord.TextChannel | None, dict | None]:
        row = await self.bot.db.fetchone("SELECT ses_channel, ses_join_on, ses_switch_on, ses_stream_on FROM log_settings WHERE guild_id=?", str(guild.id))
        settings = dict(row) if row else None
        if not settings or not settings.get("ses_channel"): return None, None
        try: 
            channel = guild.get_channel(int(settings["ses_channel"])) or await guild.fetch_channel(int(settings["ses_channel"]))
            return channel, settings
        except: return None, None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        if member.bot: return
        
        # Kullanıcı adını ve resmini güncelle
        await self.bot.db.update_user_cache(str(member.id), member.name, member.display_avatar.url)

        log_channel, settings = await self.get_log_settings(member.guild)
        send_embed = bool(log_channel and settings)

        embed = discord.Embed(timestamp=discord.utils.utcnow())
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)

        # 1. Join (Kanala Giriş)
        if before.channel is None and after.channel is not None:
            self.sessions[member.id] = time.time()
            
            # Kanal adını önbelleğe al
            await self.bot.db.update_channel_cache(str(member.guild.id), str(after.channel.id), after.channel.name)
            
            # DB Log
            db_details = {
                "username": str(member.name),
                "avatar_url": member.display_avatar.url if member.display_avatar else None,
                "text": f"Kanala Katıldı: <#{after.channel.id}>"
            }
            await self.bot.db.log_db_event(member.guild.id, "ses_join", "ses_join_on", str(member.id), db_details, channel_id=str(after.channel.id))
            
            if send_embed and settings["ses_join_on"]:
                embed.title = "🔊 Ses Kanalına Katıldı"
                embed.color = discord.Color.green()
                embed.description = f"**Kullanıcı:** {member.mention} (`{member.id}`)\n**Kanal:** {after.channel.mention}"
                try: await log_channel.send(embed=embed)
                except discord.Forbidden: pass

        # 2. Leave (Kanaldan Çıkış)
        elif before.channel is not None and after.channel is None:
            join_time = self.sessions.pop(member.id, None)
            duration_str = "Bilinmiyor"
            if join_time:
                diff = int(time.time() - join_time)
                mins, secs = divmod(diff, 60)
                hours, mins = divmod(mins, 60)
                duration_str = f"{hours}s {mins}d {secs}sn" if hours > 0 else f"{mins}dk {secs}sn"
                
            # DB Log
            db_details = {
                "username": str(member.name),
                "avatar_url": member.display_avatar.url if member.display_avatar else None,
                "duration": duration_str,
                "text": f"Kanaldan Ayrıldı: <#{before.channel.id}>\nSüre: {duration_str}"
            }
            await self.bot.db.log_db_event(member.guild.id, "ses_leave", "ses_join_on", str(member.id), db_details, channel_id=str(before.channel.id))
                
            if send_embed and settings["ses_join_on"]:
                embed.title = "🔇 Ses Kanalından Ayrıldı"
                embed.color = discord.Color.red()
                embed.description = f"**Kullanıcı:** {member.mention} (`{member.id}`)\n**Kanal:** {before.channel.mention}\n**⏳ Seste Kalma Süresi:** {duration_str}"
                try: await log_channel.send(embed=embed)
                except discord.Forbidden: pass

        # 3. Switch (Kanal Değiştirme)
        elif before.channel and after.channel and before.channel != after.channel:
            # Kanal adlarını önbelleğe al
            await self.bot.db.update_channel_cache(str(member.guild.id), str(before.channel.id), before.channel.name)
            await self.bot.db.update_channel_cache(str(member.guild.id), str(after.channel.id), after.channel.name)
            
            # Hem eski kanaldan leave hem yeni kanala join olarak switch eventiyle logla
            db_details_leave = {
                "username": str(member.name),
                "avatar_url": member.display_avatar.url if member.display_avatar else None,
                "text": f"Kanal Değiştirdi (Ayrıldı): <#{before.channel.id}>"
            }
            db_details_join = {
                "username": str(member.name),
                "avatar_url": member.display_avatar.url if member.display_avatar else None,
                "text": f"Kanal Değiştirdi (Katıldı): <#{after.channel.id}>"
            }
            await self.bot.db.log_db_event(member.guild.id, "ses_switch_leave", "ses_join_on", str(member.id), db_details_leave, channel_id=str(before.channel.id))
            await self.bot.db.log_db_event(member.guild.id, "ses_switch_join", "ses_join_on", str(member.id), db_details_join, channel_id=str(after.channel.id))
            
            if send_embed and settings["ses_switch_on"]:
                embed.title = "🔀 Ses Kanalı Değiştirildi"
                embed.color = discord.Color.blue()
                embed.description = f"**Kullanıcı:** {member.mention} (`{member.id}`)\n**Eski Kanal:** {before.channel.mention}\n**Yeni Kanal:** {after.channel.mention}"
                try: await log_channel.send(embed=embed)
                except discord.Forbidden: pass

        # 3. Stream / Camera (Ekran ve Kamera)
        channel_id = str(after.channel.id) if after.channel else (str(before.channel.id) if before.channel else None)
        if not channel_id: return

        if before.self_stream != after.self_stream:
            # Duruma göre açık veya kapalı eventi
            event_name = "ses_stream_on" if after.self_stream else "ses_stream_off"
            durum = "açtı" if after.self_stream else "kapattı"
            
            # DB Log
            db_details = {
                "username": str(member.name),
                "avatar_url": member.display_avatar.url if member.display_avatar else None,
                "text": f"Ekran Paylaşımı {durum}: <#{channel_id}>"
            }
            await self.bot.db.log_db_event(member.guild.id, event_name, "ses_stream_on", str(member.id), db_details, channel_id=channel_id)
            
            if send_embed and settings.get("ses_stream_on"):
                embed.title = f"📺 Ekran Paylaşımı {'Açıldı' if after.self_stream else 'Kapandı'}"
                embed.color = discord.Color.purple()
                embed.description = f"**Kullanıcı:** {member.mention}\n**Kanal:** <#{channel_id}>"
                try: await log_channel.send(embed=embed)
                except discord.Forbidden: pass

        if before.self_video != after.self_video:
            action = "Kamera açtı" if after.self_video else "Kamera kapattı"
            evt_type = "ses_camera_on" if after.self_video else "ses_camera_off"
            db_details = {
                "username": str(member.name),
                "avatar_url": member.display_avatar.url if member.display_avatar else None,
                "text": f"{action}: <#{channel_id}>"
            }
            await self.bot.db.log_db_event(member.guild.id, evt_type, "ses_camera_on", str(member.id), db_details, channel_id=channel_id)
            
            if send_embed and settings.get("ses_camera_on"):
                embed.title = f"📷 Kamera {'Açıldı' if after.self_video else 'Kapandı'}"
                embed.color = discord.Color.teal()
                embed.description = f"**Kullanıcı:** {member.mention}\n**Kanal:** <#{channel_id}>"
                try: await log_channel.send(embed=embed)
                except discord.Forbidden: pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceEvents(bot))
