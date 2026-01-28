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
import json
from fastapi.responses import FileResponse

# Local imports
from src.datamanager.db_handlers import room_db_handler, scanner_db_handler
from src.utils.r2_handler import get_paths_of_cached_images
from . import research, scanner
from config.vars import LOCAL_API_ROOT_PATH
from src.shared import FRD_bot

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
    servers_amnt = len(FRD_bot.guilds) if FRD_bot else "Bot not initialized"
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
    }) # commented out just for now, capstone


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve the favicon."""
    favicon_path = os.path.join(STATIC_DIR, "images", "favicon.ico")
    return FileResponse(favicon_path)

@app.get("/robots.txt", include_in_schema=False)
async def robots():
    """Serve the robots.txt file for search engine crawlers."""
    robots_path = os.path.join(STATIC_DIR, "robots.txt")
    return FileResponse(robots_path, media_type="text/plain")

@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap():
    """Serve the sitemap.xml file for search engines."""
    sitemap_path = os.path.join(STATIC_DIR, "sitemap.xml")
    return FileResponse(sitemap_path, media_type="application/xml")

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

@app.get("/franktorio-scanner/data", name="franktorio-scanner-data")
async def franktorio_scanner_data(request: Request):
    """Franktorio's Scanner data page with analytics."""
    print(f"[INFO] [{PRINT_PREFIX}] Received Franktorio Scanner data request.")

    activity_over_time = scanner_db_handler.get_statistic("activity_over_time")
    total_encounters = activity_over_time.get("total_encounters", 0)
    last_update = activity_over_time.get("updated_at", None)

    # Calculate how long ago the last update was and turn it into a readable format like: 5 minutes ago, 2 hours ago, etc.
    if last_update:
        last_update_datetime = datetime.fromtimestamp(last_update)
        time_diff = datetime.now() - last_update_datetime
        seconds = time_diff.total_seconds()
        if seconds < 60:
            last_update = f"{int(seconds)} seconds ago"
        elif seconds < 3600:
            last_update = f"{int(seconds // 60)} minutes ago"
        elif seconds < 86400:
            last_update = f"{int(seconds // 3600)} hours ago"
        else:
            last_update = f"{int(seconds // 86400)} days ago"
    else:
        last_update = "No data available"
    
    # Get all data analysis statistics
    data_context = {
        "request": request,
        "most_common_rooms_hundred": scanner_db_handler.get_statistic("most_common_rooms_hundred"),
        "most_common_rooms_fifty": scanner_db_handler.get_statistic("most_common_rooms_fifty"),
        "most_common_rooms_twentyfive": scanner_db_handler.get_statistic("most_common_rooms_twentyfive"),
        "most_common_rooms_all": scanner_db_handler.get_statistic("most_common_rooms_all"),
        "activity_over_time": activity_over_time,
        "total_encounters": total_encounters,
        "last_update": last_update
    }
    
    return templates.TemplateResponse("scanner-data.html", data_context)