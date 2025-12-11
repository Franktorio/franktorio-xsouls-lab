# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Background task to synchronize databases across servers

PRINT_PREFIX = "DATABASE SYNC"

# Third-party imports
from discord.ext import tasks

# Local imports
from config.vars import EXTERNAL_DATA_SOURCE
from src import datamanager, shared
from src.api import external_api
from src.utils import embeds, utils


@tasks.loop(hours=1)
async def sync_databases():
    """Background task to synchronize databases across servers."""
    if not EXTERNAL_DATA_SOURCE:
        print(f"[INFO] [{PRINT_PREFIX}] Skipping database synchronization - external data source is disabled")
        return
    
    print(f"[INFO] [{PRINT_PREFIX}] Starting database synchronization across servers")
    print(f"[INFO] [{PRINT_PREFIX}] Fetching external database export...")
    # Export external database
    ext_export = await external_api.export_database_api()
    if not ext_export.get("success"):
        print(f"[ERROR] [{PRINT_PREFIX}] Failed to get external database: {ext_export.get('error')}")
        return
    
    ext_database = ext_export.get("rooms", {})
    db_json = datamanager.room_db_handler.jsonify_room_db()["room_db"]

    print(f"[DEBUG] [{PRINT_PREFIX}] Comparing {len(ext_database)} external rooms with {len(db_json)} local rooms")
    # Compare each last updated timestamp and update external/internal as needed
    missing_locally = []
    missing_externally = []
    newer_locally = []
    newer_externally = []

    for room_name, ext_room_data in ext_database.items():
        local_room_data = datamanager.room_db_handler.get_roominfo(room_name)

        if not local_room_data:
            missing_locally.append((room_name, ext_room_data))
            continue

        ext_last_updated = ext_room_data.get("last_edited", 0)
        local_last_updated = local_room_data.get("last_updated", 0)

        if local_last_updated > ext_last_updated:
            newer_locally.append((room_name, local_room_data))
        elif ext_last_updated > local_last_updated:
            newer_externally.append((room_name, ext_room_data))

    for room_name in db_json.keys():
        if room_name not in ext_database:
            local_room_data = datamanager.room_db_handler.get_roominfo(room_name)
            if local_room_data:
                missing_externally.append((room_name, local_room_data))

    print(f"[INFO] [{PRINT_PREFIX}] Rooms missing locally: {len(missing_locally)}")
    print(f"[INFO] [{PRINT_PREFIX}] Rooms missing externally: {len(missing_externally)}")
    print(f"[INFO] [{PRINT_PREFIX}] Rooms newer locally: {len(newer_locally)}")
    print(f"[INFO] [{PRINT_PREFIX}] Rooms newer externally: {len(newer_externally)}")

    # Process missing externally - upload to external API
    for room_name, local_data in missing_externally:
        print(f"[INFO] [{PRINT_PREFIX}] Uploading missing room to external API: {room_name}")
        
        # Validate image URLs - filter out file paths
        picture_urls = local_data.get("picture_urls", [])
        valid_urls = [url for url in picture_urls if url.startswith(("http://", "https://"))]
        
        if len(valid_urls) < len(picture_urls):
            print(f"[WARNING] [{PRINT_PREFIX}]    Filtered out {len(picture_urls) - len(valid_urls)} invalid URLs (file paths)")
        
        if len(valid_urls) < 4:
            print(f"[WARNING] [{PRINT_PREFIX}]   Skipped {room_name}: Only {len(valid_urls)} valid HTTP URLs (need at least 4)")
            continue
        
        result = await external_api.export_room_to_api(
            room_name=room_name,
            roomtype=local_data.get("roomtype", "Unclassified"),
            picture_urls=valid_urls,
            description=local_data.get("description", ""),
            doc_by_user_id=local_data.get("doc_by_user_id", 0),
            tags=local_data.get("tags", []),
            last_edited_by=local_data.get("edited_by_user_id"),
            timestamp=local_data.get("last_updated", 0)
        )
        if not result.get("success"):
            print(f"[ERROR] [{PRINT_PREFIX}]   Failed to upload {room_name}: {result.get('error')}")
        else:
            print(f"[INFO] [{PRINT_PREFIX}]   Uploaded {room_name}")

    # Process missing locally, download from external API
    for room_name, ext_data in missing_locally:
        print(f"[INFO] [{PRINT_PREFIX}] Downloading missing room from external API: {room_name}")
        
        # Validate image URLs from external API: filter out file paths
        picture_urls = ext_data.get("images", [])
        valid_urls = [url for url in picture_urls if url.startswith(("http://", "https://"))]
        
        if len(valid_urls) < len(picture_urls):
            print(f"[WARNING] [{PRINT_PREFIX}]    External API sent {len(picture_urls) - len(valid_urls)} invalid URLs (file paths) - filtered out")
        
        # Get existing local data to preserve edit history
        local_room = datamanager.room_db_handler.get_roominfo(room_name)
        existing_edits = local_room.get('edits', []) if local_room else None
        
        # Use replace_doc to sync without creating spurious edit history
        datamanager.room_db_handler.replace_doc(
            room_name=room_name,
            roomtype=ext_data.get("roomtype", "Unclassified"),
            picture_urls=valid_urls,
            description=ext_data.get("description", ""),
            doc_by_user_id=ext_data.get("documented_by", 0),
            tags=ext_data.get("tags", []),
            timestamp=ext_data.get("last_edited", 0),
            edited_by_user_id=ext_data.get("last_edited_by"),
            edits=existing_edits  # Preserve existing edit history
        )
        print(f"[INFO] [{PRINT_PREFIX}]   Downloaded {room_name}")

    # Process newer locally: upload to external API
    for room_name, local_data in newer_locally:
        print(f"[INFO] [{PRINT_PREFIX}] Updating external API (local is newer): {room_name}")
        
        # Validate image URLs: filter out file paths
        picture_urls = local_data.get("picture_urls", [])
        valid_urls = [url for url in picture_urls if url.startswith(("http://", "https://"))]
        
        if len(valid_urls) < len(picture_urls):
            print(f"[WARNING] [{PRINT_PREFIX}]    Filtered out {len(picture_urls) - len(valid_urls)} invalid URLs (file paths)")
        
        if len(valid_urls) < 4:
            print(f"[WARNING] [{PRINT_PREFIX}]   Skipped {room_name}: Only {len(valid_urls)} valid HTTP URLs (need at least 4)")
            print(f"[WARNING] [{PRINT_PREFIX}]    Keeping external version to avoid data loss")
            
            # Download from external to fix discrepancy
            ext_room_data = ext_database.get(room_name)
            if ext_room_data:
                datamanager.room_db_handler.replace_doc(
                    room_name=room_name,
                    roomtype=ext_room_data.get("roomtype", "Unclassified"),
                    picture_urls=[url for url in ext_room_data.get("images", []) if url.startswith(("http://", "https://"))],
                    description=ext_room_data.get("description", ""),
                    doc_by_user_id=ext_room_data.get("documented_by", 0),
                    tags=ext_room_data.get("tags", []),
                    timestamp=ext_room_data.get("last_edited", 0),
                    edited_by_user_id=ext_room_data.get("last_edited_by")
                )
                await utils.global_reset(room_name)
                print(f"[INFO] [{PRINT_PREFIX}]   Reverted local {room_name} to external version")
            continue
        
        upload_result = await external_api.export_room_to_api(
            room_name=room_name,
            roomtype=local_data.get("roomtype", "Unclassified"),
            picture_urls=valid_urls,
            description=local_data.get("description", ""),
            doc_by_user_id=local_data.get("doc_by_user_id", 0),
            tags=local_data.get("tags", []),
            last_edited_by=local_data.get("edited_by_user_id"),
            timestamp=local_data.get("last_updated", 0)
        )
        
        if not upload_result.get("success"):
            # Check if this is a skippable error (like not enough images)
            print(f"[ERROR] [{PRINT_PREFIX}]   Failed to upload {room_name}: {upload_result.get('error')}")
            print(f"[ERROR] [{PRINT_PREFIX}]    Keeping external version to avoid data loss")
            continue
        
        print(f"[INFO] [{PRINT_PREFIX}]   Updated {room_name} in external database")

    # Process newer externally: update local database
    for room_name, ext_data in newer_externally:
        print(f"[INFO] [{PRINT_PREFIX}] Updating local database (external is newer): {room_name}")
        
        # Validate image URLs from external API: filter out file paths
        picture_urls = ext_data.get("images", [])
        valid_urls = [url for url in picture_urls if url.startswith(("http://", "https://"))]
        
        if len(valid_urls) < len(picture_urls):
            print(f"[WARNING] [{PRINT_PREFIX}]    External API sent {len(picture_urls) - len(valid_urls)} invalid URLs (file paths) - filtered out")
        
        datamanager.room_db_handler.document_room(
            room_name=room_name,
            roomtype=ext_data.get("roomtype", "Unclassified"),
            picture_urls=valid_urls,
            description=ext_data.get("description", ""),
            doc_by_user_id=ext_data.get("documented_by", 0),
            tags=ext_data.get("tags", []),
            timestamp=ext_data.get("last_edited", 0),
            edited_by_user_id=ext_data.get("last_edited_by")
        )

        await utils.global_reset(room_name)
        print(f"[INFO] [{PRINT_PREFIX}]   Updated {room_name} in local database")
        
    print(f"[INFO] [{PRINT_PREFIX}] Database synchronization complete!")
    print(f"[INFO] [{PRINT_PREFIX}]    Uploaded: {len(missing_externally)} rooms")
    print(f"[INFO] [{PRINT_PREFIX}]    Downloaded: {len(missing_locally)} rooms")
    print(f"[INFO] [{PRINT_PREFIX}]    Updated externally: {len(newer_locally)} rooms")
    print(f"[INFO] [{PRINT_PREFIX}]    Updated locally: {len(newer_externally)} rooms")
