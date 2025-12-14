# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Scanner database handler

PRINT_PREFIX = "SCANNER DB"

# Standard library imports
import sqlite3
import threading
import random
import string
import hashlib
import os
import time

# Local imports
from ..database_manager import connect_db


DB_FILE_NAME = "frd_scanner.db"
SESSION_LIFE = 7200  # 2 hours in seconds
TASK_FREQUENCY = 600  # 10 minutes in seconds
SCHEMA = {
    "sessions": """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            last_edited_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            session_password TEXT,
            scanner_version TEXT NOT NULL,
            closed INTEGER NOT NULL DEFAULT 0
        );
    """,
    
    "encountered_rooms": """
        CREATE TABLE IF NOT EXISTS encountered_rooms (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            room_name TEXT NOT NULL,
            found_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
    """
}


def _connect_db() -> sqlite3.Connection:
    """Connect to the scanner database and return the connection."""
    return connect_db(DB_FILE_NAME)

def _close_sessions_task():
    """Background task to periodically close old sessions."""
    from time import sleep

    def close_old_sessions() -> None:
        """Close sessions that have been inactive for longer than SESSION_LIFE."""
        conn = _connect_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sessions
            SET closed = 1
            WHERE closed = 0 AND (strftime('%s', 'now') - last_edited_at) > ?
        """, (SESSION_LIFE,))
        
        conn.commit()
        conn.close()

        print(f"[INFO] [{PRINT_PREFIX}] Closed old sessions inactive for more than {SESSION_LIFE} seconds.")

    while True:
        close_old_sessions()
        sleep(TASK_FREQUENCY)  # Run every 10 minutes

def _generate_session_id() -> str:
    """Generate a random alphanumeric session ID."""
    length = 16
    characters = string.ascii_letters + string.digits
    session_id = ''.join(random.choice(characters) for _ in range(length))
    return session_id

def _generate_password(length: int = 12) -> str:
    """Generate a random alphanumeric password of given length."""

    characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

def _hash_password(password: str) -> str:
    """Hash a password securely."""

    salt = os.urandom(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + pwdhash.hex()

def _compare_password(stored_password: str, provided_password: str) -> bool:
    """Compare a stored hashed password with a provided password."""

    salt = bytes.fromhex(stored_password[:32])
    stored_pwdhash = stored_password[32:]
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
    return pwdhash.hex() == stored_pwdhash

def init_scanner_extras():
    """Initialize database triggers and indexes after tables are created."""
    conn = _connect_db()
    cursor = conn.cursor()
    
    # Create trigger to update last_edited_at on sessions table
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_last_edited_at
        AFTER INSERT ON encountered_rooms
        BEGIN
            UPDATE sessions
            SET last_edited_at = strftime('%s', 'now')
            WHERE session_id = NEW.session_id;
        END;
    """)

    # Create indexes for performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_open_closed 
        ON sessions(closed)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_rooms_session_id 
        ON encountered_rooms(session_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_rooms_found_at 
        ON encountered_rooms(found_at)
    """)
    
    conn.commit()
    conn.close()

    # Start the background task to close old sessions
    threading.Thread(target=_close_sessions_task, daemon=True).start()


def start_session(scanner_version: str) -> tuple[str, str]:
    """
    Start a new scanning session.
    
    Args:
        scanner_version: The version of the scanner software.
    Returns:
        A tuple containing (session_id, password).
    """
    conn = _connect_db()
    cursor = conn.cursor()

    password = _generate_password()
    session_id = _generate_session_id()
    
    cursor.execute("""
        INSERT INTO sessions (session_id, scanner_version, session_password)
        VALUES (?, ?, ?)
    """, (session_id, scanner_version, _hash_password(password)))
    
    conn.commit()
    conn.close()
    
    print(f"[INFO] [{PRINT_PREFIX}] Started new session {session_id} with scanner version {scanner_version}.")
    return session_id, password

def validate_session(session_id: str, session_password: str) -> bool:
    """Validate a scanning session. 
    Will obfuscate and always take the same time to prevent timing attacks.
    Returns:
        True if the session is valid and open, False otherwise.
    """
    start = time.time()
    end = start + 1.0  # Ensure at least 1 second of processing time
    conn = _connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT session_password
        FROM sessions
        WHERE session_id = ? AND closed = 0
    """, (session_id,))
    stored_password = cursor.fetchone()
    conn.close()

    if stored_password is None:
        time.sleep(max(0, end - time.time()))
        print(f"[ERROR] [{PRINT_PREFIX}] Session {session_id} is invalid or closed.")
        return False
    
    is_valid = _compare_password(stored_password[0], session_password)
    if not is_valid:
        time.sleep(max(0, end - time.time()))
        print(f"[ERROR] [{PRINT_PREFIX}] Invalid password for session {session_id}.")
    return is_valid

def end_session(session_id: str, session_password: str) -> bool:
    """End a scanning session.
    
    Returns:
        True if the session was ended successfully, False otherwise.
    """
    conn = _connect_db()
    cursor = conn.cursor()

    # Verify session password
    cursor.execute("""
        SELECT session_password
        FROM sessions
        WHERE session_id = ? AND closed = 0
    """, (session_id,))
    stored_password = cursor.fetchone()
    if stored_password is None or not _compare_password(stored_password[0], session_password):
        conn.close()
        print(f"[ERROR] [{PRINT_PREFIX}] Failed to end session {session_id}: invalid session ID or password, or session is already closed.")
        return False
    
    cursor.execute("""
        UPDATE sessions
        SET closed = 1
        WHERE session_id = ?
    """, (session_id,))
    
    print(f"[INFO] [{PRINT_PREFIX}] Ended session {session_id}.")
    conn.commit()
    conn.close()
    return True

def log_encountered_room(session_id: str, room_name: str, session_password: str) -> bool:
    """
    Log an encountered room during a scanning session.
    
    Args:
        session_id: The ID of the scanning session.
        room_name: The name of the encountered room.
    
    Returns:
        True if the room was logged successfully, False otherwise.
    """
    conn = _connect_db()
    cursor = conn.cursor()

    # Verify session password, will return False if invalid or if session is closed
    cursor.execute("""
        SELECT session_password
        FROM sessions
        WHERE session_id = ? AND closed = 0
    """, (session_id,))
    stored_password = cursor.fetchone()
    if stored_password is None or not _compare_password(stored_password[0], session_password):
        conn.close()
        print(f"[ERROR] [{PRINT_PREFIX}] Failed to log room '{room_name}': invalid session ID or password, or session is closed.")
        return False
    
    cursor.execute("""
        INSERT INTO encountered_rooms (session_id, room_name)
        VALUES (?, ?)
    """, (session_id, room_name))

    success = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    
    print(f"[INFO] [{PRINT_PREFIX}] Logged encountered room '{room_name}' in session {session_id}.")
    return success

def get_sessions(include_closed: bool = True) -> list[tuple]:
    """
    Get a list of sessions in descending order by creation date (newest first).
    
    Returns:
        A list of tuples containing (session_id, created_at, last_edited_at, scanner_version, closed).
    """
    conn = _connect_db()
    cursor = conn.cursor()
    
    if include_closed:
        cursor.execute("""
            SELECT session_id, created_at, last_edited_at, scanner_version, closed
            FROM sessions
            ORDER BY created_at DESC
        """)
    else:
        cursor.execute("""
            SELECT session_id, created_at, last_edited_at, scanner_version, closed
            FROM sessions
            WHERE closed = 0
            ORDER BY created_at DESC
        """)
    
    sessions = cursor.fetchall()
    conn.close()

    print(f"[INFO] [{PRINT_PREFIX}] Retrieved {'all' if include_closed else 'open'} sessions.")
    return sessions

def get_session_rooms(session_id: str) -> list[tuple]:
    """
    Get a list of rooms encountered in a specific session in ascending order by the time they were found (latest first).
    
    Returns:
        A list of tuples containing (room_name, found_at).
    """
    conn = _connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT room_name, found_at
        FROM encountered_rooms
        WHERE session_id = ?
        ORDER BY found_at ASC
    """, (session_id,))
    
    encounters = cursor.fetchall()
    conn.close()
    
    print(f"[INFO] [{PRINT_PREFIX}] Retrieved encountered rooms for session {session_id}.")
    return encounters

def get_all_encountered_rooms() -> list[tuple]:
    """
    Get a list of all encountered rooms across all sessions in ascending order by the time they were found (latest first).
    
    Returns:
        A list of tuples containing (session_id, room_name, found_at).
    """
    conn = _connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT session_id, room_name, found_at
        FROM encountered_rooms
        ORDER BY found_at ASC
    """)
    
    encounters = cursor.fetchall()
    conn.close()
    
    print(f"[INFO] [{PRINT_PREFIX}] Retrieved all encountered rooms across all sessions.")
    return encounters

def jsonify_database() -> dict[str, any]:
    """
    Convert the entire scanner database into a JSON-serializable dictionary.
    Returns:
        A dictionary representation of the scanner database of structure.
        {
            "sessions": {
                session_id: {
                    "session_id": str,
                    "created_at": int,
                    "last_edited_at": int,
                    "scanner_version": str,
                    "closed": bool,
                    "rooms": [
                        {
                            "event_id": int,
                            "room_name": str,
                            "found_at": int
                        },
                        ...
                    ]
                },
            }
            "encountered_rooms": [
                {
                    "event_id": int,
                    "session_id": str,
                    "room_name": str,
                    "found_at": int
                },
                ...
            ]
        }
    """
    conn = _connect_db()
    cursor = conn.cursor()
    
    data = {
        "sessions": {},
        "encountered_rooms": []
    }
    
    # Fetch sessions
    cursor.execute("SELECT session_id, created_at, last_edited_at, scanner_version, closed FROM sessions")
    sessions = cursor.fetchall()
    for session_row in sessions:
        data["sessions"][session_row[0]] = {
            "session_id": session_row[0],
            "created_at": session_row[1],
            "last_edited_at": session_row[2],
            "scanner_version": session_row[3],
            "closed": bool(session_row[4]),
            "rooms": []
        }
    
    # Fetch encountered rooms
    cursor.execute("SELECT event_id, session_id, room_name, found_at FROM encountered_rooms")
    rooms = cursor.fetchall()
    for room_row in rooms:
        data["encountered_rooms"].append({
            "event_id": room_row[0],
            "session_id": room_row[1],
            "room_name": room_row[2],
            "found_at": room_row[3]
        })
        # Associate rooms with their respective sessions
        session = room_row[1]
        if session in data["sessions"]:
            data["sessions"][session]["rooms"].append({
                "event_id": room_row[0],
                "room_name": room_row[2],
                "found_at": room_row[3]
            })

    conn.close()

    print(f"[INFO] [{PRINT_PREFIX}] Converted database to JSON-serializable dictionary.")
    return data
