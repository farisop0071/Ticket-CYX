"""
Tickets CYX — Premium Discord Ticket Bot
Main entry point. Loads cogs and events, then starts the bot.
"""

import discord
from discord.ext import commands
import asyncio
import os
from utils.config import BOT_TOKEN, BOT_NAME

# Bot setup with required intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",  # Fallback prefix (slash commands are primary)
    intents=intents,
    help_command=None,  # Disable default help
)

# Extensions to load
EXTENSIONS = [
    "cogs.ticket",
    "cogs.admin",
    "cogs.help",
    "events.on_ready",
    "events.on_interaction",
]


async def load_extensions():
    """Load all cog and event extensions."""
    for ext in EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"  ✅ Loaded: {ext}")
        except Exception as e:
            print(f"  ❌ Failed to load {ext}: {e}")


async def main():
    """Main async entry point."""
    print(f"\n🚀 Starting {BOT_NAME}...\n")

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    if not os.path.exists("data/tickets.json"):
        with open("data/tickets.json", "w") as f:
            f.write("{}")

    async with bot:
        await load_extensions()
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
