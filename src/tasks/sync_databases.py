# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Background task to synchronize databases across servers

# Third-party imports
import asyncio
import discord
from discord.ext import tasks

# Local imports
import shared
import src.api.external_api as ext_api
from src import datamanager
from src.utils import embeds
from src.utils import _helpers


@tasks.loop(hours=1)
async def sync_databases():
    """Background task to synchronize databases across servers."""
    print("🔄 Starting database synchronization across servers.")

    # Export external database
    ext_export = await ext_api.export_database_api()
    if not ext_export.get("success"):
        print(f"❌ Failed to export external database: {ext_export.get('error')}")
        return
    
    ext_database = ext_export.get("rooms", {})
    db_json = datamanager.room_db_handler.jsonify_room_db()

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

    print(f"🗂️  Rooms missing locally: {len(missing_locally)}")
    print(f"🗂️  Rooms missing externally: {len(missing_externally)}")
    print(f"⬆️  Rooms newer locally: {len(newer_locally)}")
    print(f"⬇️  Rooms newer externally: {len(newer_externally)}")

    # Process missing externally - upload to external API
    for room_name, local_data in missing_externally:
        print(f"⬆️ Uploading missing room to external API: {room_name}")
        
        # Validate image URLs - filter out file paths
        picture_urls = local_data.get("picture_urls", [])
        valid_urls = [url for url in picture_urls if url.startswith(("http://", "https://"))]
        
        if len(valid_urls) < len(picture_urls):
            print(f"  ⚠️  Filtered out {len(picture_urls) - len(valid_urls)} invalid URLs (file paths)")
        
        if len(valid_urls) < 4:
            print(f"  ⏭️  Skipped {room_name}: Only {len(valid_urls)} valid HTTP URLs (need at least 4)")
            continue
        
        result = await ext_api.export_room_to_api(
            room_name=room_name,
            roomtype=local_data.get("roomtype", "Unclassified"),
            picture_urls=valid_urls,
            description=local_data.get("description", ""),
            doc_by_user_id=local_data.get("doc_by_user_id", 0),
            tags=local_data.get("tags", []),
            last_edited_by=local_data.get("edited_by_user_id")
        )
        if not result.get("success"):
            print(f"  ❌ Failed to upload {room_name}: {result.get('error')}")
        else:
            print(f"  ✅ Uploaded {room_name}")

    # Process missing locally - download from external API
    for room_name, ext_data in missing_locally:
        print(f"⬇️ Downloading missing room from external API: {room_name}")
        
        # Validate image URLs from external API - filter out file paths
        picture_urls = ext_data.get("images", [])
        valid_urls = [url for url in picture_urls if url.startswith(("http://", "https://"))]
        
        if len(valid_urls) < len(picture_urls):
            print(f"  ⚠️  External API sent {len(picture_urls) - len(valid_urls)} invalid URLs (file paths) - filtered out")
        
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
        print(f"  ✅ Downloaded {room_name}")

    # Process newer locally - delete external and re-upload
    for room_name, local_data in newer_locally:
        print(f"🔄 Updating external API (local is newer): {room_name}")
        
        # Validate image URLs - filter out file paths
        picture_urls = local_data.get("picture_urls", [])
        valid_urls = [url for url in picture_urls if url.startswith(("http://", "https://"))]
        
        if len(valid_urls) < len(picture_urls):
            print(f"  ⚠️  Filtered out {len(picture_urls) - len(valid_urls)} invalid URLs (file paths)")
        
        if len(valid_urls) < 4:
            print(f"  ⏭️  Skipped {room_name}: Only {len(valid_urls)} valid HTTP URLs (need at least 4)")
            print(f"  ⚠️  Keeping external version to avoid data loss")
            continue
        

        # Try to upload first to verify data is valid
        upload_result = await ext_api.export_room_to_api(
            room_name=room_name,
            roomtype=local_data.get("roomtype", "Unclassified"),
            picture_urls=valid_urls,
            description=local_data.get("description", ""),
            doc_by_user_id=local_data.get("doc_by_user_id", 0),
            tags=local_data.get("tags", []),
            last_edited_by=local_data.get("edited_by_user_id")
        )
        
        if not upload_result.get("success"):
            # Check if this is a skippable error (like not enough images)
            if upload_result.get("skipped"):
                print(f"  ⏭️  Skipped {room_name}: {upload_result.get('error')}")
            else:
                print(f"  ❌ Failed to upload {room_name}: {upload_result.get('error')}")
                print(f"  ⚠️  Keeping external version to avoid data loss")
            continue
        
        print(f"  ✅ Updated {room_name} in external database")

    # Process newer externally - delete local and re-download
    for room_name, ext_data in newer_externally:
        print(f"🔄 Updating local database (external is newer): {room_name}")
        
        # Validate image URLs from external API - filter out file paths
        picture_urls = ext_data.get("images", [])
        valid_urls = [url for url in picture_urls if url.startswith(("http://", "https://"))]
        
        if len(valid_urls) < len(picture_urls):
            print(f"  ⚠️  External API sent {len(picture_urls) - len(valid_urls)} invalid URLs (file paths) - filtered out")
        
        # Get existing local data to preserve edit history before updating
        local_room = datamanager.room_db_handler.get_roominfo(room_name)
        existing_edits = local_room.get('edits', []) if local_room else None
        
        # Use replace_doc to update without destroying edit history
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
        print(f"  ✅ Updated {room_name} in local database")

    print(f"✅ Database synchronization complete!")
    print(f"   📤 Uploaded: {len(missing_externally)} rooms")
    print(f"   📥 Downloaded: {len(missing_locally)} rooms")
    print(f"   🔄 Updated externally: {len(newer_locally)} rooms")
    print(f"   🔄 Updated locally: {len(newer_externally)} rooms")

