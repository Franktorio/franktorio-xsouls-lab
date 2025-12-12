# Command Documentation

> Commands found at `src\commands`

## Permission Levels

- **Level 0 (Viewer)**: No special permissions. Can do bug reports
- **Level 1 (Trial Researcher)**: Can add/remove tags and document rooms
- **Level 2 (Novice Researcher)**: Can set descriptions and room types
- **Level 3 (Experienced Researcher)**: Can rename and delete rooms
- **Level 4 (Head Researcher)**: Can manage roles, sync databases, and handle bug reports
- **Level 5 (Owner/Developer)**: Full access to all developer commands

These role permissions are only valid when they have the roles on the home-server of the bot

## Developer Commands (`/dev`)

Developer-only commands that are only executable by members with permission level 5 (Owner).

### `/dev restart`
- **Arguments**: None
- **Description**: Shuts down the bot. If running on a service with auto-restart, it will automatically restart.

### `/dev room_reset`
- **Arguments**
  - `room_name` (string): Name of the room to globally reset across servers.
- **Description**: Delete the room documentation across all servers.


### `/dev global_reset_documented`
- **Arguments**: None
- **Description**: Bulk deletes every message in the documented channel across all servers, then clears the message IDs from each server's profile. The automated task will rebuild all documented channels.

### `/dev cache_all_rooms`
- **Arguments**: None
- **Description**: Downloads and caches all room images from the database to R2 storage. Provides progress updates and a final summary of cached/failed images.

### `/dev get_room_json`
- **Arguments**: None
- **Description**: Exports the entire room database as a JSON file. Sent as a file attachment (ephemeral).

### `/dev get_room_db`
- **Arguments**: None
- **Description**: Exports the raw SQLite database file. Sent as a file attachment (ephemeral).

### `/dev room_data`
- **Arguments**: 
  - `room_name` (string): Name of the room to export
- **Description**: Exports data for a specific room as a JSON file. Sent as a file attachment (ephemeral).


## Setup Commands (`/setup`)

Commands for server administrators to configure the bot. Requires Administrator permission or Owner status.

### `/setup init`
- **Arguments**: None
- **Description**: Initializes the bot in the server. Creates a category "Franktorio & xSoul's Research Division" with two channels: `documented-rooms` and `research-leaderboard`. If already set up, asks for confirmation before rebuilding.

### `/setup leaderboard`
- **Arguments**: None
- **Description**: Deletes the old leaderboard channel and creates a new one. Resets and rebuilds the research leaderboard from scratch.

### `/setup documented`
- **Arguments**: None
- **Description**: Deletes the old documented channel and creates a new one. Clears all cached message IDs and triggers a rebuild of all room documentation (may take hours depending on room count).


## Room Commands (`/room`)

Commands for viewing room information and managing bug reports. Available to all users.

### `/room info`
- **Arguments**: 
  - `room_name` (string): Name of the room
- **Description**: Displays detailed information about a specific room, including description, type, tags, images, and documentation history.

### `/room search`
- **Arguments**: 
  - `name` (string, optional): Search query for room names
  - `tag` (Tags enum, optional): Tag to filter rooms by
  - `roomtype` (RoomType enum, optional): Type of room to filter by
- **Description**: Searches for rooms by name, tag, and/or room type. At least one parameter must be provided. Returns all rooms matching ALL provided criteria.

### `/room history`
- **Arguments**: 
  - `room_name` (string): Name of the room
- **Description**: Displays the complete edit history of a room, showing who documented it, who edited it, and what changes were made.

### `/room bug_report`
- **Arguments**: 
  - `room_name` (string): Name of the room
  - `issue_description` (string): Description of the issue (30-1000 characters)
- **Description**: Submits a bug report for a specific room. Returns a unique report ID for tracking.

### `/room view_room_reports`
- **Arguments**: 
  - `room_name` (string): Name of the room
- **Description**: Displays all bug reports for a specific room.

### `/room view_all_reports`
- **Arguments**: 
  - `include_resolved` (boolean, optional, default: True): Include resolved reports
- **Description**: Displays all bug reports across all rooms.

### `/room view_report`
- **Arguments**: 
  - `report_id` (integer): ID of the bug report
- **Description**: Displays detailed information about a specific bug report by its ID.


## Research Commands (`/research`)

Commands for documenting and managing room data. Requires appropriate researcher permissions.

### `/research document`
- **Permission Required**: Trial Researcher (Level 1)
- **Arguments**: 
  - `roomname` (string): Name of the room
  - `roomtype` (RoomType enum): Type of the room
  - `description` (string): Description of the room
  - `image1-4` (attachments): Required images (minimum 4)
  - `image5-10` (attachments, optional): Additional images (up to 10 total)
  - `ss` (boolean, optional): Is this a SS room?
  - `pss` (boolean, optional): Is this a PSS room?
  - `brighten` (boolean, optional): Apply gamma correction to brighten images
- **Description**: Adds a new room to the database with images and metadata. Images are uploaded to R2 storage. If external data source is enabled, also syncs to external API.

### `/research redocument`
- **Permission Required**: Novice Researcher (Level 2)
- **Arguments**: Same as `/research document` plus:
  - `roomname` must exist in database
- **Description**: Updates an existing room's documentation with new images and data. Completely replaces all previous images and metadata.

### `/research set_description`
- **Permission Required**: Novice Researcher (Level 2)
- **Arguments**: 
  - `roomname` (string): Name of the room
  - `description` (string): New description
- **Description**: Updates only the description of an existing room.

### `/research set_roomtype`
- **Permission Required**: Novice Researcher (Level 2)
- **Arguments**: 
  - `roomname` (string): Name of the room
  - `roomtype` (RoomType enum): New room type
- **Description**: Updates only the room type of an existing room.

### `/research set_tags`
- **Permission Required**: Trial Researcher (Level 1)
- **Arguments**: 
  - `roomname` (string): Name of the room
  - `tag1-10` (Tags enum): Tags to set (at least one required)
- **Description**: Replaces all existing tags with the provided tags. Removes any tags not specified.

### `/research add_tags`
- **Permission Required**: Trial Researcher (Level 1)
- **Arguments**: 
  - `roomname` (string): Name of the room
  - `tag1-3` (Tags enum): Tags to add (at least one required)
- **Description**: Adds tags to a room without removing existing tags. Duplicates are ignored.

### `/research remove_tags`
- **Permission Required**: Trial Researcher (Level 1)
- **Arguments**: 
  - `roomname` (string): Name of the room
  - `tag1-3` (Tags enum): Tags to remove (at least one required)
- **Description**: Removes specified tags from a room. Other tags remain unchanged.

### `/research rename`
- **Permission Required**: Experienced Researcher (Level 3)
- **Arguments**: 
  - `roomname` (string): Current name of the room
  - `newname` (string): New name for the room
- **Description**: Renames a room in the database. Updates all references and triggers global reset.

### `/research deletedoc`
- **Permission Required**: Experienced Researcher (Level 3)
- **Arguments**: 
  - `roomname` (string): Name of the room to delete
- **Description**: Permanently deletes a room from the database, including all images from R2 storage. If external data source is enabled, also deletes from external API.


## Management Commands (`/management`)

Commands for managing the bot and users. Requires Head Researcher (Level 4) or higher.

### `/management sync`
- **Permission Required**: Head Researcher (Level 4)
- **Arguments**: None
- **Description**: Manually triggers database synchronization across servers. Only runs if `EXTERNAL_DATA_SOURCE` is enabled. Restarts the sync task immediately.

### `/management role`
- **Permission Required**: Head Researcher (Level 4)
- **Arguments**: 
  - `user` (User): The user to set the permission level for
  - `role` (Literal): Permission role to assign (Viewer, Trial Researcher, Novice Researcher, Experienced Researcher, Head Researcher)
- **Description**: Sets a user's permission level by assigning/removing Discord roles in the home guild. If external data source is enabled, also syncs to external API.

### `/management delete_report`
- **Permission Required**: Head Researcher (Level 4)
- **Arguments**: 
  - `report_id` (integer): ID of the bug report to delete
- **Description**: Soft deletes a bug report by marking it as deleted in the database.

### `/management resolve_report`
- **Permission Required**: Head Researcher (Level 4)
- **Arguments**: 
  - `report_id` (integer): ID of the bug report to resolve
- **Description**: Marks a bug report as resolved in the database.

