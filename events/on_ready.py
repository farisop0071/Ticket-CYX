"""
Event handler for bot ready state.
"""

import discord
from discord.ext import commands
from utils.config import BOT_STATUS, BOT_NAME
from utils.views import TicketPanelView, TicketControlView


class OnReady(commands.Cog):
    """Handles the on_ready event."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Set activity
        activity = discord.Activity(type=discord.ActivityType.watching, name=BOT_STATUS)
        await self.bot.change_presence(activity=activity)

        # Register persistent views
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(TicketControlView())

        print(f"{'='*40}")
        print(f"  {BOT_NAME} is online!")
        print(f"  Guilds: {len(self.bot.guilds)}")
        print(f"  Users: {len(self.bot.users)}")
        print(f"{'='*40}")


async def setup(bot: commands.Bot):
    await bot.add_cog(OnReady(bot))
