# Franktorio's Research Division
# Author: Franktorio
# January 11th, 2026
# FastAPI application initialization

PRINT_PREFIX = "API APP"

import os
import random
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse

# Local imports
from src.datamanager.db_handlers import room_db_handler, server_db_handler
from src.utils.r2_handler import get_paths_of_cached_images
from . import research, scanner
from config.vars import LOCAL_API_ROOT_PATH

# Get absolute path to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(BASE_DIR, "frontend", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "frontend", "templates")

print(f"[INFO] [{PRINT_PREFIX}] BASE_DIR: {BASE_DIR}")
print(f"[INFO] [{PRINT_PREFIX}] STATIC_DIR: {STATIC_DIR}")
print(f"[INFO] [{PRINT_PREFIX}] Static directory exists: {os.path.exists(STATIC_DIR)}")

# Initialize FastAPI app
app = FastAPI(root_path=LOCAL_API_ROOT_PATH)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# Include routers
app.include_router(research.router)
app.include_router(scanner.router)

@app.get("/", name="index")
async def read_root(request: Request):
    """Root endpoint to verify API is running."""
    print(f"[INFO] [{PRINT_PREFIX}] Received index request.")
    
    rooms = room_db_handler.get_all_room_names()
    servers_amnt = len(server_db_handler.get_all_server_profiles())
    room_amnt = len(rooms)

    try:
        random_room = random.choice(rooms)
        room_data = room_db_handler.get_roominfo(random_room)
        room_data["picture_urls"] = room_data["picture_urls"][:4]  # Limit to first 4 images
        room_data["tags"].append("No Tags! Please add some!") if not room_data["tags"] else None
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Failed to fetch random room data: {e}")
        room_data = None

    return templates.TemplateResponse("index.html", {
        "request": request,
        "room_amnt": room_amnt,
        "servers_amnt": servers_amnt,
        "image_amnt": len(get_paths_of_cached_images()),
        "room_data": room_data
    })

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve the favicon."""
    favicon_path = os.path.join(STATIC_DIR, "images", "favicon.ico")
    return FileResponse(favicon_path)

@app.get("/commands", name="bot_commands")
async def bot_commands(request: Request):
    """Bot commands documentation page."""
    print(f"[INFO] [{PRINT_PREFIX}] Received bot commands request.")
    return templates.TemplateResponse("commands.html", {"request": request})

@app.get("/franktorio-scanner", name="franktorio-scanner")
async def franktorio_scanner(request: Request):
    """Franktorio's Scanner information page."""
    print(f"[INFO] [{PRINT_PREFIX}] Received Franktorio Scanner request.")
    return templates.TemplateResponse("franktorio-scanner.html", {"request": request})