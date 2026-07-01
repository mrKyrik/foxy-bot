import logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

class RoleSync(commands.Cog):
    """Rol Senkronizasyonu"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="sync_roles", aliases=["rol_senkronize", "rolesync"])
    async def sync_roles(self, ctx: commands.Context) -> None:
        """Sunucudaki tüm üyelerin mevcut rollerini Web UI için senkronize eder."""
        import os
        owner_ids = [x.strip() for x in (os.getenv("OWNER_ID") or "").split(",") if x.strip()]
        is_owner = str(ctx.author.id) in owner_ids or ctx.author.id == 601344424429092864
        if not (ctx.author.guild_permissions.administrator or is_owner):
            raise commands.CheckFailure("Yönetici yetkisi")

        msg = await ctx.send("🔄 Üye rolleri taranıyor, lütfen bekleyin... (Bu işlem sunucu büyüklüğüne göre sürebilir.)")
        
        events = []
        guild = ctx.guild
        member_count = 0
        role_count = 0

        # Şalter kontrolü (Eğer role logları kapalıysa senkronizasyon yapmasın)
        if hasattr(self.bot, "db"):
            db_row = await self.bot.db.fetchone("SELECT * FROM db_log_settings WHERE guild_id=?", str(guild.id))
            # mod_role_on veya role_add_on kapalı ise durdurulabilir. Biz genelde kapalıysa loglamıyoruz.
            if db_row and dict(db_row).get("mod_role_on") == 0:
                await msg.edit(content="❌ Rol logları (mod_role_on) veritabanında kapalı! Lütfen önce ayarları açın.")
                return

        for member in guild.members:
            if member.bot: continue
            
            # Everyone rolü hariç, kullanıcının rollerini al
            roles = [r for r in member.roles if r.id != guild.id]
            if not roles: continue

            member_count += 1
            if hasattr(self.bot, "db"):
                await self.bot.db.update_user_cache(str(member.id), member.name, member.display_avatar.url)

            for role in roles:
                if hasattr(self.bot, "db"):
                    await self.bot.db.update_role_cache(str(guild.id), str(role.id), role.name)
                
                details = {
                    "username": str(member.name),
                    "avatar_url": member.display_avatar.url if member.display_avatar else None,
                    "text": f"Toplu Rol Senkronizasyonu ile eklendi: {role.name}"
                }
                
                events.append((
                    guild.id,
                    "role_sync_add",  # Web UI bunu bar başlangıcı olarak görecek (includes 'add')
                    str(member.id),
                    details,
                    str(role.id)
                ))
                role_count += 1

        if events and hasattr(self.bot.db, "log_db_events_bulk"):
            await self.bot.db.log_db_events_bulk(events)
            
        await msg.edit(content=f"✅ Başarıyla **{member_count}** üyede toplam **{role_count}** rol senkronize edildi. (Web UI barları oluşturuldu.)")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleSync(bot))
