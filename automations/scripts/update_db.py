# This script updates all the tables so that they are compatible with the latest database schema.
# It should be run whenever the database schema is updated.

from src.datamanager import helpers

if __name__ == "__main__": # Main entry point enforcement, ensures the script is run directly and not imported on accident.
    # Initialize or update the scanner database tables
    try:
        helpers.init_databases()
        print("✅ Databases initialized or updated successfully.")
        exit(0)
    except Exception as e:
        print(f"❌ Failed to initialize or update databases: {e}")
        exit(1)