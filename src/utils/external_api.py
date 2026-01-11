# Franktorio's Research Division
# Author: Franktorio
# November 16th, 2025
# External API Integration for Pressure Research Database

PRINT_PREFIX = "EXTERNAL API"

# Standard library imports
import asyncio
from typing import Optional, Dict, Any

# Third-party imports
import aiohttp

# Local imports
from config.vars import API_BASE_URL, API_KEY, EXTERNAL_DATA_SOURCE

async def export_room_to_api(
    room_name: str,
    roomtype: str,
    picture_urls: list[str],
    description: str,
    doc_by_user_id: int,
    tags: list[str] = None,
    last_edited_by: Optional[int] = None,
    timestamp: Optional[float] = None
) -> Dict[str, Any]:
    """
    Export room data to external Pressure API.
    Returns response dict with success status.
    """
    print(f"[INFO] [{PRINT_PREFIX}] Exporting room to external API: {room_name}")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled", "skipped": True}
    
    if not API_KEY or not API_BASE_URL:
        print(f"[WARNING] [{PRINT_PREFIX}] API not configured for room export: {room_name}")
        return {"success": False, "error": "API not configured"}
    
    print(f"[DEBUG] [{PRINT_PREFIX}] Validating image count for room: {room_name}")
    # Validate image count (external API requires 4-10 images)
    image_count = len(picture_urls)
    if image_count < 4:
        print(f"[WARNING] [{PRINT_PREFIX}] Insufficient images for room {room_name}: {image_count} (minimum 4 required)")
        return {
            "success": False,
            "error": f"External API requires minimum 4 images (room has {image_count})",
            "skipped": True  # Flag to indicate this is expected, not a critical error
        }
    
    print(f"[DEBUG] [{PRINT_PREFIX}] Preparing API request for room: {room_name}")
    url = f"{API_BASE_URL}/upload-room"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    print(f"[DEBUG] [{PRINT_PREFIX}] Building payload for room: {room_name} with {len(picture_urls[:10])} images")
    payload = {
        "room_name": room_name,
        "description": description,
        "images": picture_urls[:10],  # Max 10 images
        "documented_by": doc_by_user_id,
        "tags": tags or [],
        "roomtype": roomtype
    }
    
    if last_edited_by:
        payload["last_edited_by"] = last_edited_by
    
    if timestamp is not None:
        payload["last_edited"] = timestamp
    
    try:
        print(f"[INFO] [{PRINT_PREFIX}] Sending POST request to external API for room: {room_name}")
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully exported room: {room_name}")
                    return data
                else:
                    try:
                        error_data = await resp.json()
                        error_text = str(error_data)
                    except:
                        error_text = await resp.text()
                    
                    # Log detailed error for server issues
                    if resp.status >= 500:
                        print(f"[ERROR] [{PRINT_PREFIX}] External API server error (room: {room_name}): {resp.status}")
                        print(f"[ERROR] [{PRINT_PREFIX}] Response: {error_text[:500]}")  # Truncate long responses
                    
                    return {
                        "success": False,
                        "error": f"API returned {resp.status}: {error_text[:200]}"  # Truncate for return
                    }
    except asyncio.TimeoutError:
        print(f"[ERROR] [{PRINT_PREFIX}] API request timed out for room: {room_name}")
        return {"success": False, "error": "API request timed out"}
    except aiohttp.ClientError as e:
        return {"success": False, "error": f"API request failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


async def update_room_description_api(
    room_name: str,
    description: str,
    edited_by: int
) -> Dict[str, Any]:
    """Update room description on external API."""
    print(f"[INFO] [{PRINT_PREFIX}] Updating room description: {room_name}")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled", "skipped": True}
    
    if not API_KEY or not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/room/{room_name}/description"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "description": description,
        "edited_by": edited_by
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.patch(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully updated description: {room_name}")
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_room_tags_api(
    room_name: str,
    tags: list[str],
    edited_by: int
) -> Dict[str, Any]:
    """Update room tags on external API."""
    print(f"[INFO] [{PRINT_PREFIX}] Updating room tags: {room_name}")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled", "skipped": True}
    
    if not API_KEY or not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/room/{room_name}/tags"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "tags": tags,
        "edited_by": edited_by
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.patch(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully updated tags: {room_name}")
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to update tags for {room_name}: {resp.status}")
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error updating tags for {room_name}: {str(e)}")
        return {"success": False, "error": str(e)}


async def update_room_roomtype_api(
    room_name: str,
    roomtype: str,
    edited_by: int
) -> Dict[str, Any]:
    """Update room type on external API."""
    print(f"[INFO] [{PRINT_PREFIX}] Updating room type: {room_name} -> {roomtype}")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled", "skipped": True}
    
    if not API_KEY or not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/room/{room_name}/roomtype"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "roomtype": roomtype,
        "edited_by": edited_by
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.patch(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully updated room type: {room_name}")
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to update roomtype for {room_name}: {resp.status}")
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error updating roomtype for {room_name}: {str(e)}")
        return {"success": False, "error": str(e)}


async def delete_room_api(room_name: str) -> Dict[str, Any]:
    """Delete room from external API."""
    print(f"[INFO] [{PRINT_PREFIX}] Deleting room from external API: {room_name}")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled", "skipped": True}
    
    if not API_KEY or not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/room/{room_name}/delete"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.delete(url, headers=headers) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully deleted room: {room_name}")
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to delete room {room_name}: {resp.status}")
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error deleting room {room_name}: {str(e)}")
        return {"success": False, "error": str(e)}


async def rename_room_api(
    old_name: str,
    new_name: str,
    edited_by: int
) -> Dict[str, Any]:
    """Rename a room on external API."""
    print(f"[INFO] [{PRINT_PREFIX}] Renaming room: {old_name} -> {new_name}")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled", "skipped": True}
    
    if not API_KEY or not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/room/{old_name}/rename"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "new_name": new_name,
        "edited_by": edited_by
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully renamed room: {old_name} -> {new_name}")
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to rename room {old_name}: {resp.status}")
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error renaming room {old_name}: {str(e)}")
        return {"success": False, "error": str(e)}


async def get_room_info_api(room_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific room (public endpoint)."""
    print(f"[INFO] [{PRINT_PREFIX}] Fetching room info from external API: {room_name}")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled"}
    
    if not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/room/{room_name}"
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully fetched room info: {room_name}")
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to fetch room info for {room_name}: {resp.status}")
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error fetching room info for {room_name}: {str(e)}")
        return {"success": False, "error": str(e)}


async def get_all_rooms_api(
    page: int = 1,
    per_page: int = 20,
    tag: Optional[str] = None
) -> Dict[str, Any]:
    """Get paginated list of all rooms (public endpoint)."""
    print(f"[INFO] [{PRINT_PREFIX}] Fetching all rooms from external API (page {page})")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled"}
    
    if not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/rooms"
    params = {
        "page": page,
        "per_page": per_page
    }
    if tag:
        params["tag"] = tag
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully fetched rooms list (page {page})")
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to fetch rooms list (page {page}): {resp.status}")
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error fetching rooms list (page {page}): {str(e)}")
        return {"success": False, "error": str(e)}


async def search_rooms_api(
    query: Optional[str] = None,
    tags: Optional[list[str]] = None,
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """Search rooms by text query and/or tags (public endpoint)."""
    print(f"[INFO] [{PRINT_PREFIX}] Searching rooms on external API (query: {query}, tags: {tags})")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled"}
    
    if not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/search"
    params = {
        "page": page,
        "per_page": per_page
    }
    if query:
        params["q"] = query
    if tags:
        params["tags"] = tags
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully completed room search")
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to search rooms: {resp.status}")
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error searching rooms: {str(e)}")
        return {"success": False, "error": str(e)}


async def get_stats_api() -> Dict[str, Any]:
    """Get database statistics and top contributors (public endpoint)."""
    print(f"[INFO] [{PRINT_PREFIX}] Fetching stats from external API")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled"}
    
    if not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/stats"
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully fetched stats")
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to fetch stats: {resp.status}")
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error fetching stats: {str(e)}")
        return {"success": False, "error": str(e)}


async def get_user_rooms_api(user_id: int) -> Dict[str, Any]:
    """Get all rooms documented by a specific user (public endpoint)."""
    print(f"[INFO] [{PRINT_PREFIX}] Fetching rooms for user {user_id} from external API")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled"}
    
    if not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/users/{user_id}/rooms"
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully fetched user rooms for {user_id}")
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to fetch user rooms for {user_id}: {resp.status}")
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error fetching user rooms for {user_id}: {str(e)}")
        return {"success": False, "error": str(e)}


async def export_database_api() -> Dict[str, Any]:
    """Export the complete database (requires auth)."""
    print(f"[INFO] [{PRINT_PREFIX}] Exporting complete database from external API")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled"}
    
    if not API_KEY or not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/database/export"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=60)  # Longer timeout for large export
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully exported complete database")
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to export database: {resp.status}")
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error exporting database: {str(e)}")
        return {"success": False, "error": str(e)}


async def get_bot_roles_api() -> Dict[str, Any]:
    """Get all available roles from external API (BOT endpoint)."""
    print(f"[INFO] [{PRINT_PREFIX}] Fetching bot roles from external API")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled"}
    
    if not API_KEY or not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/bot/roles"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully fetched bot roles")
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to fetch bot roles: {resp.status}")
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error fetching bot roles: {str(e)}")
        return {"success": False, "error": str(e)}


async def set_user_role_api(user_id: int, role_name: str) -> Dict[str, Any]:
    """
    Set a user's role on the external API (BOT endpoint).
    
    Args:
        user_id: Discord user ID
        role_name: Role name - "Viewer", "Trial Researcher", "Novice Researcher", 
                   "Experienced Researcher", "Head Researcher"
    
    Returns:
        Dict with success status and message or error
    
    Note:
        Cannot assign "Superadmin" role via API
        Cannot modify hardcoded superadmin users
    """
    print(f"[INFO] [{PRINT_PREFIX}] Setting user role: {user_id} -> {role_name}")
    if not EXTERNAL_DATA_SOURCE:
        return {"success": False, "error": "External data source is disabled"}
    
    if not API_KEY or not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/bot/users/{user_id}/role"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "role_name": role_name
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.put(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    print(f"[INFO] [{PRINT_PREFIX}] Successfully set user role: {user_id} -> {role_name}")
                    return await resp.json()
                else:
                    try:
                        error_data = await resp.json()
                        error_text = str(error_data)
                    except:
                        error_text = await resp.text()
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to set user role for {user_id}: {resp.status}")
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error setting user role for {user_id}: {str(e)}")
        return {"success": False, "error": str(e)}

