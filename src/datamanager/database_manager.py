# Franktorio's Research Division
# Author: Franktorio
# December 6th 2025
# Database Manager - Handles initialization of all databases

# Standard library imports
import os
import sqlite3
from typing import Dict

# Determine project root (two levels up from this file) and put DB in FRD_bot/databases
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_DIR = os.path.join(PROJECT_ROOT, "databases")

databases = {}

# Ensure databases directory exists
os.makedirs(DB_DIR, exist_ok=True)

def connect_db(db_file_name: str, read_only: bool = False) -> sqlite3.Connection:
    """
    Connect to a database and return the connection.
    Automatically creates the database directory and file if they don't exist.
    
    Args:
        db_file_name: Name of the database file
        
    Returns:
        sqlite3.Connection: Database connection
    """
    db_path = os.path.join(DB_DIR, db_file_name)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if read_only:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    else:
        conn = sqlite3.connect(db_path)

def _init_tables_from_schema(schema: Dict[str, str], db_file_name: str) -> None:
    """
    Initialize database tables from schema dictionary.
    
    Args:
        schema: Dictionary mapping table names to CREATE TABLE statements
        db_file_name: Name of the database file
    """
    conn = connect_db(db_file_name)
    cursor = conn.cursor()
    
    for table_name, create_statement in schema.items():
        cursor.execute(create_statement)
    
    conn.commit()
    conn.close()

def init_databases() -> None:
    """
    Initialize all database files and tables.
    This should be called once at startup.
    """
    # Import here to avoid circular imports
    from .db_handlers import server_db_handler, room_db_handler, scanner_db_handler
    
    os.makedirs(DB_DIR, exist_ok=True)
    
    # Initialize server database
    _init_tables_from_schema(server_db_handler.SCHEMA, server_db_handler.DB_FILE_NAME)
    databases[server_db_handler.DB_FILE_NAME] = server_db_handler
    print("[DB INIT] Server database initialized")
    
    # Initialize room database
    _init_tables_from_schema(room_db_handler.SCHEMA, room_db_handler.DB_FILE_NAME)
    databases[room_db_handler.DB_FILE_NAME] = room_db_handler
    print("[DB INIT] Room database initialized")
    
    # Initialize scanner database
    _init_tables_from_schema(scanner_db_handler.SCHEMA, scanner_db_handler.DB_FILE_NAME)
    scanner_db_handler.init_scanner_extras()
    databases[scanner_db_handler.DB_FILE_NAME] = scanner_db_handler
    print("[DB INIT] Scanner database initialized")
    
    print("[DB INIT] All databases initialized successfully")

def migrate_db(db_file_name: str) -> None:
    if db_file_name not in databases:
        raise ValueError(f"Unknown database file: {db_file_name}")

    desired_schema = databases[db_file_name].SCHEMA
    old_db_path = os.path.join(DB_DIR, db_file_name)

    temp_db_path = os.path.join(DB_DIR, f"temp_{db_file_name}")
    temp_conn = sqlite3.connect(temp_db_path)
    temp_cursor = temp_conn.cursor()

    # Initialize desired schema onto the new temp database
    for ddl in desired_schema.values():
        temp_cursor.execute(ddl)

    # Load old database into the connection
    temp_cursor.execute(f"ATTACH DATABASE '{old_db_path}' AS olddb")

    # For each table in the desired schema, copy data from old to new if columns match
    for table_name in desired_schema.keys():
        # Get columns from old table
        temp_cursor.execute(f"PRAGMA olddb.table_info({table_name})")
        old_columns_info = temp_cursor.fetchall()
        old_columns = {col[1] for col in old_columns_info}

        # Get columns from new table
        temp_cursor.execute(f"PRAGMA table_info({table_name})")
        new_columns_info = temp_cursor.fetchall()
        new_columns = {col[1] for col in new_columns_info}

        # Determine common columns
        common_columns = old_columns.intersection(new_columns)
        if not common_columns:
            continue  # No common columns to copy

        columns_str = ", ".join(common_columns)

        # Copy data from old to new table
        temp_cursor.execute(f"""
            INSERT INTO {table_name} ({columns_str})
            SELECT {columns_str} FROM olddb.{table_name}
        """)



    # Cleanup
    temp_conn.commit()
    temp_conn.close()
    os.replace(temp_db_path, old_db_path)
