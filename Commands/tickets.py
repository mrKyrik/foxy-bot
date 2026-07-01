"""
Commands/tickets.py
--------------------
Sunucu bazlı buton tabanlı destek bileti sistemi.

Veri depolama: Data/tickets.json (kanal/rol yapılandırması — JSON'da kalır)
Transkriptler: Data/transcripts/ticket-<channel_id>.txt
"""

import asyncio
import io
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands

from core.utils import json_load, json_save

log = logging.getLogger(__name__)

DB_FILE = Path("Data/tickets.json")


class TicketCloseView(discord.ui.View):
    def __init__(self, cog: "Tickets") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="close_ticket_btn",
    )
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        confirm_view = TicketConfirmCloseView(self.cog)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to close this ticket?",
            view=confirm_view,
            ephemeral=False,
        )


class TicketConfirmCloseView(discord.ui.View):
    def __init__(self, cog: "Tickets") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Yes, Close",
        style=discord.ButtonStyle.danger,
        custom_id="confirm_close_btn",
    )
    async def confirm_close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()

        channel = interaction.channel
        guild = interaction.guild

        # Collect transcript
        messages = []
        try:
            async for m in channel.history(limit=1000, oldest_first=True):
                msg_time = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
                content = m.clean_content
                if m.attachments:
                    content += f" (Attachments: {', '.join(a.url for a in m.attachments)})"
                messages.append(f"[{msg_time}] {m.author}: {content}")
        except Exception:
            pass

        # Prepare transcript as BytesIO
        transcript_content = "\n".join(messages)
        
        owner_id = int(channel.topic) if channel.topic and channel.topic.isdigit() else 0
        owner = guild.get_member(owner_id)
        if owner:
            try:
                embed_dm = discord.Embed(
                    title="🎫 Ticket Closed",
                    description=f"Your ticket in **{guild.name}** has been closed. Transcript attached.",
                    color=discord.Color.red(),
                )
                transcript_file = discord.File(
                    io.BytesIO(transcript_content.encode("utf-8")), 
                    filename=f"transcript-{channel.name}.txt"
                )
                await owner.send(embed=embed_dm, file=transcript_file)
            except Exception:
                pass

        # Log to server log channel
        row = await self.cog.bot.db.fetchone("SELECT ticket_channel FROM log_settings WHERE guild_id=?", str(guild.id))
        if row and row["ticket_channel"]:
            log_chan = guild.get_channel(int(row["ticket_channel"]))
            if log_chan:
                try:
                    embed_log = discord.Embed(
                        title="📋 Ticket Transcript",
                        description=(
                            f"Ticket `{channel.name}` closed.\n"
                            f"Opened by: <@{owner_id}>"
                        ),
                        color=discord.Color.dark_gray(),
                    )
                    transcript_file = discord.File(
                        io.BytesIO(transcript_content.encode("utf-8")), 
                        filename=f"transcript-{channel.name}.txt"
                    )
                    await log_chan.send(embed=embed_log, file=transcript_file)
                except Exception:
                    pass

        await channel.send("🔒 Closing ticket channel in 5 seconds...")
        await asyncio.sleep(5)
        try:
            await channel.delete(reason="Ticket closed by staff")
        except Exception:
            pass

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel_close_btn",
    )
    async def cancel_close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.message.delete()


class TicketOpenView(discord.ui.View):
    def __init__(self, cog: "Tickets") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Open Ticket",
        style=discord.ButtonStyle.blurple,
        emoji="🎟️",
        custom_id="open_ticket_btn",
    )
    async def open_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        guild = interaction.guild
        user = interaction.user

        data = await asyncio.to_thread(json_load, DB_FILE)
        g_id = str(guild.id)
        category_id = data.get("category", {}).get(g_id)
        category = guild.get_channel(int(category_id)) if category_id else None

        # Check if user already has an open ticket
        existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
        if existing:
            return await interaction.response.send_message(
                f"❌ You already have an open ticket: {existing.mention}", ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
        }

        support_role_id = data.get("support", {}).get(g_id)
        if support_role_id:
            support_role = guild.get_role(int(support_role_id))
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )

        try:
            ticket_channel = await guild.create_text_channel(
                name=f"ticket-{user.name}",
                category=category,
                overwrites=overwrites,
                topic=str(user.id),
                reason=f"Ticket opened by {user.name}",
            )
        except Exception as e:
            return await interaction.response.send_message(
                f"❌ Failed to create ticket channel: {e}", ephemeral=True
            )

        await interaction.response.send_message(
            f"✅ Ticket opened in {ticket_channel.mention}!", ephemeral=True
        )

        embed = discord.Embed(
            title="🎟️ Support Ticket",
            description=(
                f"Hello {user.mention}, thank you for contacting support!\n"
                "Our staff team will assist you shortly. Please describe your issue.\n\n"
                "Click the button below to close this ticket when finished."
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Only staff and the ticket author can view this channel.")
        close_view = TicketCloseView(self.cog)
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=close_view)


class Tickets(commands.Cog):
    """
    State-of-the-art server-scoped button ticket support system.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.add_view(TicketOpenView(self))
        self.bot.add_view(TicketCloseView(self))
        self.bot.add_view(TicketConfirmCloseView(self))

    @commands.group(name="ticket", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def ticket_group(self, ctx: commands.Context) -> None:
        """Setup and manage the ticketing system."""
        p = ctx.prefix
        await ctx.send(
            "🎫 **Ticketing System**\n"
            f"• `{p}ticket setup` — Deploy ticket panel\n"
            f"• `{p}ticket category <category_id>` — Set tickets category\n"
            f"• `{p}ticket support <@role>` — Define support role\n"
            f"• `{p}ticket log <#channel>` — Define transcript log channel\n"
            f"• `{p}ticket add <@user>` — Add user to ticket\n"
            f"• `{p}ticket remove <@user>` — Remove user from ticket"
        )

    @ticket_group.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def ticket_setup(self, ctx: commands.Context) -> None:
        """Deploys the ticket open panel. Usage: `f.ticket setup`"""
        embed = discord.Embed(
            title="🎟️ Server Support Center",
            description=(
                "Have a question, report, or inquiry?\n"
                "Click the button below to open a private ticket and contact our team!"
            ),
            color=discord.Color.blurple(),
        )
        view = TicketOpenView(self)
        await ctx.send(embed=embed, view=view)

    @ticket_group.command(name="category")
    @commands.has_permissions(administrator=True)
    async def ticket_category(
        self, ctx: commands.Context, category: discord.CategoryChannel = None
    ) -> None:
        """Sets the category for ticket channels. Usage: `f.ticket category <category_id>`"""
        if not category:
            return await ctx.send(f"Usage: `{ctx.prefix}ticket category <category_id>`")
        data = await asyncio.to_thread(json_load, DB_FILE)
        data.setdefault("category", {})[str(ctx.guild.id)] = str(category.id)
        await asyncio.to_thread(json_save, DB_FILE, data)
        await ctx.send(f"✅ Ticket category set to `{category.name}`.")

    @ticket_group.command(name="support")
    @commands.has_permissions(administrator=True)
    async def ticket_support(
        self, ctx: commands.Context, role: discord.Role = None
    ) -> None:
        """Sets the support staff role. Usage: `f.ticket support <@role>`"""
        if not role:
            return await ctx.send(f"Usage: `{ctx.prefix}ticket support <@role>`")
        data = await asyncio.to_thread(json_load, DB_FILE)
        data.setdefault("support", {})[str(ctx.guild.id)] = str(role.id)
        await asyncio.to_thread(json_save, DB_FILE, data)
        await ctx.send(f"✅ Support role set to {role.mention}.")

    @ticket_group.command(name="log", aliases=["logs"])
    @commands.has_permissions(administrator=True)
    async def ticket_log(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ) -> None:
        """Sets the transcript log channel. Usage: `f.ticket log <#channel>`"""
        if not channel:
            return await ctx.send(f"Usage: `{ctx.prefix}ticket log <#channel>`")
        data = await asyncio.to_thread(json_load, DB_FILE)
        data.setdefault("logs", {})[str(ctx.guild.id)] = str(channel.id)
        await asyncio.to_thread(json_save, DB_FILE, data)
        await ctx.send(f"✅ Ticket log channel set to {channel.mention}.")

    @ticket_group.command(name="add")
    async def ticket_add(
        self, ctx: commands.Context, member: discord.Member = None
    ) -> None:
        """Adds a member to an existing ticket. Usage: `f.ticket add <@user>`"""
        if not member:
            return await ctx.send(f"Usage: `{ctx.prefix}ticket add <@user>`")
        if "ticket-" not in ctx.channel.name:
            return await ctx.send("❌ This command can only be used inside ticket channels!")
        await ctx.channel.set_permissions(
            member, view_channel=True, send_messages=True, read_message_history=True
        )
        await ctx.send(f"✅ Added {member.mention} to this ticket.")

    @ticket_group.command(name="remove")
    async def ticket_remove(
        self, ctx: commands.Context, member: discord.Member = None
    ) -> None:
        """Removes a member from a ticket channel. Usage: `f.ticket remove <@user>`"""
        if not member:
            return await ctx.send(f"Usage: `{ctx.prefix}ticket remove <@user>`")
        if "ticket-" not in ctx.channel.name:
            return await ctx.send("❌ This command can only be used inside ticket channels!")
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.send(f"✅ Removed {member.mention} from this ticket.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))
