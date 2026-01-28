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
from src.utils.embeds import create_small_room_documentation_embed

_ROOM_INFO_TIMER = 120 # seconds
all_room_names_cache = []
last_room_info_time = 0

_PER_CHANNEL_COOLDOWN_TIME = 600 # Only allow the same room to be sent in a channel every 10 minutes (600 seconds)
per_channel_room_cooldown = {}  # Dict of {channel_id: {room_name: timestamp}}

# Locks
per_channel_room_cooldown_lock = asyncio.Lock()
all_room_names_cache_lock = asyncio.Lock()

COMMON_ROOMS_TO_SKIP = set(["start", "000"])

@shared.FRD_bot.event
async def on_message(message: discord.Message):
    """Event handler for new messages."""
    global last_room_info_time, _ROOM_INFO_TIMER, all_room_names_cache, per_channel_room_cooldown, _PER_CHANNEL_COOLDOWN_TIME, per_channel_room_cooldown_lock, all_room_names_cache_lock
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

    # Expire per-channel per-room cooldowns
    async with per_channel_room_cooldown_lock:
        for channel_id in list(per_channel_room_cooldown.keys()):
            expired_rooms = [room for room, timestamp in per_channel_room_cooldown[channel_id].items() if time_now - timestamp > _PER_CHANNEL_COOLDOWN_TIME]
            for room in expired_rooms:
                del per_channel_room_cooldown[channel_id][room]
            # Clean up empty channel entries
            if not per_channel_room_cooldown[channel_id]:
                del per_channel_room_cooldown[channel_id]

    # Remove quotation marks to allow matching room names within quotes
    content = message.content.replace('"', '').replace("'", '').replace('"', '').replace('"', '')
    
    # Split message into individual words
    words = content.split()

    for room_name in all_room_names_cache:
        # Check if this specific room is on cooldown in this channel
        channel_id = message.channel.id
        async with per_channel_room_cooldown_lock:
            if channel_id in per_channel_room_cooldown and room_name in per_channel_room_cooldown[channel_id]:
                continue

        # Check if any word matches the room name (case-insensitive)
        room_found = False
        for word in words:
            if word.lower() == room_name.lower():
                room_found = True
                break
        
        if room_found:
            room_info = datamanager.room_db_handler.get_roominfo(room_name)
            if not room_info:
                return

            if room_name.lower() in COMMON_ROOMS_TO_SKIP:
                # Skip common rooms to reduce spam
                return

            # Send small embed
            embed = create_small_room_documentation_embed(room_info, guild_id, message.author.display_avatar.url, str(message.author))
            await message.channel.send(embed=embed)
            print(f"[INFO] [{PRINT_PREFIX}] Sent room info for room '{room_name}' in response to message from user '{message.author}' in server '{message.guild.name}'.")

            # Set cooldown for this specific room in this channel
            async with per_channel_room_cooldown_lock:
                if channel_id not in per_channel_room_cooldown:
                    per_channel_room_cooldown[channel_id] = {}
                per_channel_room_cooldown[channel_id][room_name] = time_now
            break

