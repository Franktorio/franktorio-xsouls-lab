# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Command helper functions

PRINT_PREFIX = "UTILS"

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
        print(f"[DEBUG] [{PRINT_PREFIX}] Permission check for user {user.id}: Level 5 (Owner)")
        return 5

    # Get guild from cache only (no fetch)
    home_guild = shared.FRD_bot.get_guild(vars.HOME_GUILD_ID)
    if home_guild is None:
        print(f"[WARN] [{PRINT_PREFIX}] Permission check failed: Home guild not found in cache")
        return 0

    # Get member from cache only (no fetch)
    member = home_guild.get_member(user.id)
    if member is None:
        print(f"[DEBUG] [{PRINT_PREFIX}] Permission check for user {user.id}: Not a member of home guild")
        return 0

    # Use cached roles directly
    role_ids = {r.id for r in member.roles}

    # Check roles in priority order
    if vars.HEAD_RESEARCHER in role_ids:
        print(f"[DEBUG] [{PRINT_PREFIX}] Permission check for user {user.id}: Level 4 (Head Researcher)")
        return 4
    if vars.EXPERIENCED_RESEARCHER in role_ids:
        print(f"[DEBUG] [{PRINT_PREFIX}] Permission check for user {user.id}: Level 3 (Experienced Researcher)")
        return 3
    if vars.NOVICE_RESEARCHER in role_ids:
        print(f"[DEBUG] [{PRINT_PREFIX}] Permission check for user {user.id}: Level 2 (Novice Researcher)")
        return 2
    if vars.TRIAL_RESEARCHER in role_ids:
        print(f"[DEBUG] [{PRINT_PREFIX}] Permission check for user {user.id}: Level 1 (Trial Researcher)")
        return 1

    print(f"[DEBUG] [{PRINT_PREFIX}] Permission check for user {user.id}: Level 0 (No permission)")
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
        print(f"[DEBUG] [{PRINT_PREFIX}] User {user_id} has role: Head Researcher")
        return "Head Researcher"
    if vars.EXPERIENCED_RESEARCHER in role_ids:
        print(f"[DEBUG] [{PRINT_PREFIX}] User {user_id} has role: Experienced Researcher")
        return "Experienced Researcher"
    if vars.NOVICE_RESEARCHER in role_ids:
        print(f"[DEBUG] [{PRINT_PREFIX}] User {user_id} has role: Novice Researcher")
        return "Novice Researcher"
    if vars.TRIAL_RESEARCHER in role_ids:
        print(f"[DEBUG] [{PRINT_PREFIX}] User {user_id} has role: Trial Researcher")
        return "Trial Researcher"

    print(f"[DEBUG] [{PRINT_PREFIX}] User {user_id} has no research role")
    return "No Research Role"

async def global_reset(room_name: str):
    """
    Deletes the documentation message and its ID from all server profiles.
    Used when a room is modified in any way.
    """
    print(f"[INFO] [{PRINT_PREFIX}] Starting global reset for room '{room_name}'")
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
            print(f"[INFO] [{PRINT_PREFIX}] Deleted documentation message for room '{room_name}' in guild {guild.id}")
        except discord.NotFound:
            print(f"[DEBUG] [{PRINT_PREFIX}] Documentation message for room '{room_name}' in guild {guild.id} already deleted")
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

async def get_user_profile(user_id: int) -> dict:
    """Get the profile picture URL, username, and display name of a user from cache.
    Args:
        user_id: The Discord user ID.
    Returns:
        A dictionary containing profile_picture_url, username, and display_name.
    """
    async def _fetch_user_profile(user_id: int) -> dict:
        """Helper to fetch user profile in Discord's event loop."""
        user = await shared.FRD_bot.fetch_user(user_id)
        if user is None:
            return {
                "profile_picture_url": None,
                "username": "Unknown User",
                "display_name": "Unknown User"
            }
        
        profile_picture_url = str(user.display_avatar.url) if user.display_avatar else None
        return {
            "profile_picture_url": profile_picture_url,
            "username": str(user),
            "display_name": user.name
        }
    try:
        loop = asyncio.get_running_loop()
        # If we're in FastAPI's loop, schedule task in Discord's loop
        if loop != shared.FRD_bot.loop:
            future = asyncio.run_coroutine_threadsafe(
                _fetch_user_profile(user_id),
                shared.FRD_bot.loop
            )
            return future.result()
    except RuntimeError:
        pass  # No running loop

    # We're in Discord's loop, run normally
    return await _fetch_user_profile(user_id)

async def get_all_researchers() -> list[dict]:
    """Get a list of all researchers in the home guild.
    Returns:
        A list of dictionaries with user_id and research_level.
    """
    researchers = []

    async def _fetch_all_researchers() -> list[dict]:
        """Helper to fetch all researchers in Discord's event loop."""
        home_guild = await shared.FRD_bot.fetch_guild(vars.HOME_GUILD_ID)
        if home_guild is None:
            print(f"[WARN] [{PRINT_PREFIX}] Home guild not found in cache")
            return researchers

        for member in home_guild.members:
            role_ids = {r.id for r in member.roles}
            research_level = None
            if vars.HEAD_RESEARCHER in role_ids:
                research_level = "Head Researcher"
            elif vars.EXPERIENCED_RESEARCHER in role_ids:
                research_level = "Experienced Researcher"
            elif vars.NOVICE_RESEARCHER in role_ids:
                research_level = "Novice Researcher"
            elif vars.TRIAL_RESEARCHER in role_ids:
                research_level = "Trial Researcher"

            if research_level:
                researchers.append({
                    "user_id": member.id,
                    "username": str(member),
                    "profile_picture_url": str(member.display_avatar.url) if member.display_avatar else None,
                    "research_level": research_level
                })
        print(f"[DEBUG] [{PRINT_PREFIX}] Retrieved {len(researchers)} researchers from home guild")
        return researchers
    
    try:
        loop = asyncio.get_running_loop()
        # If we're in FastAPI's loop, schedule task in Discord's loop
        if loop != shared.FRD_bot.loop:
            future = asyncio.run_coroutine_threadsafe(
                _fetch_all_researchers(),
                shared.FRD_bot.loop
            )
            return future.result()
    except RuntimeError:
        pass  # No running loop

    # We're in Discord's loop, run normally
    return await _fetch_all_researchers()


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
        print(f"[DEBUG] [{PRINT_PREFIX}] No documented channel found for server {server_id}")
        return ""
    
    documented_channel = shared.FRD_bot.get_channel(profile['documented_channel_id'])
    if not documented_channel:
        print(f"[WARN] [{PRINT_PREFIX}] Documented channel {profile['documented_channel_id']} not found in cache for server {server_id}")
        return ""
    
    message_id = server_db_handler.get_doc_message_id(server_id, room_name)
    if not message_id:
        print(f"[DEBUG] [{PRINT_PREFIX}] No doc message ID found for room '{room_name}' in server {server_id}")
        return ""
    
    print(f"[DEBUG] [{PRINT_PREFIX}] Retrieved doc message link for room '{room_name}' in server {server_id}")
    return f"https://discord.com/channels/{server_id}/{documented_channel.id}/{message_id}"