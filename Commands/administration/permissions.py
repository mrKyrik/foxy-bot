from __future__ import annotations
from core.checks import kumiho_check, kumiho_app_check
import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import json

class Permissions(commands.Cog):
    category = "Yönetim ve Ayarlar"
    category_emoji = "⚙️"
    """Komut yetkilerini Discord üzerinden yönetmenizi sağlayan sistem."""
    def __init__(self, bot):
        self.category = "Yönetim ve Ayarlar"
        self.bot = bot

    yetki_group = app_commands.Group(name="yetki", description="Komut yetkilerini yönetin")

    @yetki_group.command(name="ekle", description="Bir komutu kullanabilmesi için belirli bir role yetki verir")
    @app_commands.default_permissions(administrator=True)
    @kumiho_check("owner")
    async def yetki_ekle(self, interaction: discord.Interaction, komut_adi: str, rol: discord.Role):
        # Sadece komut var mı diye basit bir kontrol (Prefix veya Slash)
        """Execute the yetki_ekle command.\n\n**Usage:** `{prefix}yetki_ekle`"""
        cmd = self.bot.get_command(komut_adi)
        if not cmd:
            app_cmd = discord.utils.get(self.bot.tree.get_commands(), name=komut_adi)
            if not app_cmd:
                return await interaction.response.send_message(f"❌ `{komut_adi}` adında bir komut bulunamadı.", ephemeral=True)
                
        row = await self.bot.db.fetchone("SELECT allowed_roles FROM command_permissions WHERE guild_id = ? AND command_name = ?", str(interaction.guild.id), komut_adi)
            
        allowed_roles = []
        if row and row[0]:
            try:
                allowed_roles = json.loads(row[0])
            except:
                pass
                
        if str(rol.id) not in allowed_roles:
            allowed_roles.append(str(rol.id))
            
        roles_json = json.dumps(allowed_roles)
        
        await self.bot.db.execute('''INSERT INTO command_permissions (guild_id, command_name, is_enabled, allowed_roles)
                            VALUES (?, ?, 1, ?)
                            ON CONFLICT(guild_id, command_name) 
                            DO UPDATE SET allowed_roles=excluded.allowed_roles''',
                         str(interaction.guild.id), komut_adi, roles_json)
            
        await interaction.response.send_message(f"✅ `{komut_adi}` komutu artık {rol.mention} rolü tarafından kullanılabilir.")

    @yetki_group.command(name="kaldir", description="Bir komutun yetkisini belirli bir rolden alır")
    @app_commands.default_permissions(administrator=True)
    @kumiho_check("owner")
    async def yetki_kaldir(self, interaction: discord.Interaction, komut_adi: str, rol: discord.Role):
        """Execute the yetki_kaldir command.\n\n**Usage:** `{prefix}yetki_kaldir`"""
        row = await self.bot.db.fetchone("SELECT allowed_roles FROM command_permissions WHERE guild_id = ? AND command_name = ?", str(interaction.guild.id), komut_adi)
            
        if not row or not row[0]:
            return await interaction.response.send_message(f"❌ Bu komut için atanmış özel bir rol bulunamadı.", ephemeral=True)
            
        try:
            allowed_roles = json.loads(row[0])
        except:
            allowed_roles = []
            
        if str(rol.id) in allowed_roles:
            allowed_roles.remove(str(rol.id))
            
        roles_json = json.dumps(allowed_roles)
        
        await self.bot.db.execute("UPDATE command_permissions SET allowed_roles = ? WHERE guild_id = ? AND command_name = ?", 
                         roles_json, str(interaction.guild.id), komut_adi)
            
        await interaction.response.send_message(f"✅ `{komut_adi}` komutu için {rol.mention} yetkisi kaldırıldı.")
        
    @yetki_group.command(name="listele", description="Sunucudaki özelleştirilmiş komut yetkilerini listeler")
    @app_commands.default_permissions(administrator=True)
    @kumiho_check("owner")
    async def yetki_listele(self, interaction: discord.Interaction):
        """Execute the yetki_listele command.\n\n**Usage:** `{prefix}yetki_listele`"""
        rows = await self.bot.db.fetchall("SELECT command_name, allowed_roles FROM command_permissions WHERE guild_id = ?", str(interaction.guild.id))
                
        if not rows:
            return await interaction.response.send_message("ℹ️ Bu sunucu için ayarlanmış özel bir komut yetkisi bulunmuyor.")
            
        embed = discord.Embed(title="🛡️ Özel Komut Yetkileri", color=discord.Color.blue())
        for cmd_name, roles_str in rows:
            if not roles_str or roles_str == '[]':
                continue
            try:
                role_ids = json.loads(roles_str)
                roles_mentions = [f"<@&{r_id}>" for r_id in role_ids]
                embed.add_field(name=f"/{cmd_name}", value=", ".join(roles_mentions), inline=False)
            except:
                pass
                
        if not embed.fields:
            return await interaction.response.send_message("ℹ️ Bu sunucu için ayarlanmış özel bir komut yetkisi bulunmuyor.")
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="komut-kapat", description="Belirtilen komutu sunucu genelinde kapatır.")
    @app_commands.default_permissions(administrator=True)
    @kumiho_check("owner")
    async def komut_kapat(self, interaction: discord.Interaction, komut_adi: str):
        cmd = self.bot.get_command(komut_adi)
        if not cmd:
            app_cmd = discord.utils.get(self.bot.tree.get_commands(), name=komut_adi)
            if not app_cmd:
                return await interaction.response.send_message(f"❌ `{komut_adi}` adında bir komut bulunamadı.", ephemeral=True)
        
        await self.bot.db.execute('''INSERT INTO command_permissions (guild_id, command_name, is_enabled, allowed_roles)
                            VALUES (?, ?, 0, '[]')
                            ON CONFLICT(guild_id, command_name) 
                            DO UPDATE SET is_enabled=0''', str(interaction.guild.id), komut_adi)
        
        await interaction.response.send_message(embed=discord.Embed(
            title="🚫 Komut Kapatıldı",
            description=f"`{komut_adi}` komutu sunucu genelinde tamamen devre dışı bırakıldı.",
            color=discord.Color.red()
        ))

    @app_commands.command(name="komut-ac", description="Kapatılmış bir komutu sunucu genelinde tekrar aktif eder.")
    @app_commands.default_permissions(administrator=True)
    @kumiho_check("owner")
    async def komut_ac(self, interaction: discord.Interaction, komut_adi: str):
        cmd = self.bot.get_command(komut_adi)
        if not cmd:
            app_cmd = discord.utils.get(self.bot.tree.get_commands(), name=komut_adi)
            if not app_cmd:
                return await interaction.response.send_message(f"❌ `{komut_adi}` adında bir komut bulunamadı.", ephemeral=True)
                
        await self.bot.db.execute('''INSERT INTO command_permissions (guild_id, command_name, is_enabled, allowed_roles)
                            VALUES (?, ?, 1, '[]')
                            ON CONFLICT(guild_id, command_name) 
                            DO UPDATE SET is_enabled=1''', str(interaction.guild.id), komut_adi)
        
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Komut Açıldı",
            description=f"`{komut_adi}` komutu sunucu genelinde tekrar aktif edildi.",
            color=discord.Color.green()
        ))

    panel_yetki_group = app_commands.Group(name="panel-yetki", description="Web paneli erişim yetkilerini yönetin")

    @panel_yetki_group.command(name="ekle", description="Belirli bir role veya üyeye web panel yetkisi verir.")
    @app_commands.default_permissions(administrator=True)
    @kumiho_check("owner")
    @app_commands.choices(seviye=[
        app_commands.Choice(name="Okuma (Read)", value="read"),
        app_commands.Choice(name="Yazma/Düzenleme (Write)", value="write")
    ])
    async def panel_yetki_ekle(self, interaction: discord.Interaction, hedef: discord.Mentionable, seviye: app_commands.Choice[str]):
        hedef_id = str(hedef.id)
        hedef_type = "role" if isinstance(hedef, discord.Role) else "user"
        
        await self.bot.db.execute('''INSERT INTO panel_access_controls (guild_id, target_id, target_type, permission_level)
                     VALUES (?, ?, ?, ?)
                     ON CONFLICT(guild_id, target_id)
                     DO UPDATE SET permission_level = excluded.permission_level, target_type = excluded.target_type''',
                  str(interaction.guild.id), hedef_id, hedef_type, seviye.value)
                  
        embed = discord.Embed(
            title="🛡️ Panel Yetkisi Verildi",
            description=f"{hedef.mention} için web paneli yetkisi tanımlandı.\n**Seviye:** `{seviye.name}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @panel_yetki_group.command(name="sil", description="Belirli bir rolün veya üyenin web panel yetkisini kaldırır.")
    @app_commands.default_permissions(administrator=True)
    @kumiho_check("owner")
    async def panel_yetki_sil(self, interaction: discord.Interaction, hedef: discord.Mentionable):
        await self.bot.db.execute("DELETE FROM panel_access_controls WHERE guild_id = ? AND target_id = ?", 
                                  str(interaction.guild.id), str(hedef.id))
        
        embed = discord.Embed(
            title="🗑️ Panel Yetkisi Kaldırıldı",
            description=f"{hedef.mention} için web paneli yetkisi başarıyla silindi.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

    @panel_yetki_group.command(name="listele", description="Web panel yetkisi olan kişi ve rolleri listeler.")
    @app_commands.default_permissions(administrator=True)
    @kumiho_check("owner")
    async def panel_yetki_listele(self, interaction: discord.Interaction):
        rows = await self.bot.db.fetchall("SELECT target_id, target_type, permission_level FROM panel_access_controls WHERE guild_id = ?", str(interaction.guild.id))
        if not rows:
            return await interaction.response.send_message(embed=discord.Embed(
                title="🛡️ Panel Yetkileri",
                description="ℹ️ Bu sunucu için ayarlanmış özel bir web paneli yetkisi bulunmuyor.",
                color=discord.Color.blue()
            ))
            
        embed = discord.Embed(title="🛡️ Web Paneli Yetkileri", color=discord.Color.blue())
        for target_id, target_type, perm_level in rows:
            mention = f"<@&{target_id}>" if target_type == "role" else f"<@{target_id}>"
            embed.add_field(name=f"Yetki: {perm_level.capitalize()}", value=mention, inline=False)
            
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Permissions(bot))
