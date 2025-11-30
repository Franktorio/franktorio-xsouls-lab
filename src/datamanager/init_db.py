# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025

# Standard library imports
import json
import sqlite3
import os

# Local imports
from . import room_db_handler, server_profiler

# determine project root (two levels up from this file) and put DB in FRD_bot/databases
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_DIR = os.path.join(PROJECT_ROOT, "databases")

ACTIONS_JSON_PATH = os.path.join(DB_DIR, "actions.json")
with open(ACTIONS_JSON_PATH, 'r') as f:
    actions_data = json.load(f)

def init_db():
    """Initialize the database file and tables in FRD_bot/databases if they don't exist."""
    os.makedirs(DB_DIR, exist_ok=True)
    
    # Initialize all tables
    server_profiler.init_server_profiles_table()
    print("✅ Server profiles table initialized")
    room_db_handler.init_room_db_table()
    print("✅ Room database table initialized")
    print("✅ Database initialization complete")
