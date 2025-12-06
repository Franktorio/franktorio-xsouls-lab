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
from .helpers import connect_db

DB_FILE_NAME = "frd_bot.db"

def _connect_db() -> sqlite3.Connection:
    """Connect to the scanner database and return the connection."""
    return connect_db(DB_FILE_NAME)

def init_db():
    """Initialize the database with the required tables."""
    conn = _connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_edited_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            scanner_version TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS encountered_rooms (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_event TEXT NOT NULL,
            session_id TEXT NOT NULL,
            room_name TEXT NOT NULL,
            found_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_last_edited_at
        AFTER INSERT ON encountered_rooms
        BEGIN
            UPDATE sessions
            SET last_edited_at = CURRENT_TIMESTAMP
            WHERE session_id = NEW.session_id;
        END;
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

