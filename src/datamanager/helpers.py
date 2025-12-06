# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025

# Standard library imports
import json
import sqlite3
from typing import Dict, Any
import os

# determine project root (two levels up from this file) and put DB in FRD_bot/databases
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_DIR = os.path.join(PROJECT_ROOT, "databases") # Directory for database files

# Create folder if it doesn't exist
os.makedirs(DB_DIR, exist_ok=True)

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


def init_table(schema: Dict[str, Any], db_file_name: str):
    """Initialize a database with the given schema if it doesn't exist."""
    conn = connect_db(db_file_name)
    cursor = conn.cursor()
    argument = f"{schema['arg']} ({', '.join(schema['tables'])})"
    cursor.execute(argument)
    conn.commit()
    conn.close()

    update_db(schema, db_file_name)
    remove_unused_tables(schema, db_file_name)


def update_db(schema: Dict[str, Any], db_file_name: str):
    """Update a database with the given schema."""
    conn = connect_db(db_file_name)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({schema['arg'].split()[-1]})")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # Add missing columns
    for column_def in schema['tables']:
        column_name = column_def.split()[0]
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE {schema['arg'].split()[-1]} ADD COLUMN {column_def}")

    conn.commit()
    conn.close()

def remove_unused_tables(schema: Dict[str, Any], db_file_name: str) -> bool:
    """Remove unused tables from the database that are not in the schema."""
    conn = connect_db(db_file_name)
    cursor = conn.cursor()
    
    # Get existing tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = {row[0] for row in cursor.fetchall()}
    
    # Determine the table name from the schema argument
    table_name = schema['arg'].split()[-1]
    
    # If the table is not in the schema, drop it
    if table_name not in existing_tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def init_databases():
    """Initialize the database file and tables in FRD_bot/databases if they don't exist."""
    # Import here to avoid circular imports
    from . import room_db_handler, server_db_handler, scanner_db_handler
    
    os.makedirs(DB_DIR, exist_ok=True)
    
    # Initialize server profiles table (in frd_bot.db)
    init_table(server_db_handler.SERVER_SCHEMA, server_db_handler.DB_FILE_NAME)
    print("✅ Server profiles table initialized")
    
    # Initialize room database table (in frd_room.db)
    init_table(room_db_handler.ROOM_SCHEMA, room_db_handler.DB_FILE_NAME)
    print("✅ Room database table initialized")
    
    # Initialize scanner database tables (in frd_scanner.db)
    init_table(scanner_db_handler.SESSIONS_SCHEMA, scanner_db_handler.DB_FILE_NAME)
    init_table(scanner_db_handler.ENCOUNTERED_ROOMS_SCHEMA, scanner_db_handler.DB_FILE_NAME)
    scanner_db_handler.init_scanner_extras()
    print("✅ Scanner database tables initialized")

    print("🗃️ All databases initialized successfully")
