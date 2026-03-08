"""
Premium help command with interactive category buttons.
"""

import discord
from discord import app_commands
from discord.ext import commands
from utils import embeds
from utils.views import HelpView


class HelpCog(commands.Cog):
    """Help command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="View all available commands")
    async def help_command(self, interaction: discord.Interaction):
        embed = embeds.base_embed(
            title="📖 Tickets CYX — Help",
            description=(
                "Welcome to the **Tickets CYX** help center!\n\n"
                "Use the buttons below to browse commands by category.\n\n"
                "🎫 **Ticket Commands** — Create & manage tickets\n"
                "⚙️ **Admin Commands** — Server configuration\n"
                "🔧 **Utility** — General bot commands"
            ),
        )
        view = HelpView()
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
