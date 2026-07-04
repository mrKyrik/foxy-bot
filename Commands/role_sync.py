import logging
import discord
from discord.ext import commands
from core.checks import kumiho_check

log = logging.getLogger(__name__)

class RoleSync(commands.Cog):
    category = "Yönetim ve Ayarlar"
    """Rol Senkronizasyonu"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="sync_roles", aliases=["rol_senkronize", "rolesync"])
    @kumiho_check("owner")
    async def sync_roles(self, ctx: commands.Context) -> None:
        """sync_roles işlemini güvenli bir şekilde gerçekleştirir. Kullanım: `f.sync_roles [parametreler]`"""
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
                
                events.append((
                    str(guild.id),
                    str(member.id),
                    str(role.id),
                    role.name
                ))
                role_count += 1

        if events and hasattr(self.bot, "db") and hasattr(self.bot.db, "sync_user_roles_bulk"):
            await self.bot.db.sync_user_roles_bulk(str(guild.id), events)
            
        await msg.edit(content=f"✅ Başarıyla **{member_count}** üyede toplam **{role_count}** rol senkronize edildi. (Web UI barları oluşturuldu.)")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleSync(bot))
