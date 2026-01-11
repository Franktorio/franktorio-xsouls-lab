# Franktorio's Research Division
# Author: Franktorio
# January 11th, 2026
# Scanner API endpoints

PRINT_PREFIX = "SCANNER API"

import asyncio
from datetime import datetime
from fastapi import APIRouter

# Local imports
from config.vars import LATEST_SCANNER_VERSION
from src.datamanager.db_handlers import room_db_handler, scanner_db_handler
from .models import (
    RoomInfoRequest,
    RoomEncounteredRequest,
    SessionRequest,
    SessionEndRequest
)

router = APIRouter(prefix="/scanner")

# Rate limiting
log_request_lock = asyncio.Lock()
scanner_request_logs = {}  # Dictionary to track request timestamps per session
RATE_LIMIT = 500  # Max requests per minute per IP for scanner endpoints

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

@router.post("/check_version")
async def check_scanner_version(request: SessionRequest):
    """Endpoint to check the scanner version"""
    print(f"[INFO] [{PRINT_PREFIX}] Scanner version check: {request.scanner_version}")
    return {"success": True, "latest_version": LATEST_SCANNER_VERSION}

@router.post("/request_session")
async def request_scanner_session(request: SessionRequest):
    """Endpoint to request a new scanner session"""
    
    print(f"[INFO] [{PRINT_PREFIX}] Scanner session requested (version: {request.scanner_version})")
    
    session_id, password = scanner_db_handler.start_session(scanner_version=request.scanner_version)
    return {"success": True, "session_id": session_id, "password": password}

@router.post("/end_session")
async def end_scanner_session(request: SessionEndRequest):
    """Endpoint to end a scanner session"""
    
    request_count = await _log_request(request.session_id)
    if request_count > RATE_LIMIT:
        print(f"[WARNING] [{PRINT_PREFIX}] Rate limit exceeded for session {request.session_id}")
        return {"error": "Rate limit exceeded. Please try again later."}
    
    print(f"[DEBUG] [{PRINT_PREFIX}] Scanner session end requested: {request.session_id}")
    
    valid_session = _validate_session(request.session_id, request.password)
    if not valid_session:
        return {"error": "Invalid session ID or password."}
    
    success = scanner_db_handler.end_session(session_id=request.session_id, session_password=request.password)
    if success:
        print(f"[INFO] [{PRINT_PREFIX}] Scanner session ended: {request.session_id}")
        return {"success": True, "message": f"Session '{request.session_id}' has been ended."}
    else:
        return {"error": "Invalid session ID or password, or session already ended."}

@router.post("/get_roominfo")
async def get_room_info(request: RoomInfoRequest):
    """Endpoint to get room information for the scanner"""

    request_count = await _log_request(request.session_id)
    if request_count > RATE_LIMIT:
        print(f"[WARNING] [{PRINT_PREFIX}] Rate limit exceeded for session {request.session_id}")
        return {"error": "Rate limit exceeded. Please try again later."}
    print(f"[DEBUG] [{PRINT_PREFIX}] Scanner requesting room info for '{request.room_name}'")

    valid_session = _validate_session(request.session_id, request.password)
    if not valid_session:
        return {"error": "Invalid session ID or password."}
    
    room_profile = room_db_handler.get_roominfo(request.room_name)
    if not room_profile:
        return {"error": f"Room '{request.room_name}' does not exist in the database."}
    
    return {"success": True, "room_info": room_profile}
    
@router.post("/room_encountered")
async def room_encountered(request: RoomEncounteredRequest):
    """Endpoint to log that a room has been encountered during a scanning session"""
    
    request_count = await _log_request(request.session_id)
    if request_count > RATE_LIMIT:
        print(f"[WARNING] [{PRINT_PREFIX}] Rate limit exceeded for session {request.session_id}")
        return {"error": "Rate limit exceeded. Please try again later."}
    
    print(f"[DEBUG] [{PRINT_PREFIX}] Room encountered in session {request.session_id}: '{request.room_name}'")
    
    valid_session = _validate_session(request.session_id, request.password)
    if not valid_session:
        return {"error": "Invalid session ID or password."}
    
    success = scanner_db_handler.log_encountered_room(session_id=request.session_id, session_password=request.password, room_name=request.room_name)
    if success:
        print(f"[INFO] [{PRINT_PREFIX}] Session '{request.session_id}' logged encountered room '{request.room_name}'")
        return {"success": True, "message": f"Room '{request.room_name}' has been logged for session '{request.session_id}'."}
    else:
        return {"error": "Invalid session ID or password, or session has ended."}
