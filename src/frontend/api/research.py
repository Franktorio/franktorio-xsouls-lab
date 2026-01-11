# Franktorio's Research Division
# Author: Franktorio
# January 11th, 2026
# Research API endpoints

PRINT_PREFIX = "RESEARCH API"

from datetime import datetime
from fastapi import APIRouter

# Local imports
from config.vars import LOCAL_KEY
from src.datamanager.db_handlers import room_db_handler
from src.utils import utils
from .models import (
    GetResearcherRoleRequest,
    GetUserProfileRequest,
    GetAllResearchersRequest,
    DocumentRoomRequest,
    RedocumentRoomRequest,
    SetRoomTypeRequest,
    SetTagsRequest,
    RenameRoomRequest,
    DeleteDocRequest
)

router = APIRouter()

@router.get("/get_researcher_role")
async def get_researcher_role(request: GetResearcherRoleRequest):
    """Endpoint to get a user's research level"""
    print(f"[INFO] [{PRINT_PREFIX}] Received get_researcher_role request for user ID: {request.user_id}")
    if request.api_key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    research_level = await utils.get_researcher_role(request.user_id)
    return {"user_id": request.user_id, "research_level": research_level}

@router.get("/get_all_researchers")
async def get_all_researchers(request: GetAllResearchersRequest):
    """Endpoint to get all researchers and their levels"""
    print(f"[INFO] [{PRINT_PREFIX}] Received get_all_researchers request from API key: {request.api_key}")
    if request.api_key != LOCAL_KEY:
        return {"error": "Unauthorized"}
    
    researchers = await utils.get_all_researchers()
    return {"researchers": researchers}

@router.get("/get_user_profile")
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

@router.post("/document_room")
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


@router.post("/redocument_room")
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


@router.post("/set_roomtype")
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


@router.post("/set_tags")
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


@router.post("/rename_room")
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


@router.delete("/deletedoc")
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
