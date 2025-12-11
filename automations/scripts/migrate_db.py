# This script handles database migration tasks for the project, ensuring that databases are updated to the latest schema version.
# It should be run whenever there are changes to the database schema that require rebuilding. (changing column types, adding/removing columns, etc.)

# On home directory of the project, run:
# python -m automations.scripts.migrate_db <database_file_name.db>
# OR
# python3 -m automations.scripts.migrate_db <database_file_name.db>




if __name__ == "__main__": # Main entry point enforcement, ensures the script is run directly and not imported on accident.
    from src.datamanager import database_manager
    import src.log_manager  # Ensure logging is set up

    # Get argument for which database to migrate
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m automations.scripts.migrate_db <database_file_name.db>")
        exit(1)
    db_name = sys.argv[1]

    # Initialize databases
    database_manager.init_databases()

    # Migrate the specified database
    try:
        database_manager.migrate_db(db_name)
        print(f"[INFO] [SCRIPT MIGRATE DB] Database '{db_name}' migrated successfully.")
        exit(0)
    except Exception as e:
        print(f"[ERROR] [SCRIPT MIGRATE DB] Failed to migrate database '{db_name}': {e}")
        exit(1)