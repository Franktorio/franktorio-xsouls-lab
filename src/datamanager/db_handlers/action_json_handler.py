# Franktorio's Research Division
# Author: Franktorio
# December 6th 2025
# Action JSON Handler - Manages actions.json file

PRINT_PREFIX = "ACTION JSON"

# Standard library imports
import json
import os

# Determine project root and actions.json path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DB_DIR = os.path.join(PROJECT_ROOT, "databases")
ACTIONS_JSON_PATH = os.path.join(DB_DIR, "actions.json")

# Ensure directory exists
os.makedirs(DB_DIR, exist_ok=True)

# Create actions.json if it doesn't exist
if not os.path.exists(ACTIONS_JSON_PATH):
    with open(ACTIONS_JSON_PATH, 'w') as f:
        json.dump({}, f)

# Load actions data
with open(ACTIONS_JSON_PATH, 'r') as f:
    actions_data = json.load(f)

def save_actions_json() -> None:
    """Save the actions_data dictionary to actions.json file."""
    with open(ACTIONS_JSON_PATH, 'w') as f:
        json.dump(actions_data, f, indent=2)

def get_action(key: str, default=None):
    """Get an action value from actions_data."""
    return actions_data.get(key, default)

def set_action(key: str, value) -> None:
    """Set an action value in actions_data and save to file."""
    actions_data[key] = value
    save_actions_json()