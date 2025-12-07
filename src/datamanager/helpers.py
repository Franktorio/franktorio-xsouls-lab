# Franktorio's Research Division
# Author: Franktorio
# December 6th 2025
# Legacy helpers module - redirects to database_manager

from .database_manager import connect_db, init_databases, DB_DIR, PROJECT_ROOT
from .db_handlers.action_json_handler import actions_data, save_actions_json

__all__ = ['connect_db', 'init_databases', 'DB_DIR', 'PROJECT_ROOT', 'actions_data', 'save_actions_json']