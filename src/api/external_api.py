# Franktorio's Research Division
# Author: Franktorio
# November 16th, 2025
# External API Integration for Pressure Research Database

import aiohttp
import asyncio
from typing import Optional, Dict, Any
from config.vars import API_BASE_URL, API_KEY

async def export_room_to_api(
    room_name: str,
    roomtype: str,
    picture_urls: list[str],
    description: str,
    doc_by_user_id: int,
    tags: list[str] = None,
    last_edited_by: Optional[int] = None
) -> Dict[str, Any]:
    """
    Export room data to external Pressure API.
    Returns response dict with success status.
    """
    if not API_KEY or not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    # Validate image count (external API requires 4-10 images)
    image_count = len(picture_urls)
    if image_count < 4:
        return {
            "success": False,
            "error": f"External API requires minimum 4 images (room has {image_count})",
            "skipped": True  # Flag to indicate this is expected, not a critical error
        }
    
    url = f"{API_BASE_URL}/upload-room"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
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
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    return data
                else:
                    try:
                        error_data = await resp.json()
                        error_text = str(error_data)
                    except:
                        error_text = await resp.text()
                    
                    # Log detailed error for server issues
                    if resp.status >= 500:
                        print(f"❌ External API server error (room: {room_name}): {resp.status}")
                        print(f"   Response: {error_text[:500]}")  # Truncate long responses
                    
                    return {
                        "success": False,
                        "error": f"API returned {resp.status}: {error_text[:200]}"  # Truncate for return
                    }
    except asyncio.TimeoutError:
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
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_room_roomtype_api(
    room_name: str,
    roomtype: str,
    edited_by: int
) -> Dict[str, Any]:
    """Update room type on external API."""
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
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def delete_room_api(room_name: str) -> Dict[str, Any]:
    """Delete room from external API."""
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
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def rename_room_api(
    old_name: str,
    new_name: str,
    edited_by: int
) -> Dict[str, Any]:
    """Rename a room on external API."""
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
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_room_info_api(room_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific room (public endpoint)."""
    if not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/room/{room_name}"
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_all_rooms_api(
    page: int = 1,
    per_page: int = 20,
    tag: Optional[str] = None
) -> Dict[str, Any]:
    """Get paginated list of all rooms (public endpoint)."""
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
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def search_rooms_api(
    query: Optional[str] = None,
    tags: Optional[list[str]] = None,
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """Search rooms by text query and/or tags (public endpoint)."""
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
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_stats_api() -> Dict[str, Any]:
    """Get database statistics and top contributors (public endpoint)."""
    if not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/stats"
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_user_rooms_api(user_id: int) -> Dict[str, Any]:
    """Get all rooms documented by a specific user (public endpoint)."""
    if not API_BASE_URL:
        return {"success": False, "error": "API not configured"}
    
    url = f"{API_BASE_URL}/users/{user_id}/rooms"
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def export_database_api() -> Dict[str, Any]:
    """Export the complete database (requires auth)."""
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
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_bot_roles_api() -> Dict[str, Any]:
    """Get all available roles from external API (BOT endpoint)."""
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
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
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
                    return await resp.json()
                else:
                    try:
                        error_data = await resp.json()
                        error_text = str(error_data)
                    except:
                        error_text = await resp.text()
                    return {"success": False, "error": f"API returned {resp.status}: {error_text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

