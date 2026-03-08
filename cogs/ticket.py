"""
Ticket management cog with slash commands and interactive setup.
"""

import discord
from discord import app_commands
from discord.ext import commands
from utils import embeds
from utils.views import TicketPanelView, TicketControlView
from utils.database import (
    get_ticket,
    update_ticket,
    delete_ticket,
    get_guild_settings,
    save_guild_settings,
    get_ticket_stats,
)
import asyncio


class TicketCog(commands.Cog):
    """Ticket system commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ticket_group = app_commands.Group(name="ticket", description="Ticket management commands")

    @ticket_group.command(name="setup", description="Interactive ticket panel setup")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Multi-step interactive ticket panel setup."""

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        await interaction.response.send_message(
            embed=embeds.base_embed(
                "🎫 Ticket Setup — Step 1/6",
                "What should the **embed title** be?\nType your answer below.",
            ),
        )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=120)
            title = msg.content

            await interaction.channel.send(
                embed=embeds.base_embed("🎫 Ticket Setup — Step 2/6", "Enter the **embed description**."),
            )
            msg = await self.bot.wait_for("message", check=check, timeout=120)
            description = msg.content

            await interaction.channel.send(
                embed=embeds.base_embed(
                    "🎫 Ticket Setup — Step 3/6",
                    "Enter an **embed color** (hex, e.g. #00E5CC).",
                ),
            )
            msg = await self.bot.wait_for("message", check=check, timeout=120)
            try:
                color = int(msg.content.strip("#"), 16)
            except ValueError:
                color = 0x00E5CC

            await interaction.channel.send(
                embed=embeds.base_embed(
                    "🎫 Ticket Setup — Step 4/6",
                    "Mention the **category** where tickets should be created.\n"
                    "(Paste the category ID)",
                ),
            )
            msg = await self.bot.wait_for("message", check=check, timeout=120)
            try:
                category_id = int(msg.content.strip())
            except ValueError:
                category_id = None

            await interaction.channel.send(
                embed=embeds.base_embed(
                    "🎫 Ticket Setup — Step 5/6",
                    "Mention the **support role** (e.g. @Support).",
                ),
            )
            msg = await self.bot.wait_for("message", check=check, timeout=120)
            role = msg.role_mentions[0] if msg.role_mentions else None

            await interaction.channel.send(
                embed=embeds.base_embed(
                    "🎫 Ticket Setup — Step 6/6",
                    "Enter ticket buttons as comma-separated values.\n"
                    "Format: Name:Emoji:Style:Type\n"
                    "Example: Support:🛟:primary:support, Report:🚨:danger:report\n\n"
                    "Styles: primary, secondary, success, danger",
                ),
            )
            msg = await self.bot.wait_for("message", check=check, timeout=120)

            buttons_config = []
            for part in msg.content.split(","):
                parts = [p.strip() for p in part.strip().split(":")]
                if len(parts) >= 4:
                    buttons_config.append({
                        "name": parts[0],
                        "emoji": parts[1],
                        "style": parts[2],
                        "ticket_type": parts[3],
                    })

            if not buttons_config:
                buttons_config = None

            # Save settings
            settings = {}
            if category_id:
                settings["ticket_category_id"] = category_id
            if role:
                settings["support_role_id"] = role.id
            if settings:
                await save_guild_settings(interaction.guild.id, settings)

            # Preview
            preview_embed = embeds.ticket_panel_embed(title, description, color)
            preview_view = TicketPanelView(buttons_config)

            confirm_msg = await interaction.channel.send(
                content="**Preview — Type `confirm` to send or `cancel` to abort.**",
                embed=preview_embed,
                view=preview_view,
            )

            msg = await self.bot.wait_for("message", check=check, timeout=60)

            if msg.content.lower() == "confirm":
                panel_embed = embeds.ticket_panel_embed(title, description, color)
                panel_view = TicketPanelView(buttons_config)
                await interaction.channel.send(embed=panel_embed, view=panel_view)
                await interaction.channel.send(
                    embed=embeds.success_embed("Setup Complete", "Ticket panel has been created!"),
                    delete_after=5,
                )
            else:
                await interaction.channel.send(
                    embed=embeds.warning_embed("Setup Cancelled", "Ticket panel setup was cancelled."),
                    delete_after=5,
                )

        except asyncio.TimeoutError:
            await interaction.channel.send(
                embed=embeds.error_embed("Timeout", "Setup timed out. Please try again."),
            )

    @ticket_group.command(name="panel", description="Send the ticket panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def panel(self, interaction: discord.Interaction):
        view = TicketPanelView()
        embed = embeds.ticket_panel_embed()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            embed=embeds.success_embed("Panel Sent", "Ticket panel has been sent."),
            ephemeral=True,
        )

    @ticket_group.command(name="close", description="Close the current ticket")
    async def close(self, interaction: discord.Interaction):
        ticket = await get_ticket(interaction.guild.id, interaction.channel.id)
        if not ticket:
            await interaction.response.send_message(
                embed=embeds.error_embed("Not a Ticket", "This channel is not a ticket."),
                ephemeral=True,
            )
            return

        owner = interaction.guild.get_member(ticket["ticket_owner_id"])
        if owner:
            await interaction.channel.set_permissions(owner, send_messages=False)
        await update_ticket(interaction.guild.id, interaction.channel.id, ticket_status="closed")
        await interaction.response.send_message(
            embed=embeds.success_embed("Ticket Closed", "This ticket has been closed."),
        )

    @ticket_group.command(name="delete", description="Delete the current ticket")
    @app_commands.checks.has_permissions(administrator=True)
    async def delete(self, interaction: discord.Interaction):
        ticket = await get_ticket(interaction.guild.id, interaction.channel.id)
        if not ticket:
            await interaction.response.send_message(
                embed=embeds.error_embed("Not a Ticket", "This channel is not a ticket."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=embeds.warning_embed("Deleting", "This channel will be deleted in 5 seconds..."),
        )
        await delete_ticket(interaction.guild.id, interaction.channel.id)
        await asyncio.sleep(5)
        await interaction.channel.delete(reason="Ticket deleted via command")

    @ticket_group.command(name="rename", description="Rename the ticket channel")
    @app_commands.describe(name="New channel name")
    async def rename(self, interaction: discord.Interaction, name: str):
        ticket = await get_ticket(interaction.guild.id, interaction.channel.id)
        if not ticket:
            await interaction.response.send_message(
                embed=embeds.error_embed("Not a Ticket", "This channel is not a ticket."),
                ephemeral=True,
            )
            return

        await interaction.channel.edit(name=name)
        await interaction.response.send_message(
            embed=embeds.success_embed("Renamed", f"Channel renamed to **{name}**."),
        )

    @ticket_group.command(name="add", description="Add a member to the ticket")
    @app_commands.describe(user="The user to add")
    async def add(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.channel.set_permissions(
            user, view_channel=True, send_messages=True, read_message_history=True,
        )
        await interaction.response.send_message(
            embed=embeds.success_embed("User Added", f"{user.mention} has been added."),
        )

    @ticket_group.command(name="remove", description="Remove a member from the ticket")
    @app_commands.describe(user="The user to remove")
    async def remove(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(
            embed=embeds.success_embed("User Removed", f"{user.mention} has been removed."),
        )

    @ticket_group.command(name="logs", description="Set the ticket logs channel")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="The logs channel")
    async def logs(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await save_guild_settings(interaction.guild.id, {"logs_channel_id": channel.id})
        await interaction.response.send_message(
            embed=embeds.success_embed("Logs Channel Set", f"Ticket logs will be sent to {channel.mention}."),
        )

    @ticket_group.command(name="category", description="Set the ticket category")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(category_id="The category channel ID")
    async def category(self, interaction: discord.Interaction, category_id: str):
        try:
            cid = int(category_id)
            await save_guild_settings(interaction.guild.id, {"ticket_category_id": cid})
            await interaction.response.send_message(
                embed=embeds.success_embed("Category Set", f"Tickets will be created in category ID: {cid}."),
            )
        except ValueError:
            await interaction.response.send_message(
                embed=embeds.error_embed("Invalid ID", "Please provide a valid category ID."),
                ephemeral=True,
            )

    @ticket_group.command(name="role", description="Set the support role")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="The support role")
    async def role(self, interaction: discord.Interaction, role: discord.Role):
        await save_guild_settings(interaction.guild.id, {"support_role_id": role.id})
        await interaction.response.send_message(
            embed=embeds.success_embed("Support Role Set", f"Support role set to {role.mention}."),
        )

    @ticket_group.command(name="stats", description="View ticket statistics")
    async def stats(self, interaction: discord.Interaction):
        stats = await get_ticket_stats(interaction.guild.id)
        await interaction.response.send_message(embed=embeds.stats_embed(stats))


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketCog(bot))
