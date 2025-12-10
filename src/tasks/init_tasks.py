# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Task initialization

PRINT_PREFIX = "TASK INIT"

# Local imports
from .build_documented import build_documented_channels
from .update_leaderboard import update_leaderboard
from .sync_databases import sync_databases


def start_all_tasks():
    """Start all scheduled background tasks"""
    print(f"[{PRINT_PREFIX}] Starting all background tasks...")
    tasks_to_start = [
        (build_documented_channels, "Build Documented Channels Task"),
        (update_leaderboard, "Update Leaderboard Task"),
        (sync_databases, "Sync Databases Task"),
    ]
    # Start each task if it's not already running
    for task, name in tasks_to_start:
        if not task.is_running():
            task.start()
            print(f"[{PRINT_PREFIX}] {name} started")
        else:
            print(f"[{PRINT_PREFIX}] {name} already running")
