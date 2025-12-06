# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025

# Standard library imports
import json
import sqlite3
import os

# determine project root (two levels up from this file) and put DB in FRD_bot/databases
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_DIR = os.path.join(PROJECT_ROOT, "databases")

ACTIONS_JSON_PATH = os.path.join(DB_DIR, "actions.json")

# Create actions data dictionary from JSON file if it does not exist, create an empty one
if not os.path.exists(ACTIONS_JSON_PATH):
    with open(ACTIONS_JSON_PATH, 'w') as f:
        json.dump({}, f)

with open(ACTIONS_JSON_PATH, 'r') as f:
    actions_data = json.load(f)

def connect_db(db_file_name: str) -> sqlite3.Connection:
    """
    Connect to the database and return the connection.
    
    Automatically creates the database directory and file if they don't exist.
    """
    DB_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), "databases", db_file_name)
    
    # Ensure the databases directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initialize the database file and tables in FRD_bot/databases if they don't exist."""
    # Import here to avoid circular imports
    from . import room_db_handler, server_db_handler, scanner_db_handler
    
    os.makedirs(DB_DIR, exist_ok=True)
    
    # Initialize all tables
    server_db_handler.init_db()
    print("✅ Server profiles table initialized")
    room_db_handler.init_db()
    print("✅ Room database table initialized")
    scanner_db_handler.init_db()
    print("✅ Scanner database table initialized")

    print("🗃️ All databases initialized successfully")