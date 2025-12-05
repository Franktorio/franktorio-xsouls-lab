# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Room documentation database handler

# Standard library imports
import re
import sqlite3
import datetime
import json
import os
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), "databases", "frd_room.db")

def _connect_db():
    """Connect to the database and return the connection."""
    return sqlite3.connect(DB_PATH)


def init_room_db_table():
    """Initialize the room_db table if it doesn't exist."""
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS room_db (
            room_name TEXT PRIMARY KEY,
            picture_urls TEXT NOT NULL DEFAULT '[]',
            description TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '[]',
            roomtype TEXT NOT NULL DEFAULT '',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            doc_by_user_id INTEGER NOT NULL,
            edited_by_user_id INTEGER,
            edits TEXT NOT NULL DEFAULT '[]'
        )
    """)
    
    conn.commit()
    conn.close()

def document_room(room_name: str, picture_urls: list, description: str, doc_by_user_id: int, tags: list, roomtype: str, timestamp: float, edited_by_user_id: int = None) -> bool:
    """
    Document or update a room's information in the database.
    
    Args:
        room_name: The name of the room
        picture_urls: List of picture URLs documenting the room
        description: Textual description of the room
        doc_by_user_id: Discord user ID of the documenting user
        
    Returns:
        True if successful, False otherwise
    """
    conn = _connect_db()
    cursor = conn.cursor()
    
    # Check if room already exists
    cursor.execute("SELECT room_name, picture_urls, description, edits, tags, roomtype, doc_by_user_id FROM room_db WHERE room_name = ?", (room_name,))
    row = cursor.fetchone()
    
    edits = []
    if row:
        # Room exists, prepare edit history
        existing_picture_urls = json.loads(row[1])
        existing_description = row[2]
        edits = json.loads(row[3])
        existing_doc_by = row[6]  # Get existing documenter
        
        edit_entry = {
            "timestamp": datetime.datetime.now().timestamp(),
            "previous_room_name": room_name,
            "previous_picture_urls": existing_picture_urls,
            "previous_tags": json.loads(row[4]),
            "previous_description": existing_description,
            "previous_roomtype": row[5],
            "previous_doc_by_user_id": existing_doc_by,
            "edited_by_user_id": edited_by_user_id if edited_by_user_id else doc_by_user_id
        }
        edits.append(edit_entry)
        
        # Update existing record - use Unix timestamp instead of CURRENT_TIMESTAMP
        cursor.execute("""
            UPDATE room_db
            SET picture_urls = ?, description = ?, last_updated = ?, edits = ?, tags = ?, roomtype = ?, edited_by_user_id = ?
            WHERE room_name = ?
        """, (json.dumps(picture_urls), description, datetime.datetime.now().timestamp(), json.dumps(edits), json.dumps(tags), roomtype, edited_by_user_id if edited_by_user_id else doc_by_user_id, room_name))
    else:
        # Insert new record
        cursor.execute("""
            INSERT INTO room_db (room_name, picture_urls, description, doc_by_user_id, edits, tags, roomtype, last_updated, edited_by_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (room_name, json.dumps(picture_urls), description, doc_by_user_id, json.dumps(edits), json.dumps(tags), roomtype, timestamp, None))

    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def replace_doc(room_name: str, picture_urls: list, description: str, doc_by_user_id: int, tags: list, roomtype: str, timestamp: float, edited_by_user_id: int = None, edits: list = None) -> bool:
    """
    Replace a room's documentation completely with provided data.
    Used for importing data from external sources where we want to preserve the original data including edit history.
    
    Args:
        room_name: The name of the room
        picture_urls: List of picture URLs documenting the room
        description: Textual description of the room
        doc_by_user_id: Discord user ID of the original documenting user
        tags: List of tags for the room
        roomtype: Type of the room
        timestamp: Original timestamp
        edited_by_user_id: User who performed the import/replace (optional)
        edits: Edit history to preserve (optional, defaults to empty)
        
    Returns:
        True if successful, False otherwise
    """
    conn = _connect_db()
    cursor = conn.cursor()
    
    # Check if room exists and get existing edit history
    cursor.execute("SELECT edits FROM room_db WHERE room_name = ?", (room_name,))
    result = cursor.fetchone()
    exists = result is not None
    
    # If edits not provided and room exists, preserve existing edit history
    if edits is None and exists:
        existing_edits = json.loads(result[0])
        edits = existing_edits
    elif edits is None:
        edits = []
    
    if exists:
        # Replace existing record but keep edit history
        cursor.execute("""
            UPDATE room_db
            SET picture_urls = ?, description = ?, last_updated = ?, doc_by_user_id = ?, edits = ?, tags = ?, roomtype = ?, edited_by_user_id = ?
            WHERE room_name = ?
        """, (json.dumps(picture_urls), description, timestamp, doc_by_user_id, json.dumps(edits), json.dumps(tags), roomtype, edited_by_user_id, room_name))
    else:
        # Insert new record
        cursor.execute("""
            INSERT INTO room_db (room_name, picture_urls, description, doc_by_user_id, edits, tags, roomtype, last_updated, edited_by_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (room_name, json.dumps(picture_urls), description, doc_by_user_id, json.dumps(edits), json.dumps(tags), roomtype, timestamp, edited_by_user_id))

    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def replace_imgs(room_name: str, picture_urls: list) -> bool:
    """
    Replace only the picture URLs for a specific room.
    
    Args:
        room_name: The name of the room
        picture_urls: List of new picture URLs to set for the room
    """

    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE room_db
        SET picture_urls = ?
        WHERE room_name = ?
    """, (json.dumps(picture_urls), room_name))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def rename_room(old_name: str, new_name: str, edited_by_user_id: int) -> bool:
    """
    Rename a room in the database and record edit history.
    
    Args:
        old_name: The current name of the room
        new_name: The new name to set for the room
        edited_by_user_id: User ID who is renaming the room
    """
    conn = _connect_db()
    cursor = conn.cursor()
    
    # Get existing room data
    cursor.execute("""
        SELECT picture_urls, description, edits, tags, roomtype, doc_by_user_id
        FROM room_db
        WHERE room_name = ?
    """, (old_name,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return False
    
    # Parse existing data
    picture_urls = json.loads(row[0])
    description = row[1]
    edits = json.loads(row[2])
    tags = json.loads(row[3])
    roomtype = row[4]
    doc_by_user_id = row[5]
    
    # Create edit history entry for rename
    edit_entry = {
        "timestamp": datetime.datetime.now().timestamp(),
        "previous_room_name": old_name,
        "previous_picture_urls": picture_urls,
        "previous_tags": tags,
        "previous_description": description,
        "previous_roomtype": roomtype,
        "previous_doc_by_user_id": doc_by_user_id,
        "edited_by_user_id": edited_by_user_id,
        "action": "rename"
    }
    edits.append(edit_entry)
    
    # Rename the room and update edit history
    cursor.execute("""
        UPDATE room_db
        SET room_name = ?, edits = ?, last_updated = ?, edited_by_user_id = ?
        WHERE room_name = ?
    """, (new_name, json.dumps(edits), datetime.datetime.now().timestamp(), edited_by_user_id, old_name))
    
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def set_roomtype(room_name: str, roomtype: str, edited_by_user_id: int) -> bool:
    """
    Set the room type for a specific room.
    
    Args:
        room_name: The name of the room
        roomtype: The type to set for the room
    """

    room_data = get_roominfo(room_name)
    if not room_data:
        return False
    
    document_room(room_name=room_name,
                  picture_urls=room_data['picture_urls'],
                  description=room_data['description'],
                  doc_by_user_id=room_data['doc_by_user_id'],
                  tags=room_data['tags'],
                  roomtype=roomtype,
                  timestamp=datetime.datetime.now().timestamp(),
                  edited_by_user_id=edited_by_user_id)
    return True

def set_roomtags(room_name: str, tags: list, edited_by_user_id: int) -> bool:
    """
    Set the tags for a specific room.
    
    Args:
        room_name: The name of the room
        tags: List of tags to set for the room
        doc_by_user_id: Discord user ID of the documenting user
    """

    room_data = get_roominfo(room_name)
    if not room_data:
        return False
    
    document_room(room_name=room_name,
                  picture_urls=room_data['picture_urls'],
                  description=room_data['description'],
                  doc_by_user_id=room_data['doc_by_user_id'],
                  tags=tags,
                  roomtype=room_data['roomtype'],
                  timestamp=datetime.datetime.now().timestamp(),
                  edited_by_user_id=edited_by_user_id)
    return True

def set_roomdescription(room_name: str, description: str, edited_by_user_id: int) -> bool:
    """
    Set the description for a specific room.
    
    Args:
        room_name: The name of the room
        description: The new description for the room
    """

    room_data = get_roominfo(room_name)
    if not room_data:
        return False
    
    document_room(room_name=room_name,
                  picture_urls=room_data['picture_urls'],
                  description=description,
                  doc_by_user_id=room_data['doc_by_user_id'],
                  tags=room_data['tags'],
                  roomtype=room_data['roomtype'],
                  timestamp=datetime.datetime.now().timestamp(),
                  edited_by_user_id=edited_by_user_id)
    return True

def get_roominfo(room_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve room information from the database.
    Case-insensitive search for room names.
    
    Args:
        room_name: The name of the room to retrieve (case-insensitive)

    Returns:
        A dictionary containing the room information, or None if not found.
    """
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT room_name, picture_urls, description, last_updated, doc_by_user_id, edits, tags, roomtype, edited_by_user_id
        FROM room_db
        WHERE LOWER(room_name) = LOWER(?)
    """, (room_name,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'room_name': row[0],
            'picture_urls': json.loads(row[1]),
            'description': row[2],
            'last_updated': row[3],
            'doc_by_user_id': row[4],
            'edits': json.loads(row[5]),
            'tags': json.loads(row[6]),
            'roomtype': row[7],
            'edited_by_user_id': row[8]
        }
    return None

def delete_room(room_name: str) -> bool:
    """
    Delete a room's documentation from the database.
    
    Args:
        room_name: The name of the room to delete
    """
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM room_db WHERE room_name = ?", (room_name,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def search_rooms_by_tag(tag: str) -> list:
    """
    Search for rooms that have a specific tag.
    
    Args:
        tag: The tag to search for
    """
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT room_name, picture_urls, description, last_updated, doc_by_user_id, edits, tags, roomtype, edited_by_user_id
        FROM room_db
        WHERE ? IN (SELECT value FROM json_each(tags))
    """, (tag,))
    rows = cursor.fetchall()
    conn.close()

    return [{
        'room_name': row[0],
        'picture_urls': json.loads(row[1]),
        'description': row[2],
        'last_updated': row[3],
        'doc_by_user_id': row[4],
        'edits': json.loads(row[5]),
        'tags': json.loads(row[6]),
        'roomtype': row[7],
        'edited_by_user_id': row[8]
    } for row in rows]

def search_rooms_by_name(search_term: str) -> list:
    """
    Search for rooms that match a specific name or partial name.
    
    Args:
        search_term: The name or partial name to search for
    """
    search_term = search_term.lower()

    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT room_name, picture_urls, description, last_updated, doc_by_user_id, edits, tags, roomtype, edited_by_user_id
        FROM room_db
        WHERE LOWER(room_name) LIKE ?
    """, (f"%{search_term.lower()}%",))
    rows = cursor.fetchall()
    conn.close()

    return [{
        'room_name': row[0],
        'picture_urls': json.loads(row[1]),
        'description': row[2],
        'last_updated': row[3],
        'doc_by_user_id': row[4],
        'edits': json.loads(row[5]),
        'tags': json.loads(row[6]),
        'roomtype': row[7],
        'edited_by_user_id': row[8]
    } for row in rows]

def search_rooms_by_description(search_term: str) -> list:
    """
    Search for rooms that match a specific term in their description.
    
    Args:
        search_term: The term to search for in descriptions
    """
    search_term = search_term.lower()

    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT room_name, picture_urls, description, last_updated, doc_by_user_id, edits, tags, roomtype, edited_by_user_id
        FROM room_db
        WHERE LOWER(description) LIKE ?
    """, (f"%{search_term}%",))
    rows = cursor.fetchall()
    conn.close()

    return [{
        'room_name': row[0],
        'picture_urls': json.loads(row[1]),
        'description': row[2],
        'last_updated': row[3],
        'doc_by_user_id': row[4],
        'edits': json.loads(row[5]),
        'tags': json.loads(row[6]),
        'roomtype': row[7],
        'edited_by_user_id': row[8]
    } for row in rows]

def search_rooms_by_roomtype(roomtype: str) -> list:
    """
    Search for rooms that match a specific room type.
    
    Args:
        roomtype: The room type to search for
    """
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT room_name, picture_urls, description, last_updated, doc_by_user_id, edits, tags, roomtype, edited_by_user_id
        FROM room_db
        WHERE roomtype = ?
    """, (roomtype,))
    rows = cursor.fetchall()
    conn.close()

    return [{
        'room_name': row[0],
        'picture_urls': json.loads(row[1]),
        'description': row[2],
        'last_updated': row[3],
        'doc_by_user_id': row[4],
        'edits': json.loads(row[5]),
        'tags': json.loads(row[6]),
        'roomtype': row[7],
        'edited_by_user_id': row[8]
    } for row in rows]

def get_all_room_names(sort_by: str = None) -> list:
    """
    Retrieve a list of all documented room names.

    Args:
        sort_by: The field to sort by (e.g., 'last_updated')

    Returns:
        A list of room names.
    """
    if sort_by is None:
        sort_by = "last_updated"
    
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT room_name FROM room_db ORDER BY {sort_by}")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def clear_room_db():
    """Clear all entries from the room_db table."""
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM room_db")
    conn.commit()
    conn.close()

def get_documented_by_user(user_id: int) -> list:
    """
    Retrieve all rooms documented by a specific user.

    Args:
        user_id: The Discord user ID of the documenting user

    Returns:
        A list of room information dictionaries.
    """
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT room_name, picture_urls, description, last_updated, doc_by_user_id, edits, tags, roomtype, edited_by_user_id
        FROM room_db
        WHERE doc_by_user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    return [{
        'room_name': row[0],
        'picture_urls': json.loads(row[1]),
        'description': row[2],
        'last_updated': row[3],
        'doc_by_user_id': row[4],
        'edits': json.loads(row[5]),
        'tags': json.loads(row[6]),
        'roomtype': row[7],
        'edited_by_user_id': row[8]
    } for row in rows]


def jsonify_room_db() -> Dict[str, Any]:
    """
    Export the entire room database as a JSON-serializable dictionary.

    Returns:
        A dictionary where keys are room names and values are room information.
    """
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT room_name, picture_urls, description, last_updated, doc_by_user_id, edits, tags, roomtype, edited_by_user_id FROM room_db")
    rows = cursor.fetchall()
    conn.close()

    room_data = {}
    for row in rows:
        room_data[row[0]] = {
            'picture_urls': json.loads(row[1]),
            'description': row[2],
            'last_updated': row[3],
            'doc_by_user_id': row[4],
            'edits': json.loads(row[5]),
            'tags': json.loads(row[6]),
            'roomtype': row[7],
            'edited_by_user_id': row[8]
        }
    return room_data

