# Franktorio's Research Division
# Author: Franktorio
# December 6th 2025
# Backup Manager - Handles backup and restoration of databases


# Standard library imports
import os
import sqlite3
import datetime
import threading

# Local imports
import config.vars as vars
from .db_handlers import action_json_handler
from .database_manager import DB_DIR, databases, connect_db

# Directories for backups
BACKUP_DIR = ""
SNAPSHOT_DIR = ""
REPLICA_DIR = ""

def init_backup_manager():
    """
    Initializes and starts the backup manager thread if database backups are enabled.
    """
    if not vars.DATABASE_BACKUPS_ENABLED:
        print("[BACKUPS] Database backups are disabled in configuration.")
    else:
        global BACKUP_DIR, SNAPSHOT_DIR, REPLICA_DIR

        BACKUP_DIR = os.path.join(DB_DIR, "backups")
        SNAPSHOT_DIR = os.path.join(BACKUP_DIR, "snapshots")
        REPLICA_DIR = os.path.join(BACKUP_DIR, "replicas")

        # Ensure database backups directory exists
        os.makedirs(BACKUP_DIR, exist_ok=True)
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        os.makedirs(REPLICA_DIR, exist_ok=True)

        backup_thread = threading.Thread(target=backup_manager, daemon=True)
        backup_thread.start()

def create_snapshot(db_file_name: str) -> bool:
    """
    Create a snapshot of the specified database in the snapshots directory.
    Args:
        db_file_name: Name of the database file to snapshot
    Returns:
        bool: True if snapshot creation was successful, False otherwise
    """

    try:
        with open(os.path.join(DB_DIR, db_file_name), 'rb') as src_file:
            with open(os.path.join(SNAPSHOT_DIR, db_file_name+f"_snapshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"), 'wb') as dest_file:
                dest_file.write(src_file.read())
    except Exception as e:
        print(f"[BACKUPS] Failed to create snapshot for {db_file_name}: {e}")
        return False
    return True

def create_replica(db_file_name: str) -> bool:
    """
    Create a replica of the specified database in the replicas directory and replaces the old replica.
    Args:
        db_file_name: Name of the database file to replicate 
    Returns:
        bool: True if replica creation was successful, False otherwise
    """

    try:
        with open(os.path.join(DB_DIR, db_file_name), 'rb') as src_file:
            with open(os.path.join(REPLICA_DIR, db_file_name), 'wb') as dest_file:
                dest_file.write(src_file.read())
    except Exception as e:
        print(f"[BACKUPS] Failed to create replica for {db_file_name}: {e}")
        return False
    return True

def restore_from_replica(db_file_name: str) -> bool:
    """
    Restore the specified database from its replica.
    
    Args:
        db_file_name: Name of the database file to restore
    Returns:
        bool: True if restoration was successful, False otherwise
    """
    try:
        with open(os.path.join(REPLICA_DIR, db_file_name), 'rb') as src_file:
            with open(os.path.join(DB_DIR, db_file_name), 'wb') as dest_file:
                dest_file.write(src_file.read())
    except Exception as e:
        print(f"[BACKUPS] Failed to restore {db_file_name} from replica: {e}")
        return False
    return True

def restore_from_snapshot(db_file_name: str, index: int) -> bool:
    """
    Restore the specified database from a snapshot.
    
    Args:
        db_file_name: Name of the database file to restore
        index: Index of the snapshot to restore from (0 = most recent)
    Returns:
        bool: True if restoration was successful, False otherwise
    """

    try:
        # List all snapshots for the database
        snapshots = [f for f in os.listdir(SNAPSHOT_DIR) if f.startswith(db_file_name+"_snapshot_")]
        snapshots.sort(key=lambda x: os.path.getmtime(os.path.join(SNAPSHOT_DIR, x)), reverse=True)

        if index >= len(snapshots):
            print(f"[BACKUPS] No snapshot available at index {index} for {db_file_name}.")
            return False

        snapshot_file = snapshots[index]

        with open(os.path.join(SNAPSHOT_DIR, snapshot_file), 'rb') as src_file:
            with open(os.path.join(DB_DIR, db_file_name), 'wb') as dest_file:
                dest_file.write(src_file.read())
    except Exception as e:
        print(f"[BACKUPS] Failed to restore {db_file_name} from snapshot: {e}")
        return False
    return True

def db_integrity_check(db_file_name: str) -> bool:
    """
    Perform an integrity check on the specified database.
    
    Args:
        db_file_name: Name of the database file to check
        
    Returns:
        bool: True if the database is intact, False otherwise
    """
    try:
        conn = connect_db(db_file_name, read_only=True)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check(1);") # Check up to 1 error
        result = cursor.fetchone()
        conn.close()
        return result[0] == "ok"
    except sqlite3.DatabaseError as e:
        print(f"[BACKUPS] Database integrity check failed for {db_file_name}: {e}")
        return False

def backup_manager(interval: int = 10): # Runs every 10 seconds
    """
    Runs every few seconds to create snapshots and replicas of databases when their interval is met.
    It will:
    - Perform integrity checks
    - Create snapshots
    - Create replicas

    If main database fails the integrity check, it will attempt to restore from the replica, and
    if the replica also shows integrity issues, it will rollback to the nearest snapshot.
    """

    while True:
        time_now = datetime.datetime.now().timestamp()
        last_snapshot = action_json_handler.get_action("last_snapshot_time", 0)
        last_replica = action_json_handler.get_action("last_replica_time", 0)

        # Do integrity checks on all databases
        for db_file in databases:
            check = db_integrity_check(db_file)

            if check:
                continue

            print(f"[BACKUPS] Integrity check failed for {db_file}. Attempting restoration.")

            # Try restoring from replica
            replica_success = restore_from_replica(db_file)
            if replica_success and db_integrity_check(db_file):
                print(f"[BACKUPS] Successfully restored {db_file} from replica.")
                continue
            
            for i in range(3): # Try up to 3 snapshots
                snapshot_success = restore_from_snapshot(db_file, i)
                if snapshot_success and db_integrity_check(db_file):
                    print(f"[BACKUPS] Successfully restored {db_file} from snapshot index {i}.")
                    break
        
        # Create snapshot if interval met
        if time_now - last_snapshot >= vars.DATABASE_ROLLOVER_INTERVAL:
            for db_file in databases:
                snapshot_success = create_snapshot(db_file)
                if snapshot_success:
                    print(f"[BACKUPS] Created snapshot for {db_file}.")
            action_json_handler.set_action("last_snapshot_time", time_now)
        
        # Create replica if interval met
        if time_now - last_replica >= vars.DATABASE_REPLICATION_INTERVAL:
            for db_file in databases:
                replica_success = create_replica(db_file)
                if replica_success:
                    print(f"[BACKUPS] Created replica for {db_file}.")
            action_json_handler.set_action("last_replica_time", time_now)
        
        # Delete old snapshots beyond retention period
        for snapshot_file in os.listdir(SNAPSHOT_DIR):
            snapshot_path = os.path.join(SNAPSHOT_DIR, snapshot_file)
            time_created = os.path.getmtime(snapshot_path)
            if time_now - time_created >= vars.DATABASE_ROLLOVER_MAX_AGE:
                try:
                    os.remove(snapshot_path)
                    print(f"[BACKUPS] Deleted old snapshot: {snapshot_file}.")
                except Exception as e:
                    print(f"[BACKUPS] Failed to delete old snapshot {snapshot_file}: {e}")
    
        threading.Event().wait(interval)


