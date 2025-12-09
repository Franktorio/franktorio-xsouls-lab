# Franktorio's Research Division
# Author: Franktorio
# December 6th 2025
# Backup Manager - Handles backup and restoration of databases

# Standard library imports
import os
import sqlite3
import threading

# Local imports
from .database_manager import DB_DIR, databases
from .db_handlers import server_db_handler, room_db_handler, scanner_db_handler, action_json_handler

BACKUP_DIR = os.path.join(DB_DIR, "backups")
SNAPSHOT_DIR = os.path.join(DB_DIR, "snapshots")
REPLICA_DIR = os.path.join(DB_DIR, "replicas")

# Ensure database backups directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)
