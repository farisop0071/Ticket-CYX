"""
Configuration loader for Tickets CYX.
Loads environment variables from .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
BOT_NAME: str = os.getenv("BOT_NAME", "Tickets CYX")
BOT_STATUS: str = os.getenv("BOT_STATUS", "Watching your support requests")
OWNER_ID: str = os.getenv("OWNER_ID", "")
TICKET_LOGS_CHANNEL_ID: str = os.getenv("TICKET_LOGS_CHANNEL_ID", "")

# Theme color (cyan/teal)
EMBED_COLOR = 0x00E5CC
ERROR_COLOR = 0xFF4444
SUCCESS_COLOR = 0x00E5CC
WARNING_COLOR = 0xFFAA00

# Ticket cooldown in seconds
TICKET_COOLDOWN = 60

# Auto-close inactivity timeout in seconds (24 hours)
INACTIVITY_TIMEOUT = 86400
