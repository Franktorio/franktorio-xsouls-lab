# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Scanner database handler

# Standard library imports
import sqlite3
import datetime
import os
from typing import Optional, Dict, Any, List, Tuple

# Local imports
from ..database_manager import connect_db

DB_FILE_NAME = "frd_scanner.db"

SCHEMA = {
    "sessions": """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            last_edited_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            scanner_version TEXT NOT NULL,
            closed INTEGER NOT NULL DEFAULT 0
        );
    """,
    
    "encountered_rooms": """
        CREATE TABLE IF NOT EXISTS encountered_rooms (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_event TEXT NOT NULL,
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

def start_session(session_id: str, scanner_version: str) -> None:
    """Start a new scanning session."""
    conn = _connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO sessions (session_id, scanner_version)
        VALUES (?, ?)
    """, (session_id, scanner_version))
    
    conn.commit()
    conn.close()
