# This script updates all the tables so that they are compatible with the latest database schema.
# It should be run whenever the database schema is updated.

# On home directory of the project, run:
# python -m automations.scripts.init_dbs
# OR
# python3 -m automations.scripts.init_dbs

from src.datamanager import database_manager

if __name__ == "__main__": # Main entry point enforcement, ensures the script is run directly and not imported on accident.
    # Initialize or update the scanner database tables
    try:
        database_manager.init_databases()
        print("[SCRIPT INIT DBS] Databases initialized or updated successfully.")
        exit(0)
    except Exception as e:
        print(f"[SCRIPT INIT DBS] Failed to initialize or update databases: {e}")
        exit(1)