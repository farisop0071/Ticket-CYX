"""
Admin-only commands for bot management.
"""

import discord
from discord import app_commands
from discord.ext import commands
from utils import embeds


class AdminCog(commands.Cog):
    """Administrative commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sync", description="Sync slash commands (owner only)")
    async def sync_commands(self, interaction: discord.Interaction):
        from utils.config import OWNER_ID
        if str(interaction.user.id) != OWNER_ID:
            await interaction.response.send_message(
                embed=embeds.error_embed("Permission Denied", "Only the bot owner can use this command."),
                ephemeral=True,
            )
            return

        await self.bot.tree.sync()
        await interaction.response.send_message(
            embed=embeds.success_embed("Synced", "Slash commands have been synced globally."),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
