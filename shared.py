# Franktorio's Research Division
# Author: Franktorio
# November 8th, 2025
# Shared module for bot instance

"""
Shared module to hold the bot instance.
This avoids circular imports by providing a central location
that can be imported by any module without triggering bot.py execution.
"""

from typing import Optional
from discord.ext import commands

# Global bot instance (will be set during bot initialization)
FRD_bot: Optional[commands.Bot] = None


def set_bot(bot: commands.Bot) -> None:
    """
    Set the global bot instance.
    Should only be called once by bot.py during initialization.
    """
    global FRD_bot
    FRD_bot = bot


def get_bot() -> commands.Bot:
    """
    Get the global bot instance.
    Raises RuntimeError if bot hasn't been initialized yet.
    """
    if FRD_bot is None:
        raise RuntimeError("Bot has not been initialized yet. Call set_bot() first.")
    return FRD_bot
