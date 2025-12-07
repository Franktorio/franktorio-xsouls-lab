# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# API handler for internal research operations

# Standard library imports
from datetime import datetime
from typing import Optional

# Third-party imports
from fastapi import FastAPI, Query
from pydantic import BaseModel

# Local imports
from config.vars import LOCAL_KEY
from src.datamanager.db_handlers import room_db_handler, server_db_handler, scanner_db_handler
from src.utils import utils

app = FastAPI()


# Pydantic models for request bodies
class DocumentRoomRequest(BaseModel):
    room_name: str
    roomtype: str
    picture_urls: list[str]
    description: str
    doc_by_user_id: int
    tags: Optional[list[str]] = None
    timestamp: Optional[float] = None


class RedocumentRoomRequest(BaseModel):
    room_name: str
    roomtype: str
    picture_urls: list[str]
    description: str
    doc_by_user_id: int
    edited_by_user_id: int
    tags: Optional[list[str]] = None
    timestamp: Optional[float] = None


class SetRoomTypeRequest(BaseModel):
    room_name: str
    roomtype: str
    edited_by_user_id: int


class SetTagsRequest(BaseModel):
    room_name: str
    tags: list[str]
    edited_by_user_id: int


@app.get("/")
async def read_root(key: str):
    """Root endpoint to verify API is running."""
    if key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    room_amnt = len(room_db_handler.get_all_room_names())
    servers_amnt = len(server_db_handler.get_all_server_profiles())
    current_time = datetime.now().timestamp()

    return {"message": f"Research API is running. {room_amnt} rooms documented. {servers_amnt} servers using the bot. Current timestamp: {current_time} UTC."}


@app.get("/get_researcher_role")
async def get_researcher_role(key: str, user_id: int):
    """Endpoint to get a user's research level"""
    if key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    research_level = await utils.get_researcher_role(user_id)
    return {"user_id": user_id, "research_level": research_level}

@app.get("/get_user_profile")
async def get_user_profile(key: str, user_id: int):
    """Endpoint to get a user's profile picture URL, username, and display name"""
    if key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    user_data = utils.get_user_profile(user_id)
    return {
        "user_id": user_id,
        "profile_picture_url": user_data["profile_picture_url"],
        "username": user_data["username"],
        "display_name": user_data["display_name"]
    }


@app.post("/document_room")
async def document_room(request: DocumentRoomRequest, key: str = Query(...)):
    """Endpoint to document a room"""
    if key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    room_profile = room_db_handler.get_roominfo(request.room_name)
    if room_profile:
        return {"error": "Room already documented, use the redocumentation endpoint."}
    
    timestamp = request.timestamp if request.timestamp is not None else datetime.now().timestamp()
    tags = request.tags if request.tags is not None else []
    
    room_db_handler.document_room(
        room_name=request.room_name,
        roomtype=request.roomtype,
        picture_urls=request.picture_urls[:10],  # Max 10 images
        description=request.description,
        doc_by_user_id=request.doc_by_user_id,
        tags=tags,
        timestamp=timestamp
    )
    
    return {"success": True, "message": f"Room '{request.room_name}' has been documented."}


@app.post("/redocument_room")
async def redocument_room(request: RedocumentRoomRequest, key: str = Query(...)):
    """Endpoint to redocument an existing room"""
    if key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    room_profile = room_db_handler.get_roominfo(request.room_name)
    if not room_profile:
        return {"error": "Room does not exist, use the document endpoint first."}
    
    timestamp = request.timestamp if request.timestamp is not None else datetime.now().timestamp()
    tags = request.tags if request.tags is not None else []
    
    room_db_handler.document_room(
        room_name=request.room_name,
        roomtype=request.roomtype,
        picture_urls=request.picture_urls[:10],  # Max 10 images
        description=request.description,
        doc_by_user_id=request.doc_by_user_id,
        tags=tags,
        timestamp=timestamp,
        edited_by_user_id=request.edited_by_user_id
    )
    
    await utils.global_reset(request.room_name)
    
    return {"success": True, "message": f"Room '{request.room_name}' has been redocumented."}


@app.post("/set_roomtype")
async def set_roomtype(request: SetRoomTypeRequest, key: str = Query(...)):
    """Endpoint to set the type of a room"""
    if key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    success = room_db_handler.set_roomtype(request.room_name, request.roomtype, edited_by_user_id=request.edited_by_user_id)
    
    if success:
        await utils.global_reset(request.room_name)
        return {"success": True, "message": f"Room '{request.room_name}' has been updated to type '{request.roomtype}'."}
    else:
        return {"error": f"Room '{request.room_name}' does not exist in the database."}


@app.post("/set_tags")
async def set_tags(request: SetTagsRequest, key: str = Query(...)):
    """Endpoint to set tags for a room"""
    if key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    roomdata = room_db_handler.get_roominfo(request.room_name)
    if not roomdata:
        return {"error": f"Room '{request.room_name}' does not exist in the database."}
    
    # Get existing tags and merge with new ones (unique)
    room_tags = roomdata.get('tags', [])
    for tag in request.tags:
        if tag not in room_tags:
            room_tags.append(tag)
    
    success = room_db_handler.set_roomtags(request.room_name, room_tags, edited_by_user_id=request.edited_by_user_id)
    
    if success:
        await utils.global_reset(request.room_name)
        return {"success": True, "message": f"Room '{request.room_name}' has been updated with tags: {', '.join(room_tags)}."}
    else:
        return {"error": f"Something went wrong while updating tags for room '{request.room_name}'."}


@app.post("/rename_room")
async def rename_room(key: str = Query(...), old_name: str = Query(...), new_name: str = Query(...), edited_by_user_id: int = Query(...)):
    """Endpoint to rename a room"""
    if key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    success = room_db_handler.rename_room(old_name, new_name, edited_by_user_id=edited_by_user_id)
    
    if success:
        await utils.global_reset(new_name)
        return {"success": True, "message": f"Room '{old_name}' has been renamed to '{new_name}'."}
    else:
        return {"error": f"Room '{old_name}' does not exist in the database."}


@app.delete("/deletedoc")
async def deletedoc(key: str = Query(...), room_name: str = Query(...)):
    """Endpoint to delete room documentation"""
    if key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    success = room_db_handler.delete_room(room_name)
    
    if success:
        return {"success": True, "message": f"Documentation for room '{room_name}' has been deleted."}
    else:
        return {"error": f"Room '{room_name}' does not exist in the database."}



###########################################
#            SCANNER ENDPOINTS            #
###########################################

IP_RATE_LIMIT = 60 # Max requests per minute per IP for unauthenticated scanner endpoints

scanner_request_logs = {}  # Dictionary to track request timestamps per IP

def _log_request(ip: str):
    """Helper function to log requests per IP for rate limiting"""
    current_time = datetime.now().timestamp()
    if ip not in scanner_request_logs:
        scanner_request_logs[ip] = []
    
    # Remove timestamps older than 60 seconds
    scanner_request_logs[ip] = [t for t in scanner_request_logs[ip] if current_time - t < 60]
    
    scanner_request_logs[ip].append(current_time)
    
    return len(scanner_request_logs[ip])

BASE_URL = "/scanner"

# UNAUTHENTICATED ENDPOINTS FOR THE SCANNER TOOL
@app.get(f"{BASE_URL}/get_roominfo")
async def get_room_info(room_name: str = Query(...), ip: str = Query(...)):
    """Endpoint to get room information for the scanner"""

    request_count = _log_request(ip)
    if request_count > IP_RATE_LIMIT:
        return {"error": "Rate limit exceeded. Please try again later."}
    
    room_profile = room_db_handler.get_roominfo(room_name)
    if not room_profile:
        return {"error": f"Room '{room_name}' does not exist in the database."}
    
    return {"success": True, "room_info": room_profile}

@app.get(f"{BASE_URL}/request_session")
async def request_scanner_session(ip: str = Query(...)):
    """Endpoint to request a new scanner session"""
    
    request_count = _log_request(ip)
    if request_count > IP_RATE_LIMIT:
        return {"error": "Rate limit exceeded. Please try again later."}
    
    session_id, password = scanner_db_handler.start_session(ip)
    return {"success": True, "session_id": session_id, "password": password}


