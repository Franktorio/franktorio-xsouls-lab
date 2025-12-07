# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Command helper functions

# Standard library imports
import asyncio

# Third-party imports
import discord

# Local imports
from config import vars
from src import shared
from src.datamanager.db_handlers import server_db_handler

async def permission_check(user: discord.User) -> int:
    """Check if a user has permission to use research commands.
    Args:
        user: The Discord user to check permissions for.
    Returns:
        5-1 if they have permission, 0 if not.
    """
    # Owner always has permission
    if user.id == vars.OWNER_ID:
        return 5

    # Get guild from cache only (no fetch)
    home_guild = shared.FRD_bot.get_guild(vars.HOME_GUILD_ID)
    if home_guild is None:
        return 0

    # Get member from cache only (no fetch)
    member = home_guild.get_member(user.id)
    if member is None:
        return 0

    # Use cached roles directly
    role_ids = {r.id for r in member.roles}

    # Check roles in priority order
    if vars.HEAD_RESEARCHER in role_ids:
        return 4
    if vars.EXPERIENCED_RESEARCHER in role_ids:
        return 3
    if vars.NOVICE_RESEARCHER in role_ids:
        return 2
    if vars.TRIAL_RESEARCHER in role_ids:
        return 1

    return 0

async def get_researcher_role(user_id: int) -> str:
    """Get the research level of a user.
    Args:
        user_id: The Discord user ID to check.
    Returns:
        A string representing the research level.
    """
    
    # Get guild from cache only (no fetch)
    home_guild = shared.FRD_bot.get_guild(vars.HOME_GUILD_ID)
    if home_guild is None:
        return "Home-guild Not Found"

    # Get member from cache only (no fetch)
    member = home_guild.get_member(user_id)
    if member is None:
        return "No Research Role"

    # Use cached roles directly
    role_ids = {r.id for r in member.roles}

    # Check roles in priority order
    if vars.HEAD_RESEARCHER in role_ids:
        return "Head Researcher"
    if vars.EXPERIENCED_RESEARCHER in role_ids:
        return "Experienced Researcher"
    if vars.NOVICE_RESEARCHER in role_ids:
        return "Novice Researcher"
    if vars.TRIAL_RESEARCHER in role_ids:
        return "Trial Researcher"

    return "No Research Role"

async def global_reset(room_name: str):
    """
    Deletes the documentation message and its ID from all server profiles.
    Used when a room is modified in any way.
    """
    async def _delete_message(guild, message_id, room_name):
        """Helper to delete a single message."""
        profile = server_db_handler.get_server_profile(guild.id)
        if not profile or not profile.get('documented_channel_id'):
            return
        
        documented_channel = guild.get_channel(profile['documented_channel_id'])
        if not documented_channel:
            return
        
        try:
            message = await documented_channel.fetch_message(message_id)
            await message.delete()
        except discord.NotFound:
            pass  # Message already deleted
        
        # Remove message ID from profile
        server_db_handler.remove_doc_id(guild.id, room_name)
    
    # Check if we're running in Discord's event loop or FastAPI's
    try:
        loop = asyncio.get_running_loop()
        # If we're in FastAPI's loop, schedule tasks in Discord's loop
        if loop != shared.FRD_bot.loop:
            for guild in shared.FRD_bot.guilds:
                message_id = server_db_handler.get_doc_message_id(guild.id, room_name)
                if message_id:
                    asyncio.run_coroutine_threadsafe(
                        _delete_message(guild, message_id, room_name),
                        shared.FRD_bot.loop
                    )
            return
    except RuntimeError:
        pass  # No running loop
    
    # We're in Discord's loop, run normally
    for guild in shared.FRD_bot.guilds:
        message_id = server_db_handler.get_doc_message_id(guild.id, room_name)
        if message_id:
            await _delete_message(guild, message_id, room_name)

def get_user_profile(user_id: int) -> dict:
    """Get the profile picture URL, username, and display name of a user from cache.
    Args:
        user_id: The Discord user ID.
    Returns:
        A dictionary containing profile_picture_url, username, and display_name.
    Note:
        This only checks the bot's user cache. Users not in cache will return empty strings.
        This is intentional to avoid event loop conflicts between FastAPI and Discord.py.
    """
    user = shared.FRD_bot.get_user(user_id)
    if user is None:
        # Return empty data if user is not in cache
        # We can't use fetch_user from FastAPI context due to event loop conflicts
        return {
            "profile_picture_url": "",
            "username": "",
            "display_name": ""
        }
    
    return {
        "profile_picture_url": str(user.display_avatar.url),
        "username": str(user.name),
        "display_name": str(user.display_name)
    }

def get_doc_message_link(server_id: int, room_name: str) -> str:
    """Get the link to the documented message for a room in a server.
    Args:
        server_id: The Discord server ID.
        room_name: The name of the room.
    Returns:
        A string URL to the documented message, or an empty string if not found.
    """
    profile = server_db_handler.get_server_profile(server_id)
    if not profile or not profile.get('documented_channel_id'):
        return ""
    
    documented_channel = shared.FRD_bot.get_channel(profile['documented_channel_id'])
    if not documented_channel:
        return ""
    
    message_id = server_db_handler.get_doc_message_id(server_id, room_name)
    if not message_id:
        return ""
    
    return f"https://discord.com/channels/{server_id}/{documented_channel.id}/{message_id}"