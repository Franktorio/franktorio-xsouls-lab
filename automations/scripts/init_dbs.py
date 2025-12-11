# This script initializes the databases required for the project.
# It should be run to set up or update the database tables before using the application.

# FOR MIGRATIONS, USE migrate_db.py INSTEAD. THIS SCRIPT IS ONLY FOR INITIAL SETUP.

# On home directory of the project, run:
# python -m automations.scripts.init_dbs
# OR
# python3 -m automations.scripts.init_dbs

from src.datamanager import database_manager
import src.log_manager  # Ensure logging is set up

if __name__ == "__main__": # Main entry point enforcement, ensures the script is run directly and not imported on accident.
    # Initialize or update the scanner database tables
    try:
        database_manager.init_databases()
        print("[INFO] [SCRIPT INIT DBS] Databases initialized or updated successfully.")
        exit(0)
    except Exception as e:
        print(f"[ERROR] [SCRIPT INIT DBS] Failed to initialize or update databases: {e}")
        exit(1)