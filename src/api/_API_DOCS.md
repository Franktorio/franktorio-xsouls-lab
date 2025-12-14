# Research API Documentation

## Overview

This document describes the Research API implemented in `src/api/research_api.py`.

## Endpoints Summary

Research endpoints **All Authenticated**
> These endpoints are authenticated with the LOCAL_KEY on `config/vars.py`
- GET `/` - health/status endpoint (`ReadRootRequest`)
- GET `/get_researcher_role` - returns research level for a user (`GetResearcherRoleRequest` Pydantic Basemodel)
- GET `/get_user_profile` - returns user's profile info (`GetUserProfileRequest` Pydantic Basemodel)
- POST `/document_room` - create new room documentation (`DocumentRoomRequest` Pydantic Basemodel)
- POST `/redocument_room` - update existing room documentation (`RedocumentRoomRequest` Pydantic Basemodel)
- POST `/set_roomtype` - update a room's type (`SetRoomTypeRequest` Pydantic Basemodel)
- POST `/set_tags` - add/merge tags on a room (`SetTagsRequest` Pydantic Basemodel)
- POST `/rename_room` - rename a room (`RenameRoomRequest` Pydantic Basemodel)
- DELETE `/deletedoc` - delete a room's documentation (`DeleteDocRequest` Pydantic Basemodel)

Scanner endpoints (prefixed `/scanner`):
> The authenticated endpoints require a session ID and password provided in `/scanner/request_session`
- POST `/scanner/request_session` - request a scanner session (`SessionRequest`)
- POST `/scanner/end_session` - end a scanner session (`SessionEndRequest` Pydantic Basemodel) **Authenticated**
- POST `/scanner/get_roominfo` - get room info during a scanner session (`RoomInfoRequest` Pydantic Basemodel) **Authenticated**
- POST `/scanner/room_encountered` - log encountered room in a scanner session (`RoomEncounteredRequest` Pydantic Basemodel) **Authenticated**


Unauthorized requests return:

```json
{ "error": "Unauthorized" }
```


## Request Models

Below are the request models as defined in `research_api.py`.

### ReadRootRequest
- `api_key` (string): authentication key included in the request body for the GET `/` endpoint.

### GetResearcherRoleRequest
- `user_id` (int): Discord user id to query
- `api_key` (string): authentication key

### GetUserProfileRequest
- `user_id` (int): Discord user id to query
- `api_key` (string): authentication key

### DocumentRoomRequest
- `room_name` (string)
- `roomtype` (string)
- `picture_urls` (list[string]) - max 10 are used
- `description` (string)
- `doc_by_user_id` (int)
- `tags` (optional list[string])
- `timestamp` (optional float) - unix seconds
- `api_key` (string)

### RedocumentRoomRequest
- Same fields as `DocumentRoomRequest`, plus:
- `edited_by_user_id` (int)

### SetRoomTypeRequest
- `room_name` (string)
- `roomtype` (string)
- `edited_by_user_id` (int)
- `api_key` (string)

### SetTagsRequest
- `room_name` (string)
- `tags` (list[string])
- `edited_by_user_id` (int)
- `api_key` (string)

### RenameRoomRequest
- `old_name` (string)
- `new_name` (string)
- `edited_by_user_id` (int)
- `api_key` (string)

### DeleteDocRequest
- `room_name` (string)
- `api_key` (string)


## Scanner Models

### SessionRequest
- `scanner_version` (string)

### RoomInfoRequest
- `room_name` (string)
- `session_id` (string)
- `password` (string)

### RoomEncounteredRequest
- `session_id` (string)
- `password` (string)
- `room_name` (string)

### SessionEndRequest
- `session_id` (string)
- `password` (string)


## Responses and Error Cases

- Successful actions typically return `{"success": true, ...}` with a `message` or payload.
- If a requested room doesn't exist, endpoints respond with an `error` field describing the issue.
- Scanner endpoints may respond with `{"error": "Rate limit exceeded. Please try again later."}` when hit with >60 requests in a rolling 60s window per session.

## Example Code

# Research API Usage Examples (Python)

Replace `BASE_URL` and `LOCAL_KEY` with your own in `config/vars.py`.

### Document a room

```python
import requests

BASE_URL = "http://ExampleEndpoint.com/"
LOCAL_KEY = "ExampleKey"

payload = {
    "room_name": "Compact Belt Balancer",
    "roomtype": "balancer",
    "picture_urls": ["https://example.com/img1.png"],
    "description": "A compact 4-to-4 balancer design",
    "doc_by_user_id": 123456789,
    "tags": ["compact", "efficient"],
    "timestamp": None,
    "api_key": LOCAL_KEY
}

resp = requests.post(f"{BASE_URL}/document_room", json=payload)
print(resp.status_code, resp.json())
```

## Redocument a room

```python
payload = {
    "room_name": "Compact Belt Balancer",
    "roomtype": "advanced_balancer",
    "picture_urls": ["https://example.com/updatedimg1.png"],
    "description": "Updated design",
    "doc_by_user_id": 123456789,
    "edited_by_user_id": 987654321,
    "tags": ["updated"],
    "timestamp": None,
    "api_key": LOCAL_KEY
}

resp = requests.post(f"{BASE_URL}/redocument_room", json=payload)
print(resp.json())
```

### Get user profile

```python
payload = {"user_id": 123456789, "api_key": LOCAL_KEY}
resp = requests.request("GET", f"{BASE_URL}/get_user_profile", json=payload)
print(resp.json())
```

## Scanner Examples

```python
import requests

# Open a session
resp = requests.post(f"{BASE_URL}/scanner/request_session", json={"scanner_version": "1.0.0"})
data = resp.json()
session_id = data.get("session_id")
password = data.get("password")

# Report an encounter
resp = requests.post(f"{BASE_URL}/scanner/get_roominfo", json={
    "room_name": "Compact Belt Balancer",
    "session_id": session_id,
    "password": password
})
print(resp.json())

# Close the session
resp = requests.post(f"{BASE_URL}/scanner/end_session", json={"session_id": session_id, "password": password})
print(resp.json())
```
