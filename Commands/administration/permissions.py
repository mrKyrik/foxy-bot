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

async def setup(bot):
    await bot.add_cog(Permissions(bot))
