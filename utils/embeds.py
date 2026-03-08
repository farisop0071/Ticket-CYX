"""
Premium styled embed builders for Tickets CYX.
All bot responses use these helpers for consistent branding.
"""

import discord
from datetime import datetime
from utils.config import EMBED_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, BOT_NAME


def base_embed(
    title: str,
    description: str,
    color: int = EMBED_COLOR,
) -> discord.Embed:
    """Create a base embed with branding."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow(),
    )
    embed.set_footer(text=f"{BOT_NAME} • Support System")
    return embed


def success_embed(title: str, description: str) -> discord.Embed:
    """Green/cyan success embed."""
    return base_embed(f"✅ {title}", description, SUCCESS_COLOR)


def error_embed(title: str, description: str) -> discord.Embed:
    """Red error embed."""
    return base_embed(f"❌ {title}", description, ERROR_COLOR)


def warning_embed(title: str, description: str) -> discord.Embed:
    """Yellow warning embed."""
    return base_embed(f"⚠️ {title}", description, WARNING_COLOR)


def ticket_welcome_embed(
    user: discord.Member,
    category: str,
    guild_name: str,
) -> discord.Embed:
    """Welcome embed sent when a ticket is created."""
    embed = base_embed(
        title="🎫 Ticket Opened",
        description=(
            f"Welcome {user.mention}!\n\n"
            f"**Category:** {category}\n"
            f"**Server:** {guild_name}\n\n"
            "Please describe your issue and a staff member will assist you shortly.\n"
            "Use the buttons below to manage your ticket."
        ),
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    return embed


def ticket_panel_embed(
    title: str = "🎫 Support Tickets",
    description: str = "Click a button below to create a ticket.",
    color: int = EMBED_COLOR,
) -> discord.Embed:
    """The main ticket panel embed."""
    return base_embed(title, description, color)


def transcript_embed(
    channel_name: str,
    owner: discord.Member,
    message_count: int,
) -> discord.Embed:
    """Embed sent with transcript file."""
    return base_embed(
        title="📝 Ticket Transcript",
        description=(
            f"**Channel:** #{channel_name}\n"
            f"**Owner:** {owner.mention}\n"
            f"**Messages:** {message_count}"
        ),
    )


def stats_embed(stats: dict) -> discord.Embed:
    """Ticket statistics embed."""
    return base_embed(
        title="📊 Ticket Statistics",
        description=(
            f"**Total Tickets:** {stats['total']}\n"
            f"**Open:** {stats['open']}\n"
            f"**Closed:** {stats['closed']}\n"
            f"**Claimed:** {stats['claimed']}"
        ),
    )


def help_embed(category: str, commands: list[dict]) -> discord.Embed:
    """Help menu embed for a category."""
    desc_lines = []
    for cmd in commands:
        desc_lines.append(
            f"**/{cmd['name']}**\n"
            f"> {cmd['description']}\n"
            f"> Usage: `{cmd['usage']}`\n"
        )

    return base_embed(
        title=f"📖 Help — {category}",
        description="\n".join(desc_lines),
    )
