# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Scanner database handler

# Standard library imports
import re
import sqlite3
import datetime
import json
import os
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), "databases", "frd_bot.db")