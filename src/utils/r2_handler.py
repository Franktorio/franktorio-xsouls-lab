# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# API handler for Cloudflare R2 image storage

PRINT_PREFIX = "R2 HANDLER"

# Standard library imports
import asyncio
import io
import os
import datetime

# Third-party imports
import boto3
import requests
import discord
from botocore.config import Config
from PIL import Image

# Local imports
from src.datamanager.database_manager import DB_DIR
from config.vars import (
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    R2_MAX_RETRIES,
    R2_TIMEOUT_SECONDS,
    WEBP_QUALITY
)


# Cache directory
CACHE_DIR = os.path.join(DB_DIR, "images")
CACHE = {"order": [], "rooms": {}}  # order tracks LRU, rooms stores image data by room
cache_lock = asyncio.Lock()
MAX_CACHED_ROOMS = 10  # Maximum number of rooms to cache
current_cache_size = 0  # Track current cache size in bytes

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)


def _get_cache_filename(url: str) -> str:
    """Generate a consistent cache filename from a URL."""
    # Extract the filename from the URL (e.g., room_name/room_name_0.png)
    if "cdn.xsoul.org/" in url:
        # Extract everything after the domain
        path_part = url.split("cdn.xsoul.org/")[-1]
        # Replace / with _ to flatten folder structure for cache
        cache_filename = path_part.replace('/', '_')
    elif "r2.cloudflarestorage.com/" in url:
        # Extract after bucket name
        if f"/{R2_BUCKET_NAME}/" in url:
            path_part = url.split(f"/{R2_BUCKET_NAME}/")[-1]
        else:
            path_part = url.split("/")[-1]
        cache_filename = path_part.replace('/', '_')
    elif "pub-04cb5978395f420cb9fc562a28212288.r2.dev/" in url:
        # Support old URL format
        path_part = url.split("pub-04cb5978395f420cb9fc562a28212288.r2.dev/")[-1]
        cache_filename = path_part.replace('/', '_')
    else:
        # Fallback for unknown URLs - extract just the filename
        cache_filename = url.split('/')[-1]
    
    if not cache_filename.endswith('.webp'):
        base_name = os.path.splitext(cache_filename)[0]
        cache_filename = f"{base_name}.webp"
    
    return cache_filename


def _get_cache_path(url: str) -> str:
    """Get the full cache path for a URL."""
    return os.path.join(CACHE_DIR, _get_cache_filename(url))


def _is_cached(url: str) -> bool:
    """Check if an image URL is already cached."""
    cache_path = _get_cache_path(url)
    return os.path.exists(cache_path) and os.path.getsize(cache_path) > 0


async def _download_and_cache(url: str) -> str:
    """Download an image from URL and cache it. Returns the cache path."""
    
    # Replace any ? with %3F
    cache_path = _get_cache_path(url)
    
    # Run the blocking requests call in a thread pool to prevent blocking the event loop
    loop = asyncio.get_event_loop()
    
    def _sync_download():
        try:
            # Use requests with timeout
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.content

                # Write to cache
                with open(cache_path, 'wb') as f:
                    # Turn image to webp to save space
                    with Image.open(io.BytesIO(data)) as image:
                        webp_buffer = io.BytesIO()
                        image.save(webp_buffer, format="WEBP", quality=WEBP_QUALITY)
                        data = webp_buffer.getvalue()
                    f.write(data)

                print(f"[INFO] [{PRINT_PREFIX}] Cached image: {cache_path}")
                return cache_path
            else:
                print(f"[ERROR] [{PRINT_PREFIX}] Failed to download image from {url}: Status {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] [{PRINT_PREFIX}] Error downloading image from {url}: {e}")
            return None
    
    return await loop.run_in_executor(None, _sync_download)

async def remove_cached_image(url: str) -> bool:
    """Remove a cached image given its URL."""
    cache_path = _get_cache_path(url)
    try:
        if os.path.exists(cache_path):
            os.remove(cache_path)
            return True
        return False
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error removing cached image {cache_path}: {e}")
        return False

async def get_cached_image_path(url: str) -> str:
    """
    Get the local cache path for an image URL.
    Downloads and caches if not already cached.
    Returns the cache path, or None if download fails.
    """
    url = url.replace('?', '%3F')
    if _is_cached(url):
        return _get_cache_path(url)
    else:
        print(f"[INFO] [{PRINT_PREFIX}] Downloading and caching image")
        return await _download_and_cache(url)
    
def get_paths_of_cached_images() -> set | None:
    """Return the a set of cached images on disk."""
    try:
        files = os.listdir(CACHE_DIR)
        valid_files = [f for f in files if os.path.getsize(os.path.join(CACHE_DIR, f)) > 0]
        return set(valid_files)
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] Error counting cached images: {e}")
        return None
    

async def upload_to_r2(image_data, room_name: str, image_index: int = 1):
    """
    Upload image data to Cloudflare R2 and return the URL
    
    Args:
        image_data: Image bytes to upload
        room_name: Name of the room (used in filename)
        image_index: Index of the image (1, 2, 3, etc.) - starts at 1
    
    Returns:
        Public URL of uploaded image or None if failed
    """
    if not R2_ACCESS_KEY_ID or not R2_SECRET_ACCESS_KEY:
        print(f"[WARNING] [{PRINT_PREFIX}] R2 credentials not set in config/vars.py")
        return None
    
    try:
        endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        
        config = Config(
            retries={'max_attempts': R2_MAX_RETRIES, 'mode': 'adaptive'},
            connect_timeout=R2_TIMEOUT_SECONDS,
            read_timeout=R2_TIMEOUT_SECONDS,
            signature_version='s3v4'
        )
        
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=config,
            region_name='auto'
        )
        
        # Convert image to WebP format
        # Check if image isn't WEBP already
        if not image_data.startswith(b'RIFF') or not image_data[8:12] == b'WEBP':
            with Image.open(io.BytesIO(image_data)) as image:
                webp_buffer = io.BytesIO()
                image.save(webp_buffer, format='WEBP', quality=WEBP_QUALITY)
                webp_data = webp_buffer.getvalue()
        else:
            webp_data = image_data

        
        # Example: ElectricityPuzzle2/ElectricityPuzzle2_1.webp
        clean_room_name = room_name.replace('/', '_').replace('\\', '_')
        filename = f"{clean_room_name}/{clean_room_name}_{image_index}.webp"
        
        # Upload to R2 with cache control headers to prevent stale cache
        s3_client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=filename,
            Body=webp_data,
            ContentType='image/webp',
            CacheControl='public, max-age=604800'  # Cache for a week
        )
        
        pub_url = f"{R2_PUBLIC_URL}/{filename}" # timestamp to bust CDN cache
        await _download_and_cache(pub_url)
        return pub_url
        
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] R2 upload failed: {e}")
        return None

async def delete_room_images(room_name: str) -> bool:
    """
    Delete all images associated with a specific room from R2 and cache.
    This function searches for and deletes all images matching the room name pattern.
    
    Args:
        room_name: Name of the room whose images should be deleted
    
    Returns:
        True if any images were deleted, False otherwise
    """
    if not R2_ACCESS_KEY_ID or not R2_SECRET_ACCESS_KEY:
        print(f"[ERROR] [{PRINT_PREFIX}] R2 credentials not set")
        return False
    
    try:
        # R2 endpoint format: https://<account_id>.r2.cloudflarestorage.com
        endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        
        # Configure S3 client for R2
        config = Config(
            retries={'max_attempts': R2_MAX_RETRIES, 'mode': 'adaptive'},
            connect_timeout=R2_TIMEOUT_SECONDS,
            read_timeout=R2_TIMEOUT_SECONDS,
            signature_version='s3v4'
        )
        
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=config,
            region_name='auto'
        )
        
        # Clean room name for filename matching
        clean_room_name = room_name.replace('/', '_').replace('\\', '_')
        prefix = f"{clean_room_name}/"
        
        # List all objects with this room prefix
        deleted_count = 0
        try:
            response = s3_client.list_objects_v2(
                Bucket=R2_BUCKET_NAME,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    filename = obj['Key']
                    try:
                        s3_client.delete_object(
                            Bucket=R2_BUCKET_NAME,
                            Key=filename
                        )
                        deleted_count += 1
                        print(f"[INFO] [{PRINT_PREFIX}] Deleted R2 image: {filename}")
                        
                        # Remove from both disk cache AND memory cache
                        url = f"{R2_PUBLIC_URL}/{filename}"
                        cache_removed = await remove_cached_image(url)
                        if cache_removed:
                            print(f"[INFO] [{PRINT_PREFIX}] Removed disk cached image for: {filename}")
                        
                        # Remove from memory cache as well
                        remove_image_from_memory_cache(url)
                    except Exception as e:
                        print(f"[ERROR] [{PRINT_PREFIX}] Failed to delete {filename}: {e}")
        except Exception as e:
            print(f"[ERROR] [{PRINT_PREFIX}] Failed to list objects for room {room_name}: {e}")
        
        return deleted_count > 0
        
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] R2 room image cleanup failed: {e}")
        return False


async def delete_r2_images(image_urls):
    """
    Delete images from Cloudflare R2 given their URLs
    
    Args:
        image_urls: List of R2 image URLs to delete
    
    Returns:
        True if any images were deleted, False otherwise
    """
    if not R2_ACCESS_KEY_ID or not R2_SECRET_ACCESS_KEY:
        print(f"[{PRINT_PREFIX}] R2 credentials not set")
        return False
    
    try:
        # R2 endpoint format: https://<account_id>.r2.cloudflarestorage.com
        endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        
        # Configure S3 client for R2
        config = Config(
            retries={'max_attempts': R2_MAX_RETRIES, 'mode': 'adaptive'},
            connect_timeout=R2_TIMEOUT_SECONDS,
            read_timeout=R2_TIMEOUT_SECONDS,
            signature_version='s3v4'
        )
        
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=config,
            region_name='auto'
        )
        
        deleted_count = 0
        for url in image_urls:
            # Check if URL is from our R2 bucket
            if "cdn.xsoul.org/" in url or f"{R2_ACCOUNT_ID}.r2.cloudflarestorage.com/" in url or "pub-04cb5978395f420cb9fc562a28212288.r2.dev/" in url:
                # Extract filename from URL (including folder structure like room_name/room_name_0.png)
                if "cdn.xsoul.org/" in url:
                    filename = url.split("cdn.xsoul.org/")[-1]
                elif f"/{R2_BUCKET_NAME}/" in url:
                    filename = url.split(f"/{R2_BUCKET_NAME}/")[-1]
                else:
                    filename = "/".join(url.split("/")[-2:])
                
                try:
                    s3_client.delete_object(
                        Bucket=R2_BUCKET_NAME,
                        Key=filename
                    )
                    deleted_count += 1
                    print(f"[INFO] [{PRINT_PREFIX}] Deleted R2 image: {filename}")
                    
                    # Remove from both disk cache AND memory cache
                    cache_removed = await remove_cached_image(url)
                    if cache_removed:
                        print(f"[INFO] [{PRINT_PREFIX}] Removed disk cached image for: {filename}")
                    
                    # Remove from memory cache as well
                    remove_image_from_memory_cache(url)
                except Exception as e:
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to delete {filename}: {e}")
        
        return deleted_count > 0
        
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] R2 cleanup failed: {e}")
        return False
    
async def get_stored_images(room_data, roomname):
    """
    Retrieve stored images for a room from cache or disk.
    Returns a list of discord.File objects for sending in messages.
    """

    files = []
    images_urls = room_data.get("picture_urls", [])
    now = datetime.datetime.now().timestamp()

    for i, img_url in enumerate(images_urls):
        try:
            # Get cached image path
            cache_path = await get_cached_image_path(img_url)
            if not cache_path or not os.path.exists(cache_path) or os.path.getsize(cache_path) == 0:
                print(f"[WARN] [{PRINT_PREFIX}] Invalid memory cache path for {img_url}, skipping")
                continue
            async with cache_lock:
                # Use memory cache if valid
                cached_entry = get_image_from_memory_cache(img_url)
                if cached_entry and now - cached_entry["timestamp"] < 1800 and cached_entry["bytes"]:
                    img_bytes = cached_entry["bytes"]
                    files.append(discord.File(io.BytesIO(img_bytes), filename=f"{roomname}_{i+1}.png"))
                    continue
                elif cached_entry is not None:
                    remove_image_from_memory_cache(img_url)

                # Read from disk
                def read_file(path):
                    with open(path, 'rb') as f:
                        return f.read()

                img_bytes = await asyncio.to_thread(read_file, cache_path)
                if not img_bytes:
                    print(f"[WARN] [{PRINT_PREFIX}] Disk image {roomname}_{i+1} is empty, skipping")
                    continue

                # Store in memory cache using helper
                add_image_to_memory_cache(img_url, img_bytes, roomname)

                files.append(discord.File(io.BytesIO(img_bytes), filename=f"{roomname}_{i+1}.png"))
                print(f"[INFO] [{PRINT_PREFIX}] Cached image {roomname}_{i+1} in memory")

        except Exception as e:
            print(f"[ERROR] [{PRINT_PREFIX}] Error loading image {roomname}_{i+1}: {e}")

    return files

def get_image_from_memory_cache(url: str) -> dict:
    """Retrieve an image's cache entry from the in-memory cache.
    Updates LRU order by moving to end.
    
    Returns:
        Dictionary with 'bytes' and 'timestamp' keys, or None if not cached.
    """
    # Find which room contains this URL
    for room_name, images in CACHE["rooms"].items():
        if url in images:
            # Update LRU order - move room to end (most recently used)
            if room_name in CACHE["order"]:
                CACHE["order"].remove(room_name)
                CACHE["order"].append(room_name)
            
            print(f"[DEBUG] [{PRINT_PREFIX}] Retrieved image from memory cache for URL: {url}")
            return images[url]
    
    print(f"[DEBUG] [{PRINT_PREFIX}] Image not found in memory cache for URL: {url}")
    return None

def add_image_to_memory_cache(url: str, image_bytes: bytes, room_name: str = None):
    """Add an image's bytes to the in-memory cache.
    Evicts oldest rooms if cache exceeds 10 rooms limit.
    
    Args:
        url: Image URL
        image_bytes: Image bytes data
        room_name: Name of the room (extracted from URL if not provided)
    """
    global current_cache_size
    
    image_size = len(image_bytes)
    now = datetime.datetime.now().timestamp()
    
    # Extract room name from URL if not provided
    if not room_name:
        # URL format: cdn.xsoul.org/RoomName/RoomName_1.png
        if "cdn.xsoul.org/" in url:
            room_name = url.split("cdn.xsoul.org/")[1].split("/")[0]
        elif "r2.cloudflarestorage.com/" in url or "r2.dev/" in url:
            # Extract room name from path
            path_parts = url.split("/")
            if len(path_parts) >= 2:
                room_name = path_parts[-2]
    
    # If room_name still not found, use a default
    if not room_name:
        room_name = "unknown"
    
    # Check if room exists in cache
    if room_name not in CACHE["rooms"]:
        # Check if we need to evict oldest room
        if len(CACHE["rooms"]) >= MAX_CACHED_ROOMS:
            # Remove the oldest room (first in order list)
            oldest_room = CACHE["order"][0]
            images_to_remove = CACHE["rooms"][oldest_room]
            for old_url, old_data in images_to_remove.items():
                old_size = len(old_data["bytes"])
                current_cache_size -= old_size
            del CACHE["rooms"][oldest_room]
            CACHE["order"].remove(oldest_room)
            print(f"[INFO] [{PRINT_PREFIX}] Evicted room from cache: {oldest_room} ({len(images_to_remove)} images)")
        
        # Add new room
        CACHE["rooms"][room_name] = {}
        CACHE["order"].append(room_name)
    else:
        # Move room to end (most recently used)
        if room_name in CACHE["order"]:
            CACHE["order"].remove(room_name)
            CACHE["order"].append(room_name)
    
    # Add image to room
    CACHE["rooms"][room_name][url] = {"bytes": image_bytes, "timestamp": now}
    current_cache_size += image_size
    print(f"[INFO] [{PRINT_PREFIX}] Added image to memory cache: {url} ({image_size / (1024*1024):.2f}MB, room: {room_name}, total rooms: {len(CACHE['rooms'])})")

def update_image_in_memory_cache(url: str, image_bytes: bytes):
    """Update an existing image's bytes in the in-memory cache."""
    global current_cache_size
    
    # Find the room containing this URL
    found = False
    for room_name, images in CACHE["rooms"].items():
        if url in images:
            # Update cache size accounting
            old_size = len(images[url]["bytes"])
            new_size = len(image_bytes)
            current_cache_size = current_cache_size - old_size + new_size
            
            now = datetime.datetime.now().timestamp()
            images[url] = {"bytes": image_bytes, "timestamp": now}
            
            # Move room to end (most recently used)
            if room_name in CACHE["order"]:
                CACHE["order"].remove(room_name)
                CACHE["order"].append(room_name)
            
            print(f"[INFO] [{PRINT_PREFIX}] Updated image in memory cache for URL: {url}")
            found = True
            break
    
    if not found:
        print(f"[WARNING] [{PRINT_PREFIX}] Attempted to update non-existent image in memory cache for URL: {url}")
        # Extract room name for adding to cache
        room_name = None
        if "cdn.xsoul.org/" in url:
            room_name = url.split("cdn.xsoul.org/")[1].split("/")[0]
        add_image_to_memory_cache(url, image_bytes, room_name)

def remove_image_from_memory_cache(url: str):
    """Remove an image from the in-memory cache."""
    global current_cache_size
    
    # Find and remove the image from its room
    for room_name, images in list(CACHE["rooms"].items()):
        if url in images:
            image_size = len(images[url]["bytes"])
            del images[url]
            current_cache_size -= image_size
            
            # If room has no more images, remove the room
            if not images:
                del CACHE["rooms"][room_name]
                if room_name in CACHE["order"]:
                    CACHE["order"].remove(room_name)
            
            print(f"[INFO] [{PRINT_PREFIX}] Removed image from memory cache for URL: {url} ({image_size / (1024*1024):.2f}MB)")
            return
    
    print(f"[WARNING] [{PRINT_PREFIX}] Attempted to remove non-existent image from memory cache for URL: {url}")


async def migrate_cdn_to_webp():
    """
    Migrate all non-WebP images in R2 bucket to WebP format.
    Downloads each non-WebP image, converts it to WebP, and re-uploads it.
    Processes multiple images concurrently for faster migration.
    
    Returns:
        dict: Statistics about the migration (total, converted, failed, skipped) and URL mappings
    """
    if not R2_ACCESS_KEY_ID or not R2_SECRET_ACCESS_KEY:
        print(f"[ERROR] [{PRINT_PREFIX}] R2 credentials not set")
        return {"error": "R2 credentials not set"}
    
    try:
        endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        
        config = Config(
            retries={'max_attempts': R2_MAX_RETRIES, 'mode': 'adaptive'},
            connect_timeout=R2_TIMEOUT_SECONDS,
            read_timeout=R2_TIMEOUT_SECONDS,
            signature_version='s3v4'
        )
        
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=config,
            region_name='auto'
        )
        
        # Statistics and URL mappings
        stats = {
            "total": 0,
            "converted": 0,
            "failed": 0,
            "skipped": 0,
            "url_mappings": {}  # old_url -> new_url
        }
        
        # Collect all keys to process
        print(f"[INFO] [{PRINT_PREFIX}] Starting CDN migration to WebP...")
        print(f"[INFO] [{PRINT_PREFIX}] Listing all objects in bucket...")
        all_keys = []
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=R2_BUCKET_NAME)
        
        for page in pages:
            if 'Contents' not in page:
                continue
            all_keys.extend([obj['Key'] for obj in page['Contents']])
        
        stats["total"] = len(all_keys)
        print(f"[INFO] [{PRINT_PREFIX}] Found {stats['total']} total objects")
        
        # Process images concurrently
        async def process_image(key):
            """Process a single image conversion."""
            # Skip if already WebP
            if key.lower().endswith('.webp'):
                old_url = f"{R2_PUBLIC_URL}/{key}"
                return {"status": "skipped", "old_url": old_url, "new_url": old_url}
            
            loop = asyncio.get_event_loop()
            
            def convert_image():
                try:
                    # Check if file still exists before processing (may have been converted already)
                    try:
                        s3_client.head_object(Bucket=R2_BUCKET_NAME, Key=key)
                    except Exception:
                        # File doesn't exist anymore (already converted by another batch)
                        base_key = os.path.splitext(key)[0]
                        new_key = f"{base_key}.webp"
                        return {
                            "status": "already_converted",
                            "old_url": f"{R2_PUBLIC_URL}/{key}",
                            "new_url": f"{R2_PUBLIC_URL}/{new_key}"
                        }
                    
                    # Download the image
                    print(f"[INFO] [{PRINT_PREFIX}] Processing {key}...")
                    response = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key=key)
                    image_data = response['Body'].read()
                    
                    # Convert to WebP
                    with Image.open(io.BytesIO(image_data)) as image:
                        webp_buffer = io.BytesIO()
                        image.save(webp_buffer, format='WEBP', quality=WEBP_QUALITY)
                        webp_data = webp_buffer.getvalue()
                    
                    # Generate new key with .webp extension
                    base_key = os.path.splitext(key)[0]
                    new_key = f"{base_key}.webp"
                    
                    # Upload the WebP version
                    s3_client.put_object(
                        Bucket=R2_BUCKET_NAME,
                        Key=new_key,
                        Body=webp_data,
                        ContentType='image/webp',
                        CacheControl='public, max-age=604800'
                    )
                    
                    # Delete the old version
                    s3_client.delete_object(Bucket=R2_BUCKET_NAME, Key=key)
                    print(f"[INFO] [{PRINT_PREFIX}] Converted {key} -> {new_key}")
                    
                    return {
                        "status": "converted",
                        "old_url": f"{R2_PUBLIC_URL}/{key}",
                        "new_url": f"{R2_PUBLIC_URL}/{new_key}"
                    }
                    
                except Exception as e:
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to convert {key}: {e}")
                    return {"status": "failed", "error": str(e)}
            
            result = await loop.run_in_executor(None, convert_image)
            
            # Clear cache for old URL if converted
            if result["status"] == "converted":
                await remove_cached_image(result["old_url"])
                remove_image_from_memory_cache(result["old_url"])
            
            return result
        
        # Process all images concurrently (limit to 10 at a time to avoid overwhelming the service)
        batch_size = 10
        for i in range(0, len(all_keys), batch_size):
            batch = all_keys[i:i + batch_size]
            results = await asyncio.gather(*[process_image(key) for key in batch], return_exceptions=True)
            
            # Collect statistics
            for result in results:
                if isinstance(result, Exception):
                    stats["failed"] += 1
                    continue
                    
                if result["status"] == "skipped":
                    stats["skipped"] += 1
                    stats["url_mappings"][result["old_url"]] = result["new_url"]
                elif result["status"] == "converted":
                    stats["converted"] += 1
                    stats["url_mappings"][result["old_url"]] = result["new_url"]
                elif result["status"] == "already_converted":
                    # File was already converted by a previous batch, count as skipped
                    stats["skipped"] += 1
                    stats["url_mappings"][result["old_url"]] = result["new_url"]
                elif result["status"] == "failed":
                    stats["failed"] += 1
            
            print(f"[INFO] [{PRINT_PREFIX}] Progress: {i + len(batch)}/{len(all_keys)} processed")
        
        print(f"[INFO] [{PRINT_PREFIX}] Migration complete: {stats}")
        return stats
        
    except Exception as e:
        print(f"[ERROR] [{PRINT_PREFIX}] CDN migration failed: {e}")
        return {"error": str(e)}
