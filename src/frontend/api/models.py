# Franktorio's Research Division
# Author: Franktorio
# January 11th, 2026
# Pydantic models for API requests

from typing import Optional
from pydantic import BaseModel

# Research API Models

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

# Scanner API Models

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
