# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# API handler for internal research operations

PRINT_PREFIX = "RESEARCH API"

# Standard library imports
from datetime import datetime
from typing import Optional
import asyncio

# Third-party imports
from fastapi import FastAPI, Query
from pydantic import BaseModel

# Local imports
from config.vars import LOCAL_KEY
from src.datamanager.db_handlers import room_db_handler, server_db_handler, scanner_db_handler
from src.utils import utils

app = FastAPI()


# Pydantic models for request bodies
class ReadRootRequest(BaseModel):
    api_key: str

class GetResearcherRoleRequest(BaseModel):
    user_id: int
    api_key: str

class GetUserProfileRequest(BaseModel):
    user_id: int
    api_key: str

class GetAllResearchersRequest(BaseModel):
    api_key: str

class DocumentRoomRequest(BaseModel):
    room_name: str
    roomtype: str
    picture_urls: list[str]
    description: str
    doc_by_user_id: int
    tags: Optional[list[str]] = None
    timestamp: Optional[float] = None
    api_key: str

class RedocumentRoomRequest(BaseModel):
    room_name: str
    roomtype: str
    picture_urls: list[str]
    description: str
    doc_by_user_id: int
    edited_by_user_id: int
    tags: Optional[list[str]] = None
    timestamp: Optional[float] = None
    api_key: str

class SetRoomTypeRequest(BaseModel):
    room_name: str
    roomtype: str
    edited_by_user_id: int
    api_key: str

class SetTagsRequest(BaseModel):
    room_name: str
    tags: list[str]
    edited_by_user_id: int
    api_key: str

class RenameRoomRequest(BaseModel):
    old_name: str
    new_name: str
    edited_by_user_id: int
    api_key: str

class DeleteDocRequest(BaseModel):
    room_name: str
    api_key: str

@app.get("/")
async def read_root(request: ReadRootRequest):
    """Root endpoint to verify API is running."""
    print(f"[INFO] [{PRINT_PREFIX}] Received root API request.")
    if request.api_key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    room_amnt = len(room_db_handler.get_all_room_names())
    servers_amnt = len(server_db_handler.get_all_server_profiles())
    current_time = datetime.now().timestamp()

    return {"message": f"Research API is running. {room_amnt} rooms documented. {servers_amnt} servers using the bot. Current timestamp: {current_time} UTC."}


@app.get("/get_researcher_role")
async def get_researcher_role(request: GetResearcherRoleRequest):
    """Endpoint to get a user's research level"""
    print(f"[INFO] [{PRINT_PREFIX}] Received get_researcher_role request for user ID: {request.user_id}")
    if request.api_key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    research_level = await utils.get_researcher_role(request.user_id)
    return {"user_id": request.user_id, "research_level": research_level}

@app.get("/get_all_researchers")
async def get_all_researchers(request: GetAllResearchersRequest):
    """Endpoint to get all researchers and their levels"""
    print(f"[INFO] [{PRINT_PREFIX}] Received get_all_researchers request from API key: {request.api_key}")
    if request.api_key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    researchers = await utils.get_all_researchers()
    return {"researchers": researchers}

@app.get("/get_user_profile")
async def get_user_profile(request: GetUserProfileRequest):
    """Endpoint to get a user's profile picture URL, username, and display name"""
    print(f"[INFO] [{PRINT_PREFIX}] Received get_user_profile request for user ID: {request.user_id}")
    if request.api_key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    user_data = await utils.get_user_profile(request.user_id)
    return {
        "user_id": request.user_id,
        "profile_picture_url": user_data["profile_picture_url"],
        "username": user_data["username"],
        "display_name": user_data["display_name"]
    }

@app.post("/document_room")
async def document_room(request: DocumentRoomRequest):
    """Endpoint to document a room"""
    if request.api_key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    print(f"[INFO] [{PRINT_PREFIX}] Received document_room request for '{request.room_name}'")
    
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
    
    print(f"[INFO] [{PRINT_PREFIX}] Successfully documented '{request.room_name}'")
    return {"success": True, "message": f"Room '{request.room_name}' has been documented."}


@app.post("/redocument_room")
async def redocument_room(request: RedocumentRoomRequest):
    """Endpoint to redocument an existing room"""
    if request.api_key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    print(f"[INFO] [{PRINT_PREFIX}] Received redocument_room request for '{request.room_name}'")
    
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
    
    print(f"[INFO] [{PRINT_PREFIX}] Successfully redocumented '{request.room_name}'")
    return {"success": True, "message": f"Room '{request.room_name}' has been redocumented."}


@app.post("/set_roomtype")
async def set_roomtype(request: SetRoomTypeRequest):
    """Endpoint to set the type of a room"""
    if request.api_key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    print(f"[INFO] [{PRINT_PREFIX}] Received set_roomtype request for '{request.room_name}'")
    
    success = room_db_handler.set_roomtype(request.room_name, request.roomtype, edited_by_user_id=request.edited_by_user_id)
    
    if success:
        await utils.global_reset(request.room_name)
        print(f"[INFO] [{PRINT_PREFIX}] Updated roomtype for '{request.room_name}' to '{request.roomtype}'")
        return {"success": True, "message": f"Room '{request.room_name}' has been updated to type '{request.roomtype}'."}
    else:
        return {"error": f"Room '{request.room_name}' does not exist in the database."}


@app.post("/set_tags")
async def set_tags(request: SetTagsRequest):
    """Endpoint to set tags for a room"""
    if request.api_key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    print(f"[INFO] [{PRINT_PREFIX}] Received set_tags request for '{request.room_name}'")
    
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
        print(f"[INFO] [{PRINT_PREFIX}] Updated tags for '{request.room_name}': {', '.join(room_tags)}")
        return {"success": True, "message": f"Room '{request.room_name}' has been updated with tags: {', '.join(room_tags)}."}
    else:
        return {"error": f"Something went wrong while updating tags for room '{request.room_name}'."}


@app.post("/rename_room")
async def rename_room(request: RenameRoomRequest):
    """Endpoint to rename a room"""
    if request.api_key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    print(f"[INFO] [{PRINT_PREFIX}] Received rename_room request: '{request.old_name}' -> '{request.new_name}'")
    
    success = room_db_handler.rename_room(request.old_name, request.new_name, edited_by_user_id=request.edited_by_user_id)
    
    if success:
        await utils.global_reset(request.new_name)
        print(f"[INFO] [{PRINT_PREFIX}] Successfully renamed room: '{request.old_name}' -> '{request.new_name}'")
        return {"success": True, "message": f"Room '{request.old_name}' has been renamed to '{request.new_name}'."}
    else:
        return {"error": f"Room '{request.old_name}' does not exist in the database."}


@app.delete("/deletedoc")
async def deletedoc(request: DeleteDocRequest):
    """Endpoint to delete room documentation"""
    if request.api_key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    print(f"[INFO] [{PRINT_PREFIX}] Received deletedoc request for '{request.room_name}'")
    
    success = room_db_handler.delete_room(request.room_name)
    
    if success:
        print(f"[INFO] [{PRINT_PREFIX}] Successfully deleted documentation for room '{request.room_name}'")
        return {"success": True, "message": f"Documentation for room '{request.room_name}' has been deleted."}
    else:
        return {"error": f"Room '{request.room_name}' does not exist in the database."}



###########################################
#            SCANNER ENDPOINTS            #
###########################################

class RoomInfoRequest(BaseModel):
    room_name: str
    session_id: str
    password: str

class RoomEncounteredRequest(BaseModel):
    session_id: str
    password: str
    room_name: str

class SessionRequest(BaseModel):
    scanner_version: str

class SessionEndRequest(BaseModel):
    session_id: str
    password: str

log_request_lock = asyncio.Lock()
scanner_request_logs = {}  # Dictionary to track request timestamps per session

RATE_LIMIT = 60 # Max requests per minute per IP for unauthenticated scanner endpoints

async def _log_request(session_id: str):
    """Helper function to log requests per session for rate limiting"""
    current_time = datetime.now().timestamp()
    if session_id not in scanner_request_logs:
        scanner_request_logs[session_id] = []
    
    # Remove timestamps older than 60 seconds
    async with log_request_lock:
        scanner_request_logs[session_id] = [t for t in scanner_request_logs[session_id] if current_time - t < 60]
        
        scanner_request_logs[session_id].append(current_time)
    
    return len(scanner_request_logs[session_id])

def _validate_session(session_id: str, password: str) -> bool:
    """Helper function to validate a scanner session"""
    return scanner_db_handler.validate_session(session_id, password)

BASE_URL = "/scanner"

@app.post(f"{BASE_URL}/request_session")
async def request_scanner_session(request: SessionRequest):
    """Endpoint to request a new scanner session"""
    
    print(f"[INFO] [{PRINT_PREFIX}] Scanner session requested (version: {request.scanner_version})")
    
    session_id, password = scanner_db_handler.start_session(scanner_version=request.scanner_version)
    return {"success": True, "session_id": session_id, "password": password}

@app.post(f"{BASE_URL}/end_session")
async def end_scanner_session(request: SessionEndRequest):
    """Endpoint to end a scanner session"""
    
    request_count = await _log_request(request.session_id)
    if request_count > RATE_LIMIT:
        print(f"[WARNING] [{PRINT_PREFIX}] Rate limit exceeded for session {request.session_id}")
        return {"error": "Rate limit exceeded. Please try again later."}
    
    print(f"[INFO] [{PRINT_PREFIX}] Scanner session end requested: {request.session_id}")
    
    valid_session = _validate_session(request.session_id, request.password)
    if not valid_session:
        return {"error": "Invalid session ID or password."}
    
    success = scanner_db_handler.end_session(session_id=request.session_id, session_password=request.password)
    if success:
        print(f"[INFO] [{PRINT_PREFIX}] Scanner session ended: {request.session_id}")
        return {"success": True, "message": f"Session '{request.session_id}' has been ended."}
    else:
        return {"error": "Invalid session ID or password, or session already ended."}

@app.post(f"{BASE_URL}/get_roominfo")
async def get_room_info(request: RoomInfoRequest):
    """Endpoint to get room information for the scanner"""

    request_count = await _log_request(request.session_id)
    if request_count > RATE_LIMIT:
        print(f"[WARNING] [{PRINT_PREFIX}] Rate limit exceeded for session {request.session_id}")
        return {"error": "Rate limit exceeded. Please try again later."}
    print(f"[INFO] [{PRINT_PREFIX}] Scanner requesting room info for '{request.room_name}'")

    valid_session = _validate_session(request.session_id, request.password)
    if not valid_session:
        return {"error": "Invalid session ID or password."}
    
    room_profile = room_db_handler.get_roominfo(request.room_name)
    if not room_profile:
        return {"error": f"Room '{request.room_name}' does not exist in the database."}
    
    return {"success": True, "room_info": room_profile}
    
@app.post(f"{BASE_URL}/room_encountered")
async def room_encountered(request: RoomEncounteredRequest):
    """Endpoint to log that a room has been encountered during a scanning session"""
    
    request_count = await _log_request(request.session_id)
    if request_count > RATE_LIMIT:
        print(f"[WARNING] [{PRINT_PREFIX}] Rate limit exceeded for session {request.session_id}")
        return {"error": "Rate limit exceeded. Please try again later."}
    
    print(f"[INFO] [{PRINT_PREFIX}] Room encountered in session {request.session_id}: '{request.room_name}'")
    
    valid_session = _validate_session(request.session_id, request.password)
    if not valid_session:
        return {"error": "Invalid session ID or password."}
    
    success = scanner_db_handler.log_encountered_room(session_id=request.session_id, session_password=request.password, room_name=request.room_name)
    if success:
        print(f"[INFO] [{PRINT_PREFIX}] Logged room '{request.room_name}' for session {request.session_id}")
        return {"success": True, "message": f"Room '{request.room_name}' has been logged for session '{request.session_id}'."}
    else:
        return {"error": "Invalid session ID or password, or session has ended."}