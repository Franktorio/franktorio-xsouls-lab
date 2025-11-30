# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# On message event handler

# Standard library imports
import io
import json

# Third-party imports
import discord
from discord.ext import commands
from discord import app_commands

# Local imports
import shared
from src import datamanager
import config.vars as vars

@shared.FRD_bot.event
async def on_message(message: discord.Message):
    """Event handler for new messages."""
    # Ignore messages from bots
    if message.author.bot:
        return

    # Check if message was sent in the guild's research or leaderboard channel
    guild_id = message.guild.id if message.guild else None
    if not guild_id:
        return
    profile = datamanager.server_profiler.get_server_profile(guild_id)
    if not profile:
        return
    
    research_channel_id = profile.get('documented_channel_id')
    leaderboard_channel_id = profile.get('leaderboard_channel_id')
    
    if message.channel.id not in [research_channel_id, leaderboard_channel_id]:
        return
    else:
        await message.delete()


