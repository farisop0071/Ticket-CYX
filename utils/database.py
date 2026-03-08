"""
JSON-based database for ticket storage.
Thread-safe async read/write operations.
"""

import json
import os
import asyncio
from typing import Any, Optional

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tickets.json")

_lock = asyncio.Lock()


async def _read_db() -> dict:
    """Read the database file."""
    async with _lock:
        try:
            with open(DATA_PATH, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}


async def _write_db(data: dict) -> None:
    """Write to the database file."""
    async with _lock:
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        with open(DATA_PATH, "w") as f:
            json.dump(data, f, indent=2)


async def save_ticket(
    guild_id: int,
    channel_id: int,
    owner_id: int,
    category: str,
    message_id: int,
    status: str = "open",
    claimed_by: Optional[int] = None,
    priority: str = "normal",
) -> None:
    """Save a ticket to the database."""
    db = await _read_db()
    guild_key = str(guild_id)

    if guild_key not in db:
        db[guild_key] = {"tickets": {}, "settings": {}}

    db[guild_key]["tickets"][str(channel_id)] = {
        "guild_id": guild_id,
        "ticket_channel_id": channel_id,
        "ticket_owner_id": owner_id,
        "ticket_category": category,
        "ticket_message_id": message_id,
        "ticket_status": status,
        "claimed_by": claimed_by,
        "priority": priority,
    }

    await _write_db(db)


async def get_ticket(guild_id: int, channel_id: int) -> Optional[dict]:
    """Get a ticket by channel ID."""
    db = await _read_db()
    guild_key = str(guild_id)
    return db.get(guild_key, {}).get("tickets", {}).get(str(channel_id))


async def update_ticket(guild_id: int, channel_id: int, **kwargs) -> None:
    """Update ticket fields."""
    db = await _read_db()
    guild_key = str(guild_id)
    ticket_key = str(channel_id)

    if guild_key in db and ticket_key in db[guild_key]["tickets"]:
        db[guild_key]["tickets"][ticket_key].update(kwargs)
        await _write_db(db)


async def delete_ticket(guild_id: int, channel_id: int) -> None:
    """Remove a ticket from the database."""
    db = await _read_db()
    guild_key = str(guild_id)
    ticket_key = str(channel_id)

    if guild_key in db and ticket_key in db[guild_key]["tickets"]:
        del db[guild_key]["tickets"][ticket_key]
        await _write_db(db)


async def get_guild_tickets(guild_id: int) -> dict:
    """Get all tickets for a guild."""
    db = await _read_db()
    return db.get(str(guild_id), {}).get("tickets", {})


async def get_guild_settings(guild_id: int) -> dict:
    """Get guild settings."""
    db = await _read_db()
    return db.get(str(guild_id), {}).get("settings", {})


async def save_guild_settings(guild_id: int, settings: dict) -> None:
    """Save guild settings."""
    db = await _read_db()
    guild_key = str(guild_id)

    if guild_key not in db:
        db[guild_key] = {"tickets": {}, "settings": {}}

    db[guild_key]["settings"].update(settings)
    await _write_db(db)


async def get_ticket_stats(guild_id: int) -> dict:
    """Get ticket statistics for a guild."""
    tickets = await get_guild_tickets(guild_id)
    total = len(tickets)
    open_count = sum(1 for t in tickets.values() if t["ticket_status"] == "open")
    closed_count = sum(1 for t in tickets.values() if t["ticket_status"] == "closed")
    claimed_count = sum(1 for t in tickets.values() if t.get("claimed_by"))

    return {
        "total": total,
        "open": open_count,
        "closed": closed_count,
        "claimed": claimed_count,
    }
