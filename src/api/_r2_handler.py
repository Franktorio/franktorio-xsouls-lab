# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# API handler for Cloudflare R2 image storage

PRINT_PREFIX = "R2 HANDLER"

# Standard library imports
import asyncio
import os

# Third-party imports
import boto3
import requests
from botocore.config import Config

# Local imports
from config.vars import (
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    R2_MAX_RETRIES,
    R2_TIMEOUT_SECONDS
)


# Cache directory
CACHE_DIR = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), "databases", "images")

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
        return cache_filename
    elif "r2.cloudflarestorage.com/" in url:
        # Extract after bucket name
        if f"/{R2_BUCKET_NAME}/" in url:
            path_part = url.split(f"/{R2_BUCKET_NAME}/")[-1]
        else:
            path_part = url.split("/")[-1]
        cache_filename = path_part.replace('/', '_')
        return cache_filename
    elif "pub-04cb5978395f420cb9fc562a28212288.r2.dev/" in url:
        # Support old URL format
        path_part = url.split("pub-04cb5978395f420cb9fc562a28212288.r2.dev/")[-1]
        cache_filename = path_part.replace('/', '_')
        return cache_filename
    else:
        # Fallback for unknown URLs - extract just the filename
        return url.split('/')[-1]


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
                    f.write(data)
                print(f"[{PRINT_PREFIX}] Cached image: {cache_path}")
                return cache_path
            else:
                print(f"[{PRINT_PREFIX}] Failed to download image from {url}: Status {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"[{PRINT_PREFIX}] Error downloading image from {url}: {e}")
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
        print(f"[{PRINT_PREFIX}] Error removing cached image {cache_path}: {e}")
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
        print("[{PRINT_PREFIX}] Downloading and caching image")
        return await _download_and_cache(url)


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
        print(f"[{PRINT_PREFIX}] R2 credentials not set in config/vars.py")
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
        
        # Example: ElectricityPuzzle2/ElectricityPuzzle2_1.png
        clean_room_name = room_name.replace('/', '_').replace('\\', '_')
        filename = f"{clean_room_name}/{clean_room_name}_{image_index}.png"
        
        # Upload to R2
        s3_client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=filename,
            Body=image_data,
            ContentType='image/png'
        )
        
        # Return public URL
        pub_url = f"{R2_PUBLIC_URL}/{filename}"
        await _download_and_cache(pub_url)
        return pub_url
        
    except Exception as e:
        print(f"[{PRINT_PREFIX}] R2 upload failed: {e}")
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
                        print(f"[{PRINT_PREFIX}] Deleted R2 image: {filename}")
                        
                        # Remove cached image
                        url = f"{R2_PUBLIC_URL}/{filename}"
                        cache_removed = await remove_cached_image(url)
                        if cache_removed:
                            print(f"[{PRINT_PREFIX}] Removed cached image for: {filename}")
                    except Exception as e:
                        print(f"[{PRINT_PREFIX}] Failed to delete {filename}: {e}")
        except Exception as e:
            print(f"[{PRINT_PREFIX}] Failed to list objects for room {room_name}: {e}")
        
        return deleted_count > 0
        
    except Exception as e:
        print(f"[{PRINT_PREFIX}] R2 room image cleanup failed: {e}")
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
                    print(f"[{PRINT_PREFIX}] Deleted R2 image: {filename}")
                    
                    # Remove cached image
                    cache_removed = await remove_cached_image(url)
                    if cache_removed:
                        print(f"[{PRINT_PREFIX}] Removed cached image for: {filename}")
                except Exception as e:
                    print(f"[{PRINT_PREFIX}] Failed to delete {filename}: {e}")
        
        return deleted_count > 0
        
    except Exception as e:
        print(f"[{PRINT_PREFIX}] R2 cleanup failed: {e}")
        return False
    




