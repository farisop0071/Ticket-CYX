"""
Discord UI components (buttons, modals, selects) for Tickets CYX.
"""

import discord
from discord.ui import View, Button, Modal, TextInput, Select
from utils import embeds
from utils.database import (
    save_ticket,
    get_ticket,
    update_ticket,
    delete_ticket,
    get_guild_settings,
)
import asyncio
import time
from utils.config import TICKET_COOLDOWN

# Cooldown tracker: {user_id: last_ticket_timestamp}
_cooldowns: dict[int, float] = {}


class TicketPanelView(View):
    """Persistent view with ticket creation buttons."""

    def __init__(self, buttons_config: list[dict] | None = None):
        super().__init__(timeout=None)

        if buttons_config:
            for btn_cfg in buttons_config:
                style_map = {
                    "primary": discord.ButtonStyle.primary,
                    "secondary": discord.ButtonStyle.secondary,
                    "success": discord.ButtonStyle.success,
                    "danger": discord.ButtonStyle.danger,
                }
                button = Button(
                    label=btn_cfg.get("name", "Ticket"),
                    emoji=btn_cfg.get("emoji", "🎫"),
                    style=style_map.get(btn_cfg.get("style", "primary"), discord.ButtonStyle.primary),
                    custom_id=f"ticket_create_{btn_cfg.get('ticket_type', 'support').lower().replace(' ', '_')}",
                )
                button.callback = self.create_ticket_callback
                self.add_item(button)
        else:
            # Default buttons
            for label, emoji, ticket_type in [
                ("Support", "🛟", "support"),
                ("Report", "🚨", "report"),
                ("Purchase", "💰", "purchase"),
                ("Partnership", "🤝", "partnership"),
            ]:
                button = Button(
                    label=label,
                    emoji=emoji,
                    style=discord.ButtonStyle.primary,
                    custom_id=f"ticket_create_{ticket_type}",
                )
                button.callback = self.create_ticket_callback
                self.add_item(button)

    async def create_ticket_callback(self, interaction: discord.Interaction):
        """Handle ticket creation button press."""
        user = interaction.user
        guild = interaction.guild

        # Cooldown check
        now = time.time()
        last = _cooldowns.get(user.id, 0)
        if now - last < TICKET_COOLDOWN:
            remaining = int(TICKET_COOLDOWN - (now - last))
            await interaction.response.send_message(
                embed=embeds.error_embed(
                    "Cooldown Active",
                    f"Please wait **{remaining}s** before creating another ticket.",
                ),
                ephemeral=True,
            )
            return
        _cooldowns[user.id] = now

        # Extract ticket type from custom_id
        ticket_type = interaction.data.get("custom_id", "ticket_create_support").replace("ticket_create_", "").replace("_", " ").title()

        settings = await get_guild_settings(guild.id)
        category_id = settings.get("ticket_category_id")
        support_role_id = settings.get("support_role_id")

        category = guild.get_channel(category_id) if category_id else None

        # Build overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
                read_message_history=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
            ),
        }

        if support_role_id:
            role = guild.get_role(support_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    attach_files=True,
                    read_message_history=True,
                )

        # Create channel
        channel_name = f"ticket-{user.name.lower()}"
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket created by {user}",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=embeds.error_embed("Permission Error", "I lack permissions to create channels."),
                ephemeral=True,
            )
            return

        # Send welcome embed with controls
        welcome = embeds.ticket_welcome_embed(user, ticket_type, guild.name)
        view = TicketControlView()
        msg = await channel.send(
            content=f"<@&{support_role_id}>" if support_role_id else None,
            embed=welcome,
            view=view,
        )

        # Save to DB
        await save_ticket(
            guild_id=guild.id,
            channel_id=channel.id,
            owner_id=user.id,
            category=ticket_type,
            message_id=msg.id,
        )

        await interaction.response.send_message(
            embed=embeds.success_embed("Ticket Created", f"Your ticket has been created: {channel.mention}"),
            ephemeral=True,
        )


class TicketControlView(View):
    """Buttons shown inside a ticket channel for management."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        confirm_view = ConfirmView("close")
        await interaction.response.send_message(
            embed=embeds.warning_embed("Close Ticket", "Are you sure you want to close this ticket?"),
            view=confirm_view,
            ephemeral=True,
        )

    @discord.ui.button(label="Claim", emoji="✋", style=discord.ButtonStyle.success, custom_id="ticket_claim")
    async def claim_ticket(self, interaction: discord.Interaction, button: Button):
        ticket = await get_ticket(interaction.guild.id, interaction.channel.id)
        if not ticket:
            await interaction.response.send_message(embed=embeds.error_embed("Error", "Ticket not found."), ephemeral=True)
            return

        await update_ticket(interaction.guild.id, interaction.channel.id, claimed_by=interaction.user.id)
        await interaction.response.send_message(
            embed=embeds.success_embed("Ticket Claimed", f"This ticket has been claimed by {interaction.user.mention}."),
        )

    @discord.ui.button(label="Add User", emoji="➕", style=discord.ButtonStyle.secondary, custom_id="ticket_add_user")
    async def add_user(self, interaction: discord.Interaction, button: Button):
        modal = UserInputModal(action="add")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Remove User", emoji="➖", style=discord.ButtonStyle.secondary, custom_id="ticket_remove_user")
    async def remove_user(self, interaction: discord.Interaction, button: Button):
        modal = UserInputModal(action="remove")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Lock", emoji="🔐", style=discord.ButtonStyle.secondary, custom_id="ticket_lock")
    async def lock_ticket(self, interaction: discord.Interaction, button: Button):
        ticket = await get_ticket(interaction.guild.id, interaction.channel.id)
        if not ticket:
            return

        owner = interaction.guild.get_member(ticket["ticket_owner_id"])
        if owner:
            await interaction.channel.set_permissions(owner, send_messages=False)

        await interaction.response.send_message(
            embed=embeds.success_embed("Ticket Locked", "The ticket owner can no longer send messages."),
        )

    @discord.ui.button(label="Unlock", emoji="🔓", style=discord.ButtonStyle.secondary, custom_id="ticket_unlock")
    async def unlock_ticket(self, interaction: discord.Interaction, button: Button):
        ticket = await get_ticket(interaction.guild.id, interaction.channel.id)
        if not ticket:
            return

        owner = interaction.guild.get_member(ticket["ticket_owner_id"])
        if owner:
            await interaction.channel.set_permissions(owner, send_messages=True)

        await interaction.response.send_message(
            embed=embeds.success_embed("Ticket Unlocked", "The ticket owner can send messages again."),
        )

    @discord.ui.button(label="Transcript", emoji="📝", style=discord.ButtonStyle.secondary, custom_id="ticket_transcript")
    async def transcript(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        messages = []
        async for msg in interaction.channel.history(limit=500, oldest_first=True):
            messages.append(msg)

        # Generate HTML transcript
        html = generate_transcript_html(messages, interaction.channel.name)
        filename = f"transcript-{interaction.channel.name}.html"

        file = discord.File(
            fp=__import__("io").BytesIO(html.encode()),
            filename=filename,
        )

        ticket = await get_ticket(interaction.guild.id, interaction.channel.id)
        owner = interaction.guild.get_member(ticket["ticket_owner_id"]) if ticket else interaction.user

        settings = await get_guild_settings(interaction.guild.id)
        logs_channel_id = settings.get("logs_channel_id")

        if logs_channel_id:
            logs_channel = interaction.guild.get_channel(logs_channel_id)
            if logs_channel:
                await logs_channel.send(
                    embed=embeds.transcript_embed(interaction.channel.name, owner, len(messages)),
                    file=file,
                )

        await interaction.followup.send(
            embed=embeds.success_embed("Transcript Generated", f"Saved {len(messages)} messages."),
            ephemeral=True,
        )

    @discord.ui.button(label="Delete", emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="ticket_delete")
    async def delete_ticket(self, interaction: discord.Interaction, button: Button):
        confirm_view = ConfirmView("delete")
        await interaction.response.send_message(
            embed=embeds.warning_embed("Delete Ticket", "This ticket will be deleted in 5 seconds. Are you sure?"),
            view=confirm_view,
            ephemeral=True,
        )


class ConfirmView(View):
    """Confirmation dialog for destructive actions."""

    def __init__(self, action: str):
        super().__init__(timeout=30)
        self.action = action

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger, custom_id="confirm_yes")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if self.action == "close":
            ticket = await get_ticket(interaction.guild.id, interaction.channel.id)
            if ticket:
                owner = interaction.guild.get_member(ticket["ticket_owner_id"])
                if owner:
                    await interaction.channel.set_permissions(owner, send_messages=False)
                await update_ticket(interaction.guild.id, interaction.channel.id, ticket_status="closed")

            await interaction.response.send_message(
                embed=embeds.success_embed("Ticket Closed", "This ticket has been closed."),
            )

        elif self.action == "delete":
            await interaction.response.send_message(
                embed=embeds.warning_embed("Deleting", "This channel will be deleted in 5 seconds..."),
            )
            await delete_ticket(interaction.guild.id, interaction.channel.id)
            await asyncio.sleep(5)
            await interaction.channel.delete(reason="Ticket deleted")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="confirm_no")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            embed=embeds.success_embed("Cancelled", "Action cancelled."),
            ephemeral=True,
        )


class UserInputModal(Modal):
    """Modal for adding/removing a user from a ticket."""

    def __init__(self, action: str):
        super().__init__(title=f"{'Add' if action == 'add' else 'Remove'} User")
        self.action = action
        self.user_input = TextInput(
            label="User ID or Mention",
            placeholder="Enter user ID (e.g. 123456789)",
            required=True,
        )
        self.add_item(self.user_input)

    async def on_submit(self, interaction: discord.Interaction):
        user_id_str = self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", "")
        try:
            user_id = int(user_id_str)
        except ValueError:
            await interaction.response.send_message(
                embed=embeds.error_embed("Invalid Input", "Please provide a valid user ID."),
                ephemeral=True,
            )
            return

        member = interaction.guild.get_member(user_id)
        if not member:
            await interaction.response.send_message(
                embed=embeds.error_embed("User Not Found", "Could not find that user in this server."),
                ephemeral=True,
            )
            return

        if self.action == "add":
            await interaction.channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )
            await interaction.response.send_message(
                embed=embeds.success_embed("User Added", f"{member.mention} has been added to the ticket."),
            )
        else:
            await interaction.channel.set_permissions(member, overwrite=None)
            await interaction.response.send_message(
                embed=embeds.success_embed("User Removed", f"{member.mention} has been removed from the ticket."),
            )


class HelpView(View):
    """Paginated help menu with category buttons."""

    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="Ticket Commands", emoji="🎫", style=discord.ButtonStyle.primary, custom_id="help_tickets")
    async def ticket_help(self, interaction: discord.Interaction, button: Button):
        commands = [
            {"name": "ticket setup", "description": "Interactive ticket panel setup wizard", "usage": "/ticket setup"},
            {"name": "ticket panel", "description": "Re-send the ticket panel", "usage": "/ticket panel"},
            {"name": "ticket close", "description": "Close the current ticket", "usage": "/ticket close"},
            {"name": "ticket delete", "description": "Delete the current ticket", "usage": "/ticket delete"},
            {"name": "ticket rename", "description": "Rename the ticket channel", "usage": "/ticket rename <name>"},
        ]
        await interaction.response.edit_message(embed=embeds.help_embed("Ticket Commands", commands), view=self)

    @discord.ui.button(label="Admin Commands", emoji="⚙️", style=discord.ButtonStyle.secondary, custom_id="help_admin")
    async def admin_help(self, interaction: discord.Interaction, button: Button):
        commands = [
            {"name": "ticket add", "description": "Add a member to the ticket", "usage": "/ticket add <user>"},
            {"name": "ticket remove", "description": "Remove a member from the ticket", "usage": "/ticket remove <user>"},
            {"name": "ticket logs", "description": "Set the ticket logs channel", "usage": "/ticket logs <channel>"},
            {"name": "ticket category", "description": "Set the ticket category", "usage": "/ticket category <category>"},
            {"name": "ticket role", "description": "Set the support role", "usage": "/ticket role <role>"},
            {"name": "ticket stats", "description": "View ticket statistics", "usage": "/ticket stats"},
        ]
        await interaction.response.edit_message(embed=embeds.help_embed("Admin Commands", commands), view=self)

    @discord.ui.button(label="Utility", emoji="🔧", style=discord.ButtonStyle.secondary, custom_id="help_utility")
    async def utility_help(self, interaction: discord.Interaction, button: Button):
        commands = [
            {"name": "help", "description": "Show this help menu", "usage": "/help"},
        ]
        await interaction.response.edit_message(embed=embeds.help_embed("Utility Commands", commands), view=self)


def generate_transcript_html(messages: list, channel_name: str) -> str:
    """Generate an HTML transcript of ticket messages."""
    rows = ""
    for msg in messages:
        avatar = msg.author.display_avatar.url if msg.author.display_avatar else ""
        content = msg.content.replace("<", "&lt;").replace(">", "&gt;") if msg.content else "<em>No text content</em>"
        attachments = "".join(f'<br><a href="{a.url}">{a.filename}</a>' for a in msg.attachments)
        rows += f"""
        <div class="message">
            <img src="{avatar}" class="avatar" />
            <div class="content">
                <span class="author">{msg.author.display_name}</span>
                <span class="timestamp">{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}</span>
                <p>{content}{attachments}</p>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Transcript - #{channel_name}</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; background: #1a1b1e; color: #dcddde; margin: 0; padding: 20px; }}
h1 {{ color: #00e5cc; border-bottom: 2px solid #00e5cc33; padding-bottom: 10px; }}
.message {{ display: flex; gap: 12px; padding: 8px 16px; border-radius: 4px; }}
.message:hover {{ background: #2a2b2f; }}
.avatar {{ width: 40px; height: 40px; border-radius: 50%; }}
.author {{ color: #00e5cc; font-weight: 600; margin-right: 8px; }}
.timestamp {{ color: #72767d; font-size: 0.75em; }}
.content p {{ margin: 4px 0 0; }}
a {{ color: #00aff4; }}
</style>
</head>
<body>
<h1>📝 Transcript — #{channel_name}</h1>
<p style="color:#72767d;">Generated by Tickets CYX</p>
{rows}
</body>
</html>"""
