# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Background task to build documented channels

PRINT_PREFIX = "LEADERBOARD SYNC"

# Third-party imports
import discord
from discord.ext import tasks

# Local imports
from src import datamanager, shared
from src.datamanager.db_handlers.action_json_handler import actions_data, save_actions_json
from src.utils import embeds, utils

@tasks.loop(minutes=1)
async def update_leaderboard():
    """Background task to update the leaderboards."""

    
    # Iterate through all guilds the bot is in
    for guild in shared.FRD_bot.guilds:
        # Get server profile to find leaderboard channel
        profile = datamanager.server_db_handler.get_server_profile(guild.id)
        if not profile or not profile.get('leaderboard_channel_id'):
            continue

        leaderboard_channel = guild.get_channel(profile['leaderboard_channel_id'])
        if not leaderboard_channel:
            print(f"[WARNING] [{PRINT_PREFIX}] Leaderboard channel not found in server {guild.name}, clearing configuration")
            datamanager.server_db_handler.update_server_profile(
                server_id=guild.id,
                leaderboard_channel_id=0
            )
            continue

        message_id = actions_data.get("leaderboard_messages", {}).get(str(guild.id))
        if not message_id:
            print(f"[INFO] [{PRINT_PREFIX}] Leaderboard message ID not found in server {guild.id}. Creating a new one.")
            # Send initial leaderboard message
            message = await leaderboard_channel.send("Initializing leaderboard...")
            message_id = message.id
            if "leaderboard_messages" not in actions_data:
                actions_data["leaderboard_messages"] = {}
            actions_data["leaderboard_messages"][str(guild.id)] = str(message_id)
            save_actions_json()

        try:
            message = await leaderboard_channel.fetch_message(message_id)
        except discord.NotFound:
            print(f"[INFO] [{PRINT_PREFIX}] Leaderboard message not found in server {guild.id}. Creating a new one.")
            # Send initial leaderboard message
            message = await leaderboard_channel.send("Initializing leaderboard...")
            message_id = message.id
            if "leaderboard_messages" not in actions_data:
                actions_data["leaderboard_messages"] = {}
            actions_data["leaderboard_messages"][str(guild.id)] = str(message_id)
            save_actions_json()
        
        rooms = datamanager.room_db_handler.jsonify_room_db()["room_db"]
        top_10 = {}
        for room in rooms:
            room = rooms[room]
            documenter = room.get('doc_by_user_id')
            top_10[documenter] = top_10.get(documenter, 0) + 1
        # Sort the top 10 contributors
        top_10 = dict(sorted(top_10.items(), key=lambda item: item[1], reverse=True)[:10])

        # Update the leaderboard message
        await message.edit(embed=embeds.create_leaderboard_embed(top_10), content=None)