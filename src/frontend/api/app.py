# Franktorio's Research Division
# Author: Franktorio
# January 11th, 2026
# FastAPI application initialization

PRINT_PREFIX = "API APP"

from logging import root
import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse

# Local imports
from src.datamanager.db_handlers import room_db_handler, server_db_handler
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

@app.get("/", name="root")
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

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve the favicon."""
    favicon_path = os.path.join(STATIC_DIR, "images", "favicon.ico")
    return FileResponse(favicon_path)