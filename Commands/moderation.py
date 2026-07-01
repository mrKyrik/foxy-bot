import asyncio
import datetime
import json
import logging
import random
import re
from pathlib import Path

import discord
from discord.ext import commands, tasks

from core.utils import json_load, json_save

log = logging.getLogger(__name__)

warnsFile = Path("Data/warns.json")
confirmFile = Path("Data/confirmationWords.json")
tempBansFile = Path("Data/tempBans.json")

ACTION_GIF = "https://cdn.discordapp.com/banners/1505199750855659570/7b097c5d9cffbb17df26b5357adf92a1.png?size=512"


class TriviaConfirmation(discord.ui.View):
    def __init__(self, ctx, trivia_file_path, action_type="warns_wipe"):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.value = None
        self.initial_message = None
        self.action_type = action_type  # "warns_wipe" or "unban_all"

        self.answers, self.correct_answer = self.load_and_pick_answer(trivia_file_path)

        available_options = self.answers[:25]

        options = [
            discord.SelectOption(label=str(ans), value=str(ans))
            for ans in available_options
        ]

        self.select_menu = discord.ui.Select(
            placeholder="Select the correct answer to confirm...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    def load_and_pick_answer(self, file_path):
        """Loads your verification source JSON array."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                data = [data]

            correct_selection = random.choice(data)
            return data, correct_selection

        except Exception as e:
            print(f"Error loading trivia confirmation file: {e}")
            fallback = [
                "Confirm Data Purge",
                "Authorize Database Wipe",
                "Emergency Override",
            ]
            return fallback, random.choice(fallback)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                f"Only {self.ctx.author.mention} can interact with this.",
                ephemeral=True,
            )
            return False
        return True

    async def select_callback(self, interaction: discord.Interaction):
        user_choice = self.select_menu.values[0]

        if user_choice == self.correct_answer:
            self.value = True
            self.stop()

            title = "Failed"
            description = "There is a chance this action didnt complete"
            if self.action_type == "warns_wipe":
                try:
                    await self.ctx.bot.db.execute("DELETE FROM warns WHERE guild_id=?", str(self.ctx.guild.id))
                except Exception as e:
                    print(f"Error deleting warnings from db: {e}")

                title = "Database Reset Success"
                description = f"All infraction logs for **{self.ctx.guild.name}** have been wiped."

            elif self.action_type == "unban_all":
                await interaction.response.defer()

                unban_count = 0
                async for ban_entry in self.ctx.guild.bans():
                    try:
                        await self.ctx.guild.unban(
                            ban_entry.user, reason=f"Mass unban by {self.ctx.author}"
                        )
                        unban_count += 1
                        await asyncio.sleep(0.5)
                    except discord.HTTPException:
                        pass

                title = "Mass Unban Success"
                description = (
                    f"Successfully unbanned {unban_count} users from the server."
                )

            embed = discord.Embed(
                title=title, description=description, color=discord.Color.green()
            )

            if self.action_type == "unban_all":
                await interaction.edit_original_response(
                    content=None, embed=embed, view=None
                )
            else:
                await interaction.response.edit_message(
                    content=None, embed=embed, view=None
                )

        else:
            self.value = False
            self.stop()

            embed = discord.Embed(
                title="Verification Failed",
                description="Incorrect choice selected. The operation was aborted safely.",
                color=discord.Color.red(),
            )
            await interaction.response.edit_message(
                content=None, embed=embed, view=None
            )

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()

        embed = discord.Embed(
            title="Operation Cancelled",
            description="Action cancelled by user. No modifications were made.",
            color=discord.Color.orange(),
        )
        await interaction.response.edit_message(content=None, embed=embed, view=None)

    async def on_timeout(self):
        self.stop()
        if self.initial_message:
            try:
                await self.initial_message.delete()
            except discord.HTTPException:
                pass


class BanPaginator(discord.ui.View):
    def __init__(self, ctx, embeds):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.embeds = embeds
        self.index = 0

        self.prev_btn = discord.ui.Button(
            label="⬅️ Prev", style=discord.ButtonStyle.gray
        )

        self.page_btn = discord.ui.Button(
            label=f"Page {self.index + 1}/{len(self.embeds)}",
            style=discord.ButtonStyle.gray,
            disabled=True,
        )

        self.next_btn = discord.ui.Button(
            label="➡️ Next", style=discord.ButtonStyle.gray
        )

        self.prev_btn.callback = self.prev_page
        self.next_btn.callback = self.next_page

        self.add_item(self.prev_btn)
        self.add_item(self.page_btn)
        self.add_item(self.next_btn)

        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = self.index == 0
        self.next_btn.disabled = self.index == len(self.embeds) - 1
        self.page_btn.label = f"Page {self.index + 1}/{len(self.embeds)}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                f"Only {self.ctx.author.mention} can interact with this.",
                ephemeral=True,
            )
            return False
        return True

    async def prev_page(self, interaction: discord.Interaction):
        if self.index > 0:
            self.index -= 1
        self.update_buttons()

        await interaction.response.edit_message(
            embed=self.embeds[self.index], view=self
        )

    async def next_page(self, interaction: discord.Interaction):
        if self.index < len(self.embeds) - 1:
            self.index += 1

        self.update_buttons()

        await interaction.response.edit_message(
            embed=self.embeds[self.index], view=self
        )


class Moderation(commands.Cog):
    """
    Moderation commands like kick, ban, unban...
    """

    def __init__(self, bot):
        self.bot = bot
        self.check_temp_bans.start()

    async def cog_unload(self):
        self.check_temp_bans.cancel()

    def parse_time(self, time: str) -> datetime.timedelta | None:
        timeRegex = re.compile(r"(\d+)(s|m|h|d|mo|y)")
        matches = timeRegex.findall(time.lower())

        if not matches:
            return None

        totalSec = 0
        for amount, unit in matches:
            amount = int(amount)
            if unit == "s":
                totalSec += amount
            elif unit == "m":
                totalSec += amount * 60
            elif unit == "h":
                totalSec += amount * 3600
            elif unit == "d":
                totalSec += amount * 86400
            elif unit == "mo":
                totalSec += amount * 2592000  # Approximated as 30 days
            elif unit == "y":
                totalSec += amount * 31536000  # Approximated as 365 days

        return datetime.timedelta(seconds=totalSec)

    @commands.command(aliases=["k"])
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(
        self, ctx, user: discord.Member = None, *, reason="No reason provided."
    ):
        """
        Kicks the specified user from the server if you have permission.
        Usage: `.[kick|k] <user> [reason]`

        Arguments:
            \tuser (discord.Member): The user to kick.
            \treason (str, optional): The reason for the kick.
        """
        if user is None:
            return await ctx.send("Usage: `.[kick|k] <user> [reason]`")
        if user == self.bot.user:
            return await ctx.send("I am not kicking myself.")

        if user.top_role.position >= ctx.author.top_role.position:
            return await ctx.send("You cannot kick this user.")
        else:
            kick = ACTION_GIF

            embeded = discord.Embed(
                title="User Kicked",
                description=f"{user.mention} has been officially kicked.",
                color=discord.Color.yellow(),
            )
            embeded.add_field(name="Reason", value=reason, inline=False)
            embeded.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

            embeded.set_thumbnail(url=kick)

            embededUser = embeded.copy()
            embededUser.title = "You have been kicked"
            embededUser.description = f"You have been kicked from {ctx.guild.name}."

            try:
                await user.send(embed=embededUser)
            except discord.Forbidden:
                pass

            await user.kick(reason=reason)
            await ctx.send(embed=embeded)

    @commands.group(name="ban", aliases=["b"], invoke_without_command=True)
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban_group(
        self, ctx, user: discord.Member = None, *, reason="No reason provided."
    ):
        """
        Bans the specified user from the server if you have permission.
        Usage: `.[ban|b] <user> [reason]`

        Arguments:
            \tuser (discord.Member): The user to ban.
            \treason (str, optional): The reason for the ban.
        """

        if user is None:
            return await ctx.send("Usage: `.[ban|b] <user> [reason]`")
        if user == self.bot.user:
            return await ctx.send("I am not banning myself.")

        if user.top_role.position >= ctx.author.top_role.position:
            return await ctx.send("You cannot ban this user.")
        else:
            ban = ACTION_GIF

            embeded = discord.Embed(
                title="User Banned",
                description=f"{user.mention} has been officially banned.",
                color=discord.Color.red(),
            )
            embeded.add_field(name="Reason", value=reason, inline=False)
            embeded.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

            embeded.set_thumbnail(url=ban)

            embededUser = embeded.copy()
            embededUser.title = "You have been banned"
            embededUser.description = f"You have been banned from {ctx.guild.name}."

            try:
                await user.send(embed=embededUser)
            except discord.Forbidden:
                pass

            await user.ban(reason=reason)
            await ctx.send(embed=embeded)

    @ban_group.command(name="soft")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban_soft(
        self, ctx, user: discord.Member = None, *, reason: str = "No reason provided."
    ):
        """
        Bans and unbans the specified user from the server to kick and purge their messages.

        Usage:
            \t.ban soft <user> [reason]

        Arguments:
            \tmember (str): The user to ban and unban by Name, Tag, or ID.
            \treason (str): The reason for the soft ban.
        """
        if user is None:
            return await ctx.send("Usage: `.[ban|b] soft <user> [reason]`")
        if user == self.bot.user:
            return await ctx.send("I am not soft banning myself.")

        if user.top_role.position >= ctx.author.top_role.position:
            return await ctx.send("You cannot soft ban this user.")
        else:
            ban = ACTION_GIF

            embeded = discord.Embed(
                title="User Soft Banned",
                description=f"{user.mention} has been soft banned.",
                color=discord.Color.red(),
            )
            embeded.add_field(name="Reason", value=reason, inline=False)
            embeded.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

            embeded.set_thumbnail(url=ban)

            embededUser = embeded.copy()
            embededUser.title = "You have been soft banned"
            embededUser.description = (
                f"You have been soft banned from {ctx.guild.name}."
            )

            try:
                await user.send(embed=embededUser)
                await user.send(
                    "-# soft ban is a kick with purge messages, you can rejoin"
                )
            except discord.Forbidden:
                pass

            await user.ban(reason=reason)
            await ctx.send(embed=embeded)
            await ctx.send("-# soft ban is a kick with purge messages, they can rejoin")
            await user.unban(reason="Soft ban")

    @ban_group.command(name="temporary", aliases=["temp"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban_temp(
        self,
        ctx,
        user: discord.Member = None,
        *args,
    ):
        """
        Bans the specified user from the server for a temporary period.

        Time format:
            \tm = minutes, h = hours, d = days, mo = months, y = years
            \tExamples: 1d, 2h, 30m, 5s

        Usage:
            \t.[ban|b] [temporary|temp] <user> <time> [reason]

        Arguments:
            \tuser (discord.Member): The user to ban.
            \ttime (str, optional): The duration of the ban. Defaults to *1d* (1 day).
            \treason (str, optional): The reason for the ban. Defaults to *No reason provided*.
        """
        if not user:
            return await ctx.send(
                "usage: `.[ban|b] [temporary|temp] <user> <time> [reason]`"
            )
        if user == self.bot.user:
            return await ctx.send("I am not banning myself.")

        if user.top_role.position >= ctx.author.top_role.position:
            return await ctx.send("You cannot ban this user.")

        if not args:
            args = ("1d",)

        full_input_str = " ".join(args)

        duration = self.parse_time(full_input_str)
        if not duration:
            return await ctx.send("Invalid time format. Time format: `s,m,h,d,mo,y`")

        reason = "No reason provided."
        timeRegex = re.compile(r"(\d+)(s|m|h|d|mo|y)")
        matches = list(timeRegex.finditer(full_input_str.lower()))

        if matches:
            last_match_end = matches[-1].end()
            extracted_reason = full_input_str[last_match_end:].strip()
            if extracted_reason:
                reason = extracted_reason

        ban_gif = ACTION_GIF

        unban_time = datetime.datetime.now(datetime.timezone.utc) + duration
        unban_timestamp = int(unban_time.timestamp())

        embeded = discord.Embed(
            title="User Temporarily Banned",
            description=f"{user.mention} has been temporarily banned.",
            color=discord.Color.red(),
        )
        embeded.add_field(
            name="Duration",
            value=f"Expires <t:{unban_timestamp}:F> (<t:{unban_timestamp}:R>)",
            inline=False,
        )
        embeded.add_field(name="Reason", value=reason, inline=False)
        embeded.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        if ban_gif:
            embeded.set_thumbnail(url=ban_gif)

        if not user.bot:
            embededUser = embeded.copy()
            embededUser.title = "You have been temporarily banned"
            embededUser.description = (
                f"You have been temporarily banned from {ctx.guild.name}."
            )

            try:
                await user.send(embed=embededUser)
            except (discord.Forbidden, discord.HTTPException):
                pass

        await user.ban(reason=f"[Temp-ban by {ctx.author}] {reason}")
        await ctx.send(embed=embeded)

        await self.bot.db.execute(
            "INSERT OR REPLACE INTO temp_bans (guild_id, user_id, unban_timestamp) VALUES (?, ?, ?)",
            str(ctx.guild.id), str(user.id), float(unban_timestamp)
        )

    @tasks.loop(seconds=30, reconnect=True)
    async def check_temp_bans(self):
        await self.bot.wait_until_ready()
        try:
            now = datetime.datetime.now(datetime.timezone.utc).timestamp()
            
            rows = await self.bot.db.fetchall("SELECT guild_id, user_id FROM temp_bans WHERE unban_timestamp <= ?", now)
            
            for row in rows:
                guild_id_str = str(row["guild_id"])
                user_id_str = str(row["user_id"])
                guild = self.bot.get_guild(int(guild_id_str))
                
                if guild:
                    try:
                        user = await self.bot.fetch_user(int(user_id_str))
                        await guild.unban(user, reason="Temporary ban expired.")
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        pass
                
                await self.bot.db.execute("DELETE FROM temp_bans WHERE guild_id=? AND user_id=?", guild_id_str, user_id_str)
        except Exception as e:
            log.error(f"Error in check_temp_bans task: {e}")

    @commands.group(name="unban", aliases=["ub"], invoke_without_command=True)
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban_group(self, ctx, *, member: str = None):
        """
        Unbans the specified user from the server if you have permission.

        Usage:
            \t.unban <user>        - Unban a specific user by Name, Tag, or ID.

        Arguments:
            \tuser (str): The user to unban by Name, Tag, or ID.
        """
        if member is None:
            return await ctx.send("Usage: `.[unban|ub] <user>`\n")

        cleaned_member = (
            member.replace("<@", "").replace(">", "").replace("!", "").strip()
        )

        bans = [entry async for entry in ctx.guild.bans()]

        for ban_entry in bans:
            user = ban_entry.user

            if (
                str(user) == cleaned_member
                or user.name.lower() == cleaned_member.lower()
                or str(user.id) == cleaned_member
                or (
                    user.global_name
                    and user.global_name.lower() == cleaned_member.lower()
                )
            ):
                await ctx.guild.unban(user)
                return await ctx.send(f"Unbanned {user}.")

        await ctx.send("User not found in banned list.")

    async def _list_ban(self, ctx):
        bans = [entry async for entry in ctx.guild.bans()]

        if not bans:
            return await ctx.send("No banned users.")

        rows = await self.bot.db.fetchall("SELECT user_id, unban_timestamp FROM temp_bans WHERE guild_id=?", str(ctx.guild.id))
        guild_temp_bans = {str(row["user_id"]): row["unban_timestamp"] for row in rows}

        embeds = []
        for ban in bans:
            user = ban.user
            user_id_str = str(user.id)

            embed = discord.Embed(
                title=f"Banned User: {user}", color=discord.Color.red()
            )
            embed.set_thumbnail(url=user.display_avatar.url)

            embed.add_field(
                name="User Info",
                value=(
                    f"**Username:** {user.name}\n"
                    f"**Global Name:** {user.global_name or 'None'}\n"
                    f"**ID:** {user.id}"
                ),
                inline=False,
            )

            ban_type = "Permanent"
            duration_str = ""

            if user_id_str in guild_temp_bans:
                ban_type = "Temporary"
                unban_timestamp = guild_temp_bans[user_id_str]
                duration_str = f"\n**Expires:** <t:{int(unban_timestamp)}:F> (<t:{int(unban_timestamp)}:R>)"

            embed.add_field(
                name="Ban Details",
                value=(
                    f"**Type:** {ban_type}{duration_str}\n"
                    f"**Reason:** {ban.reason or 'No reason provided.'}"
                ),
                inline=False,
            )

            embeds.append(embed)

        view = BanPaginator(ctx, embeds)
        return await ctx.send(embed=embeds[0], view=view)

    @ban_group.command(name="list")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban_list(self, ctx):
        """
        Shows banned users with pagination.
        Same as `.[uban|ub] list`
        Usage: `.[ban|b] list`
        """
        await self._list_ban(ctx)

    @unban_group.command(name="list")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban_list(self, ctx):
        """
        Shows banned users with pagination.
        Same as `.[ban|b] list`
        Usage: `.[unban|ub] list`
        """
        await self._list_ban(ctx)

    @commands.group(name="warn", aliases=["w"], invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def warn_group(
        self, ctx, user: discord.Member = None, *, reason: str = "No reason provided."
    ):
        """
        Manages server warnings with sequential Case IDs.

        Usage:
            \t.warn <@user/ID> [reason] - Warn a member.

        Arguments:
            \tuser (str): The user to warn by Name, Tag, or ID.
            \treason (str, optional): The reason for the warning. Defaults to "No reason provided.".
        """
        if user is None:
            return await ctx.send("Usage: `.[warn|w] <user> [reason]`\n")

        if user == self.bot.user:
            return await ctx.send("I am not warning myself.")

        warns = warnsFile

        warns = warnsFile

        await self.bot.db.execute(
            "INSERT INTO warns (guild_id, user_id, mod_id, reason) VALUES (?, ?, ?, ?)",
            str(ctx.guild.id), str(user.id), str(ctx.author.id), reason
        )

        rows = await self.bot.db.fetchall(
            "SELECT warn_id FROM warns WHERE guild_id=? AND user_id=? ORDER BY warn_id ASC",
            str(ctx.guild.id), str(user.id)
        )
        total_warns = len(rows)
        strikes = total_warns // 3
        next_case_id = rows[-1]["warn_id"] if rows else 1

        embed_color = (
            discord.Color.red() if total_warns >= 3 else discord.Color.orange()
        )
        embeded = discord.Embed(
            title="User Warned",
            description=f"{user.mention} has been officially warned.",
            color=embed_color,
        )
        embeded.add_field(name="Reason", value=reason, inline=False)
        embeded.add_field(name="Total Warns", value=str(total_warns), inline=True)
        embeded.add_field(name="Case ID", value=f"#{next_case_id}", inline=True)

        if total_warns >= 3:
            embeded.add_field(
                name="Total Strikes",
                value=str(strikes),
                inline=True,
            )

        await ctx.send(embed=embeded)

        embeded.title = "You have been warned"
        embeded.description = (
            f"You have been officially warned in **{ctx.guild.name}**."
        )
        try:
            await user.send(embed=embeded)
        except discord.Forbidden:
            pass

    @warn_group.command(name="clear")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def warn_clear(self, ctx, *, target: str = None):
        """
        Remove a specific warning by its ID or clear all warnings.

        Usage:
            \t`.warn clear <case_id>`
            \t`.warn clear all`
        Arguments:
            \ttarget_id (str): The Case ID of the warning to clear, or "all" to clear all warnings.
        """
        if not target:
            return await ctx.send(
                "Usage: `.warn clear <case_id>`\r\nUsage: `.warn clear all`."
            )

        confirm = confirmFile
        target = target.strip().lower()

        if target == "all":
            rows = await self.bot.db.fetchall("SELECT 1 FROM warns WHERE guild_id=?", str(ctx.guild.id))
            if not rows:
                return await ctx.send("The warning database is already empty.")

            view = TriviaConfirmation(ctx, confirm, action_type="warns_wipe")
            embed = discord.Embed(
                title="CRITICAL ACTION REQUIRED",
                description=(
                    "You are about to wipe **EVERY SINGLE INFRACTION** in this server.\n"
                    "This action is completely irreversible.\n\n"
                    f"To verify this action, select `{view.correct_answer}` from the dropdown menu below."
                ),
                color=discord.Color.dark_red(),
            )
            embed.set_footer(
                text="This security confirmation window expires in 30 seconds."
            )
            msg = await ctx.send(embed=embed, view=view)
            view.initial_message = msg
            return

        found = False
        row = await self.bot.db.fetchone("SELECT 1 FROM warns WHERE guild_id=? AND warn_id=?", str(ctx.guild.id), target)
        if row:
            await self.bot.db.execute("DELETE FROM warns WHERE guild_id=? AND warn_id=?", str(ctx.guild.id), target)
            found = True

            embed = discord.Embed(
                title="Case Cleared",
                description=f"Successfully cleared warning Case #{target}.",
                color=discord.Color.green(),
            )
            return await ctx.send(embed=embed)

        if not found:
            embed = discord.Embed(
                title="Case Not Found",
                description=f"Could not find any active warning associated with Case ID #{target}.",
                color=discord.Color.red(),
            )
            return await ctx.send(embed=embed)

    @warn_group.command(name="list")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def warn_list(self, ctx, *, target_user: discord.Member = None):
        """
        List all warned users or view specific user infractions.
        Usage: `.warn list [user]`

        Arguments:
            \tuser (discord.Member, optional): The user to view warnings for. Defaults to None.
        """
        query = "SELECT warn_id, user_id, reason FROM warns WHERE guild_id=?"
        args = [str(ctx.guild.id)]
        if target_user:
            query += " AND user_id=?"
            args.append(str(target_user.id))
        
        rows = await self.bot.db.fetchall(query, *args)
        if not rows:
            if target_user:
                return await ctx.send(f"**{target_user}** does not have any active warnings.")
            return await ctx.send("No users have any active warnings in this server.")
            
        grouped_data = {}
        for row in rows:
            uid = row["user_id"]
            if uid not in grouped_data:
                grouped_data[uid] = {"warnings": {}, "strikes": 0}
            grouped_data[uid]["warnings"][str(row["warn_id"])] = row["reason"]
            
        for uid in grouped_data:
            grouped_data[uid]["strikes"] = len(grouped_data[uid]["warnings"]) // 3

        embeds = []
        for user_id, user_data in grouped_data.items():
            member = ctx.guild.get_member(int(user_id))
            name_str = f"{member} ({member.id})" if member else f"User ID: {user_id}"
            warnings_dict = user_data.get("warnings", {})
            strikes = user_data.get("strikes", 0)

            embed = discord.Embed(
                title=f"Warnings for {name_str}", color=discord.Color.red()
            )
            if member:
                embed.set_thumbnail(url=member.display_avatar.url)

            embed.add_field(
                name="Stats",
                value=f"**Total Warns:** {len(warnings_dict)}\n**Total Strikes:** {strikes}",
                inline=False,
            )

            sorted_warns = sorted(warnings_dict.items(), key=lambda x: int(x[0]))
            warn_list_text = "".join(
                [f"Case #{w_id} - {w_reason}\n" for w_id, w_reason in sorted_warns]
            )

            embed.add_field(
                name="Active Infractions", value=warn_list_text, inline=False
            )
            embeds.append(embed)

        if not embeds:
            return await ctx.send("No warnings found matching your criteria.")
        if len(embeds) == 1:
            return await ctx.send(embed=embeds[0])

        view = BanPaginator(ctx, embeds)
        return await ctx.send(embed=embeds[0], view=view)

    async def _execute_purge(self, ctx, limit: int, check_func=None):
        """Helper method to handle the shared purge execution loop cleanly."""
        if limit < 1 or limit > 500:
            return await ctx.send("Purge limit must be between 1 and 500.")

        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
        deleted = await ctx.channel.purge(limit=limit + 1, check=check_func)

        confirm = await ctx.send(f"Successfully deleted **{len(deleted)}** messages.")
        await asyncio.sleep(3)
        try:
            await confirm.delete()
        except discord.HTTPException:
            pass

    @commands.group(name="purge", aliases=["clear", "clr"], invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge_group(self, ctx, amount: int = 10):
        """
        Purges recent messages.
        Usage: .[purge|clear|clr] [amount]
        Arguments:
            \tamount (int, optional): The number of messages to purge. Defaults to 10.
        """

        await self._execute_purge(ctx, limit=amount)

    @purge_group.command(name="bot", aliases=["bots"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge_bot(self, ctx, amount: int = 100):
        """
        Purges only bot messages.
        Usage: .[purge|clear|clr] bot [amount]
        Arguments:
            \tamount (int, optional): The number of bot messages to purge. Defaults to 100.
        """
        await self._execute_purge(ctx, limit=amount, check_func=lambda m: m.author.bot)

    @purge_group.command(name="user")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge_user(self, ctx, target: discord.Member, amount: int = 10):
        """
        Purges messages from a specific user.
        Usage: .[purge|clear|clr] user <@user/ID> [amount]

        Arguments:
            \tamount (int, optional): The number of messages to purge. Defaults to 10.
        """
        await self._execute_purge(
            ctx, limit=amount, check_func=lambda m: m.author.id == target.id
        )

    @purge_group.command(name="contains", aliases=["contain", "text"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge_contains(self, ctx, text: str, amount: int = 10):
        """
        Purges messages containing specific text.
        Usage: .[purge|clear|clr] contains <text> [amount]

        Arguments:
            \ttext (str): The text to search for in messages.
            \tamount (int, optional): The number of messages to purge. Defaults to 10.
        """
        await self._execute_purge(
            ctx,
            limit=amount,
            check_func=lambda m: text.lower() in m.content.lower(),
        )

    @purge_group.command(
        name="embeds", aliases=["embed", "file", "files", "attachment", "attachments"]
    )
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge_embeds(self, ctx, amount: int = 100):
        """
        Purges messages with embeds or attachments.
        Usage: .purge embeds [amount]

        Arguments:
            \tamount (int, optional): The number of messages to purge. Defaults to 100.
        """
        await self._execute_purge(
            ctx,
            limit=amount,
            check_func=lambda m: len(m.embeds) > 0 or len(m.attachments) > 0,
        )

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def nuke(self, ctx, channel: discord.TextChannel = None):
        """
        Nukes a channel by cloning it and deleting the old one.
        Usage: `.nuke [channel]`
        Arguments:
            \tchannel (discord.TextChannel, optional): The specific channel to nuke. Defaults to the current channel.
        """

        targetChannel = channel or ctx.channel
        pos = targetChannel.position

        new_channel = await targetChannel.clone(reason=f"Nuke by {ctx.author}")

        await targetChannel.delete(reason=f"Nuke by {ctx.author}")
        await new_channel.edit(position=pos)

        await new_channel.send("first mwheehhe")

        nuke = ACTION_GIF

        embed = discord.Embed(
            description=f"Nuked by **{ctx.author}**",
            color=discord.Color.red(),
        )
        if nuke:
            embed.set_image(url=nuke)
        await new_channel.send(embed=embed)

    @commands.command(aliases=["ui", "whois"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def userinfo(self, ctx, member: discord.Member = None):
        """
        Returns information about the mentioned/replyed person
        Usage: `.[userinfo|ui|whois] [member]`
        Arguments:
            member (discord.Member, optional): The member whose information to retrieve. Defaults to the command author.
        """
        member = member or ctx.author

        profile = member.display_avatar.url
        name = member.name
        id = member.id

        statusEmojis = {
            "online": "🟢 Online",
            "idle": "🌙 Idle",
            "dnd": "🔴 Do Not Disturb",
            "offline": "⚪ Offline",
        }

        status = statusEmojis.get(str(member.status).lower(), "⚪ Offline")
        activity = member.activity.name if member.activity else "None"
        activity = f"{status} | {activity}"

        created = f"<t:{int(member.created_at.timestamp())}:F>\n(<t:{int(member.created_at.timestamp())}:R>)"
        joined = (
            f"<t:{int(member.joined_at.timestamp())}:F>\n(<t:{int(member.joined_at.timestamp())}:R>)"
            if member.joined_at
            else "N/A"
        )

        key_perms = []
        perms = {
            "administrator": "👑 Administrator",
            "manage_guild": "⚙️ Manage Server",
            "manage_roles": "🛡️ Manage Roles",
            "manage_channels": "📁 Manage Channels",
            "kick_members": "👢 Kick Members",
            "ban_members": "🔨 Ban Members",
        }
        for perm, label in perms.items():
            if getattr(member.guild_permissions, perm):
                key_perms.append(label)

        key_perms_text = ", ".join(key_perms) if key_perms else "Standard Member"

        roles = [role.mention for role in reversed(member.roles[1:])]
        rolesText = ", ".join(roles) if roles else "N/A"

        colour = member.color if member.color.value != 0 else discord.Color.blurple()

        embeded = discord.Embed(
            title=f"User Info | {member.display_name}",
            color=colour,
        )
        embeded.set_thumbnail(url=profile)

        embeded.add_field(name="Username", value=name, inline=True)
        embeded.add_field(name="ID", value=f"```{id}```", inline=True)
        embeded.add_field(
            name="Status | Activity",
            value=activity,
            inline=True,
        )

        embeded.add_field(name="📅 Account Created", value=created, inline=True)
        embeded.add_field(name="📥 Joined Server", value=joined, inline=True)

        embeded.add_field(
            name="🔑 Key Permissions", value=f"`{key_perms_text}`", inline=False
        )
        embeded.add_field(
            name=f"🎭 Roles ({len(roles)})", value=rolesText, inline=False
        )

        await ctx.send(embed=embeded)

    async def cog_command_error(self, ctx, error):

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.")
            return
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("I do not have permission to do that.")
            return
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Please provide a valid whole **number**.")
            return

        await ctx.send(f"An error occurred: {error}")


async def setup(bot):
    await bot.add_cog(Moderation(bot))
