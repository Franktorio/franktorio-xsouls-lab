# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# On message event handler

PRINT_PREFIX = "MESSAGE EVENTS"

# Standard library imports
import time
import asyncio
import re

# Third-party imports
import discord

# Local imports
from src import datamanager, shared
from src.utils import embeds

_ROOM_INFO_TIMER = 120 # seconds
all_room_names_cache = []
last_room_info_time = 0

_PER_CHANNEL_COOLDOWN_TIME = 5 # Only allow one room info request per channel every 5 seconds
per_channel_cooldown = {}

# Locks
per_channel_cooldown_lock = asyncio.Lock()
all_room_names_cache_lock = asyncio.Lock()

@shared.FRD_bot.event
async def on_message(message: discord.Message):
    """Event handler for new messages."""
    global last_room_info_time, _ROOM_INFO_TIMER, all_room_names_cache, per_channel_cooldown, _PER_CHANNEL_COOLDOWN_TIME, per_channel_cooldown_lock, all_room_names_cache_lock
    # Ignore messages from bots
    if message.author.bot:
        return

    # Check if message was sent in the guild's research or leaderboard channel
    guild_id = message.guild.id if message.guild else None
    if not guild_id:
        return
    profile = datamanager.server_db_handler.get_server_profile(guild_id)
    if not profile:
        return
    
    research_channel_id = profile.get('documented_channel_id')
    leaderboard_channel_id = profile.get('leaderboard_channel_id')
    
    if message.channel.id in [research_channel_id, leaderboard_channel_id]:
        await message.delete()
        print(f"[INFO] [{PRINT_PREFIX}] Deleted message in documented or leaderboard channel in server '{message.guild.name}' from user '{message.author}'.")
        return

    # Check if its time to refresh room names cache
    time_now = time.time()
    async with all_room_names_cache_lock:
        if time_now - last_room_info_time > _ROOM_INFO_TIMER:
            all_room_names_cache = datamanager.room_db_handler.get_all_room_names()
            last_room_info_time = time_now
            print(f"[INFO] [{PRINT_PREFIX}] Refreshed room names cache with {len(all_room_names_cache)} entries for on_message.")

    # Expire per-channel cooldowns
    async with per_channel_cooldown_lock:
        expired_channels = [channel for channel, timestamp in per_channel_cooldown.items() if time_now - timestamp > _PER_CHANNEL_COOLDOWN_TIME]
        for channel in expired_channels:
            del per_channel_cooldown[channel]

    content = message.content

    for room_name in all_room_names_cache:
        if message.channel in per_channel_cooldown:
            break

        escaped = re.escape(room_name)
        pattern = rf'\b{escaped}\b'

        if re.search(pattern, content, re.IGNORECASE):
            room_info = datamanager.room_db_handler.get_roominfo(room_name)
            if not room_info:
                return

            await embeds.send_room_documentation_embed(message.channel, room_info)
            print(f"[INFO] [{PRINT_PREFIX}] Sent room info for room '{room_name}' in response to message from user '{message.author}' in server '{message.guild.name}'.")

            async with per_channel_cooldown_lock:
                per_channel_cooldown[message.channel] = time_now
            break

