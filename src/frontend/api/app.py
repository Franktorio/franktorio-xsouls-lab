# Franktorio's Research Division
# Author: Franktorio
# January 11th, 2026
# FastAPI application initialization

PRINT_PREFIX = "API APP"

import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Local imports
from src.datamanager.db_handlers import room_db_handler, server_db_handler
from . import research, scanner

# Get absolute path to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
STATIC_DIR = os.path.join(BASE_DIR, "src", "frontend", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "src", "frontend", "templates")

print(f"[INFO] [{PRINT_PREFIX}] BASE_DIR: {BASE_DIR}")
print(f"[INFO] [{PRINT_PREFIX}] STATIC_DIR: {STATIC_DIR}")
print(f"[INFO] [{PRINT_PREFIX}] Static directory exists: {os.path.exists(STATIC_DIR)}")

# Initialize FastAPI app
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include routers
app.include_router(research.router)
app.include_router(scanner.router)

@app.get("/")
async def read_root(request: Request):
    """Root endpoint to verify API is running."""
    print(f"[INFO] [{PRINT_PREFIX}] Received root API request.")
    
    room_amnt = len(room_db_handler.get_all_room_names())
    servers_amnt = len(server_db_handler.get_all_server_profiles())
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return templates.TemplateResponse("root.html", {
        "request": request,
        "room_amnt": room_amnt,
        "servers_amnt": servers_amnt,
        "current_time": current_time
    })
