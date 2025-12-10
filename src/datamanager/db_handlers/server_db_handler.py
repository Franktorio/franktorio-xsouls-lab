# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Server Profile Manager - stores per-server configuration

PRINT_PREFIX = "SERVER DB"

# Standard library imports
import re
import sqlite3
import json
from typing import Optional, Dict, Any

# Local imports
from ..database_manager import connect_db

DB_FILE_NAME = "frd_bot.db"

SCHEMA = {
    "server_profiles": """
        CREATE TABLE IF NOT EXISTS server_profiles (
            server_id INTEGER PRIMARY KEY,
            leaderboard_channel_id INTEGER,
            documented_channel_id INTEGER,
            doc_msg_ids TEXT
        );
    """
}

def _connect_db() -> sqlite3.Connection:
    """Connect to the database and return the connection."""
    return connect_db(DB_FILE_NAME)


def get_server_profile(server_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a server profile by server_id.
    
    Args:
        server_id: The Discord server (guild) ID
        
    Returns:
        Dictionary with server profile data or None if not found
        {
            'server_id': int,
            'leaderboard_channel_id': int,
            'documented_channel_id': int,
            'doc_msg_ids': {"Roomname": message_id, ...}
        }
    """
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT server_id, leaderboard_channel_id, documented_channel_id, doc_msg_ids
        FROM server_profiles
        WHERE server_id = ?
    """, (server_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'server_id': row[0],
            'leaderboard_channel_id': row[1],
            'documented_channel_id': None if row[2] == 0 else row[2],
            'doc_msg_ids': json.loads(row[3]) if row[3] else {}
        }
    return None


def create_server_profile(server_id: int, leaderboard_channel_id: int = None, 
                         documented_channel_id: int = None, doc_msg_ids: Dict[str, int] = None) -> bool:
    """
    Create a new server profile.
    
    Args:
        server_id: The Discord server (guild) ID
        leaderboard_channel_id: Channel ID for leaderboard
        documented_channel_id: Channel ID for documentation
        doc_msg_ids: Dictionary mapping room names to message IDs
        
    Returns:
        True if created successfully, False otherwise
    """
    if doc_msg_ids is None:
        doc_msg_ids = {}
    
    conn = _connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO server_profiles (server_id, leaderboard_channel_id, documented_channel_id, doc_msg_ids)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(server_id) DO UPDATE SET
                leaderboard_channel_id = excluded.leaderboard_channel_id,
                documented_channel_id = excluded.documented_channel_id,
                doc_msg_ids = excluded.doc_msg_ids
        """, (server_id, leaderboard_channel_id, documented_channel_id, json.dumps(doc_msg_ids)))

        conn.commit()
        conn.close()
        print(f"[{PRINT_PREFIX}] Created/updated server profile for guild {server_id}")
    except Exception as e:
        print(f"[{PRINT_PREFIX}] Error creating server profile for guild {server_id}: {e}")
        raise
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def update_server_profile(server_id: int, leaderboard_channel_id: int = None,
                         documented_channel_id: int = None, doc_msg_ids: Dict[str, int] = None) -> bool:
    """
    Update an existing server profile. Only updates provided fields.
    
    Args:
        server_id: The Discord server (guild) ID
        leaderboard_channel_id: Channel ID for leaderboard (optional)
        documented_channel_id: Channel ID for documentation (optional)
        doc_msg_ids: Dictionary mapping room names to message IDs (optional)
        
    Returns:
        True if updated successfully, False otherwise
    """
    conn = _connect_db()
    cursor = conn.cursor()
    
    # Build dynamic update query based on provided fields
    updates = []
    params = []
    
    if leaderboard_channel_id is not None:
        updates.append("leaderboard_channel_id = ?")
        params.append(leaderboard_channel_id)
    
    if documented_channel_id is not None:
        updates.append("documented_channel_id = ?")
        params.append(documented_channel_id)
    
    if doc_msg_ids is not None:
        updates.append("doc_msg_ids = ?")
        params.append(json.dumps(doc_msg_ids))
    
    if not updates:
        conn.close()
        return False
    
    params.append(server_id)
    query = f"UPDATE server_profiles SET {', '.join(updates)} WHERE server_id = ?"
    
    cursor.execute(query, params)
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def set_leaderboard_channel(server_id: int, channel_id: int) -> bool:
    """Set the leaderboard channel for a server."""
    profile = get_server_profile(server_id)
    if profile:
        return update_server_profile(server_id, leaderboard_channel_id=channel_id)
    else:
        return False


def set_documented_channel(server_id: int, channel_id: int) -> bool:
    """Set the documented channel for a server."""
    profile = get_server_profile(server_id)
    if profile:
        return update_server_profile(server_id, documented_channel_id=channel_id)
    else:
        return False


def add_doc_id(server_id: int, room_name: str, message_id: int) -> bool:
    """
    Add or update a documentation message ID for a specific room.
    
    Args:
        server_id: The Discord server (guild) ID
        room_name: Name of the room/category
        message_id: Discord message ID to store
        
    Returns:
        True if successful, False otherwise
    """
    profile = get_server_profile(server_id)
    if profile:
        doc_msg_ids = profile['doc_msg_ids'].copy()
        doc_msg_ids[room_name] = message_id
        return update_server_profile(server_id, doc_msg_ids=doc_msg_ids)
    else:
        return False


def remove_doc_id(server_id: int, room_name: str) -> bool:
    """
    Remove a documentation message ID for a specific room.
    
    Args:
        server_id: The Discord server (guild) ID
        room_name: Name of the room/category to remove
        
    Returns:
        True if successful, False otherwise
    """
    profile = get_server_profile(server_id)
    if profile and room_name in profile['doc_msg_ids']:
        doc_msg_ids = profile['doc_msg_ids'].copy()
        del doc_msg_ids[room_name]
        return update_server_profile(server_id, doc_msg_ids=doc_msg_ids)
    return False

def clear_doc_ids(server_id: int) -> bool:
    """
    Clears the documented message IDs for all rooms in a server profile.
    """
    profile = get_server_profile(server_id)
    if profile:
        return update_server_profile(server_id, doc_msg_ids={})
    return False

def get_doc_message_id(server_id: int, room_name: str) -> Optional[int]:
    """
    Get a specific documentation message ID for a room.
    
    Args:
        server_id: The Discord server (guild) ID
        room_name: Name of the room/category
        
    Returns:
        Message ID if found, None otherwise
    """
    profile = get_server_profile(server_id)
    if profile:
        return profile['doc_msg_ids'].get(room_name)
    return None


def delete_server_profile(server_id: int) -> bool:
    """
    Delete a server profile completely.
    
    Args:
        server_id: The Discord server (guild) ID
        
    Returns:
        True if deleted successfully, False otherwise
    """
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM server_profiles WHERE server_id = ?", (server_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def clear_server_profiles():
    """Delete all server profiles from the database."""
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM server_profiles")
    conn.commit()
    conn.close()

def get_all_server_profiles() -> list:
    """
    Retrieve all server profiles.
    
    Returns:
        List of dictionaries with server profile data
    """
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT server_id, leaderboard_channel_id, documented_channel_id, doc_msg_ids FROM server_profiles")
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        'server_id': row[0],
        'leaderboard_channel_id': row[1],
        'documented_channel_id': row[2],
        'doc_msg_ids': json.loads(row[3]) if row[3] else {}
    } for row in rows]