# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Background task to build documented channels

PRINT_PREFIX = "DOCUMENTED BUILDER"

# Standard library imports
import asyncio

# Third-party imports
import discord
from discord.ext import tasks

# Local imports
from src import datamanager, shared
from src.utils import embeds

# Configuration
BATCH_SIZE = 50  # Number of rooms to process concurrently per server
currently_running_builds = []

_force_fetch_iterations = 0
_MAX_FORCE_FETCH = 5

@tasks.loop(minutes=1)
async def build_documented_channels():
    """Background task to sync documented channels with room database."""
    global _force_fetch_iterations
    
    print(f"[INFO] [{PRINT_PREFIX}] Starting documented channel sync cycle")
    # Get all rooms from database
    all_rooms = datamanager.room_db_handler.get_all_room_names(sort_by="last_updated")
    
    if not all_rooms:
        print(f"[INFO] [{PRINT_PREFIX}] No rooms found in database, skipping sync")
        return
    
    # Forcefully load guilds to ensure cache is populated
    _force_fetch_iterations += 1
    if _force_fetch_iterations >= _MAX_FORCE_FETCH:
        _force_fetch_iterations = 0
        async for _ in shared.FRD_bot.fetch_guilds():
            pass
    
    print(f"[INFO] [{PRINT_PREFIX}] Processing {len(shared.FRD_bot.guilds)} guild(s) for sync")
    for guild in shared.FRD_bot.guilds:
        asyncio.create_task(_sync_server_documentation(guild, all_rooms))
    

async def _sync_server_documentation(guild: discord.Guild, all_rooms: list):
    """Sync a server's documented channel with the room database."""
    server_id = guild.id
    
    # Check if already running
    if server_id in currently_running_builds:
        return  # Skip if a build is already running for this server
    
    try:
        currently_running_builds.append(server_id)
        
        # Get server profile
        profile = datamanager.server_db_handler.get_server_profile(server_id)
        if not profile or not profile.get('documented_channel_id'):
            # Commented out because it clogs logs unnecessarily
            # print(f"[{PRINT_PREFIX}] No documented channel configured for {guild.name}")
            return
        
        # Store the initial channel ID to detect if setup runs again mid-sync
        initial_channel_id = profile['documented_channel_id']
        
        # Try to get channel from cache first, then fetch if not available
        documented_channel = guild.get_channel(profile['documented_channel_id'])
        if not documented_channel:
            try:
                documented_channel = await guild.fetch_channel(profile['documented_channel_id'])
            except discord.NotFound:
                # Clear the channel ID and doc IDs but keep the profile (preserves leaderboard channel, etc.)
                print(f"[WARNING] [{PRINT_PREFIX}] Documented channel not found for {guild.name}, clearing configuration")
                datamanager.server_db_handler.update_server_profile(
                    server_id=server_id,
                    documented_channel_id=0,
                    doc_msg_ids={}
                )
                return  # Stop processing this server immediately
            except Exception as e:
                print(f"[ERROR] [{PRINT_PREFIX}] Error fetching channel in server {guild.name}: {e}")
                return  # Stop processing this server immediately
        
        # Get current documented rooms in this server
        current_doc_ids = profile.get('doc_msg_ids', {})
        
        # Find rooms that need to be added or updated
        rooms_to_process = []
        for room_name in all_rooms:
            room_info = datamanager.room_db_handler.get_roominfo(room_name)
            if not room_info:
                continue
                
            # Check if room needs to be added or updated
            if room_name not in current_doc_ids:
                rooms_to_process.append(room_name)
            else:
                # Check if room was updated (compare timestamps if available)
                # For now, we'll skip already documented rooms unless explicitly requested
                pass
        
        # Find rooms that were deleted from database but still in server
        rooms_to_delete = []
        for room_name in current_doc_ids.keys():
            if room_name not in all_rooms:
                rooms_to_delete.append(room_name)
        
        # Delete removed rooms
        for room_name in rooms_to_delete:
            await _delete_room_documentation(room_name, documented_channel, server_id, guild)
        
        if not rooms_to_process:
            return  # Nothing to update
        
        print(f"[INFO] [{PRINT_PREFIX}] Found {len(rooms_to_process)} new rooms to document in {guild.name}")
        
        # Process rooms in batches
        for i in range(0, len(rooms_to_process), BATCH_SIZE):
            # Double-check profile still exists and channel ID hasn't changed (in case setup was run again)
            current_profile = datamanager.server_db_handler.get_server_profile(server_id)
            if not current_profile:
                print(f"[WARNING] [{PRINT_PREFIX}] Server profile deleted mid-sync for {guild.name}, stopping.")
                return
            
            if current_profile.get('documented_channel_id') != initial_channel_id:
                print(f"[WARNING] [{PRINT_PREFIX}] Channel ID changed mid-sync for {guild.name} (setup was run again), stopping old sync.")
                return
            
            batch = rooms_to_process[i:i+BATCH_SIZE] if len(rooms_to_process) > BATCH_SIZE else rooms_to_process[i:]
            tasks_to_run = []
            
            for room_name in batch:
                task = _process_single_room(
                    room_name=room_name,
                    documented_channel=documented_channel,
                    server_id=server_id,
                    guild=guild
                )
                tasks_to_run.append(task)
            
            # Process batch concurrently
            await asyncio.gather(*tasks_to_run, return_exceptions=True)
        
        print(f"[INFO] [{PRINT_PREFIX}] Completed sync for {guild.name}")
        
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error syncing server {guild.name}: {e}")
    finally:
        # Always remove from running builds list
        if server_id in currently_running_builds:
            currently_running_builds.remove(server_id)


async def _delete_room_documentation(room_name: str, documented_channel: discord.TextChannel, server_id: int, guild: discord.Guild):
    """Delete a room's documentation message from a server."""
    try:
        msg_id = datamanager.server_db_handler.get_doc_message_id(server_id, room_name)
        if msg_id:
            try:
                message = await documented_channel.fetch_message(msg_id)
                await message.delete()
                print(f"[INFO] [{PRINT_PREFIX}] Deleted '{room_name}' from server {guild.name} ({server_id})")
            except discord.NotFound:
                print(f"[INFO] [{PRINT_PREFIX}] Message for '{room_name}' already deleted in {guild.name}")
            
            # Remove from server profile
            datamanager.server_db_handler.remove_doc_id(server_id, room_name)
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error deleting '{room_name}' from server {server_id}: {e}")


async def _process_single_room(room_name: str, documented_channel: discord.TextChannel, server_id: int, guild: discord.Guild) -> bool:
    """Process a single room documentation. Returns True on success, False on failure."""
    try:
        # Get room info from database
        room_info = datamanager.room_db_handler.get_roominfo(room_name)
        if not room_info:
            print(f"[WARNING] [{PRINT_PREFIX}] Room '{room_name}' not found in database")
            return True  # Remove from queue anyway
        
        if not datamanager.server_db_handler.get_server_profile(server_id):
            return True
        
        # Check if room already has a message in this server
        existing_msg_id = datamanager.server_db_handler.get_doc_message_id(server_id, room_name)
        
        if existing_msg_id:
            # Update existing message
            try:
                message = await documented_channel.fetch_message(existing_msg_id)
                
                # Prepare room data
                room_data = {
                    "room_name": room_info['room_name'],
                    "description": room_info['description'],
                    "tags": room_info['tags'],
                    "roomtype": room_info.get('roomtype', 'Unknown - Please update!'),
                    "picture_urls": room_info['picture_urls'],
                    "doc_by_user_id": room_info['doc_by_user_id'],
                    "last_updated": room_info['last_updated']
                }
                
                # Delete old message and send new one (to update images)
                await message.delete()
                message_id = await embeds.send_room_documentation_embed(documented_channel, room_data)
                datamanager.server_db_handler.add_doc_id(server_id, room_name, message_id)
                
                print(f"[INFO] [{PRINT_PREFIX}] Updated '{room_name}' in server {guild.name} ({server_id})")
                return True
                
            except discord.NotFound:
                # Message was deleted, create new one
                pass
        
        # Create new documentation message
        room_data = {
            "room_name": room_info['room_name'],
            "description": room_info['description'],
            "tags": room_info['tags'],
            "roomtype": room_info.get('roomtype', 'Unknown - Please update!'),
            "picture_urls": room_info['picture_urls'],
            "doc_by_user_id": room_info['doc_by_user_id'],
            "last_updated": room_info['last_updated'],
            "edited_by_user_id": room_info.get('edited_by_user_id')  # Include editor if available
        }
        
        # Send documentation message
        message_id = await embeds.send_room_documentation_embed(documented_channel, room_data)
        
        # Store message ID in server profile
        datamanager.server_db_handler.add_doc_id(server_id, room_name, message_id)
        
        print(f"[INFO] [{PRINT_PREFIX}] Documented '{room_name}' in server {guild.name} ({server_id})")
        return True
    
    except discord.NotFound:
        print(f"[WARNING] [{PRINT_PREFIX}] Channel not found when documenting '{room_name}' in server {guild.name} ({server_id})")
        print(f"[WARNING] [{PRINT_PREFIX}] Channel was deleted during sync. Clearing channel ID.")
        # Clear the channel reference but keep the profile
        datamanager.server_db_handler.update_server_profile(
            server_id=server_id,
            documented_channel_id=None,
            doc_msg_ids={}
        )
        return True  # Still mark as processed to avoid infinite retry
        
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error documenting '{room_name}' in server {server_id}: {e}")
        return True  # Still mark as processed to avoid infinite retry
