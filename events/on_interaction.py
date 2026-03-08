"""
Fallback interaction handler for custom_id routing.
Most interactions are handled by persistent views, but this catches edge cases.
"""

import discord
from discord.ext import commands
from utils import embeds


class OnInteraction(commands.Cog):
    """Handles fallback interactions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # Only handle component interactions not caught by views
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")

        # Log unhandled interactions for debugging
        if not interaction.response.is_done():
            pass  # Handled by persistent views


async def setup(bot: commands.Bot):
    await bot.add_cog(OnInteraction(bot))
