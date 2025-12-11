# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Research Commands

PRINT_PREFIX = "RESEARCH COMMANDS"

# Standard library imports
import asyncio
import io
import json
from typing import Optional

# Third-party imports
import aiohttp
import discord
from discord import app_commands
from PIL import Image

# Local imports
from config.vars import RoomType, Tags
from src import shared
from src.api import _r2_handler, external_api
from src.datamanager.db_handlers import room_db_handler
from src.utils import embeds, utils

async def _get_image_links(images: list[Optional[discord.Attachment]], brighten: bool, room_name: str) -> list[str]:
    """Process attachments and return list of image links."""
    image_links = []
    
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for i, img in enumerate(images, 1):
            # Download and process image
            try:
                async with session.get(img.url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        
                        if brighten:
                            # Apply gamma correction
                            pil_img = Image.open(io.BytesIO(data))
                            gamma = 0.3  # Lower gamma = brighter 
                            brightened = pil_img.point(lambda x: int(255 * ((x / 255) ** gamma)))
                            
                            # Convert back to bytes
                            output = io.BytesIO()
                            brightened.save(output, format='PNG')
                            output.seek(0)
                            processed_data = output.getvalue()
                        else:
                            processed_data = data
                        
                        # Upload to R2
                        r2_url = await _r2_handler.upload_to_r2(processed_data, room_name, i)
                        if r2_url:
                            image_links.append(r2_url)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"[ERROR] [{PRINT_PREFIX}] Error downloading image {i}: {e}")
                continue
    
    return image_links

class ResearchCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="research", description="Research Division commands")
    
    @app_commands.command(name="document", description="Add a documentation entry to the database.")
    @app_commands.describe(
        roomname="Name of the room",
        roomtype="Type of the room",
        description="Brief description of the room",
        image1="First image",
        image2="Second image", 
        image3="Third image",
        image4="Fourth image",
        image5="Fifth image (optional)",
        image6="Sixth image (optional)",
        image7="Seventh image (optional)",
        image8="Eighth image (optional)",
        image9="Ninth image (optional)",
        image10="Tenth image (optional)",
        ss="Is this a SS room?",
        pss="Is this a PSS room?",
        brighten="Apply gamma correction to brighten images?"
    )
    async def document(
    self,
    interaction: discord.Interaction,
    roomname: str,
    roomtype: RoomType,
    description: str,
    image1: discord.Attachment,
    image2: discord.Attachment,
    image3: discord.Attachment,
    image4: discord.Attachment,
    image5: Optional[discord.Attachment] = None,
    image6: Optional[discord.Attachment] = None,
    image7: Optional[discord.Attachment] = None,
    image8: Optional[discord.Attachment] = None,
    image9: Optional[discord.Attachment] = None,
    image10: Optional[discord.Attachment] = None,
    ss: Optional[bool] = False,
    pss: Optional[bool] = False,
    brighten: Optional[bool] = True):
        """Document a room with images and description."""
        print(f"[INFO] [{PRINT_PREFIX}] Document room '{roomname}' by {interaction.user}")
        print(f"[DEBUG] [{PRINT_PREFIX}] Room type: {roomtype}, Images provided: {sum([1 for img in [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10] if img])}")
        await interaction.response.defer()
        
        print(f"[DEBUG] [{PRINT_PREFIX}] Checking permissions for user {interaction.user}")
        level = await utils.permission_check(interaction.user)
        if level < 2:
            print(f"[WARNING] [{PRINT_PREFIX}] Permission denied for user {interaction.user} (level: {level})")
            await interaction.followup.send("You do not have permission to document rooms. You need to be trial researcher or higher.", ephemeral=True)
            return
        
        # Check if room was already documented
        print(f"[{PRINT_PREFIX}] Checking if room '{roomname}' already exists")
        existing_room = room_db_handler.get_roominfo(roomname)
        if existing_room:
            print(f"[{PRINT_PREFIX}] Room '{roomname}' already documented, rejecting duplicate")
            await interaction.followup.send(f"The room '{roomname}' has already been documented.")
            return
        
        images = [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10] 
        images = [img for img in images if img is not None]
        image_links = await _get_image_links(images, brighten, roomname)

        # Make sure its only 10 images max
        image_links = image_links[:10]

        # Build tags list properly
        tags = []
        if ss:
            tags.append("SS")
        if pss:
            tags.append("PSS")

        doc_timestamp = discord.utils.utcnow().timestamp()
        
        room_db_handler.document_room(
            room_name=roomname,
            roomtype=roomtype,
            picture_urls=image_links,
            description=description,
            doc_by_user_id=interaction.user.id,
            tags=tags,
            timestamp=doc_timestamp
        )

        # Export to external API after local save
        api_response = await external_api.export_room_to_api(
            room_name=roomname,
            roomtype=roomtype,
            picture_urls=image_links,
            description=description,
            doc_by_user_id=interaction.user.id,
            tags=tags,
            timestamp=doc_timestamp
        )
        
        if not api_response.get("success"):
            if api_response.get("skipped"):
                print(f"[{PRINT_PREFIX}] Skipped external API export for '{roomname}': {api_response.get('error')}")
            else:
                print(f"[{PRINT_PREFIX}] Failed to export room '{roomname}' to external API: {api_response.get('error')}")

        embed = embeds.create_success_embed(
            "Room Documented",
            f"The room '{roomname}' has been successfully documented."
        )
        
        doc_embed, pictures = await embeds.send_room_documentation_embed(interaction.channel, {
            "room_name": roomname,
            "description": description,
            "doc_by_user_id": interaction.user.id,
            "last_updated": discord.utils.utcnow().timestamp(),
            "roomtype": roomtype,
            "tags": tags,
            "picture_urls": image_links,
            "edited_by_user_id": None  # New room, no edits yet
        }, return_embed=True)
        
        await interaction.channel.send(embed=doc_embed, files=pictures)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="redocument", description="Update an existing room's documentation.")
    @app_commands.describe(
        roomname="Name of the room",
        roomtype="Type of the room",
        description="Brief description of the room",
        image1="First image",
        image2="Second image", 
        image3="Third image",
        image4="Fourth image",
        image5="Fifth image (optional)",
        image6="Sixth image (optional)",
        image7="Seventh image (optional)",
        image8="Eighth image (optional)",
        image9="Ninth image (optional)",
        image10="Tenth image (optional)",
        ss="Is this a SS room?",
        pss="Is this a PSS room?",
        brighten="Apply gamma correction to brighten images?"
    )
    async def redocument(
    self,
    interaction: discord.Interaction,
    roomname: str,
    roomtype: RoomType,
    description: str,
    image1: discord.Attachment,
    image2: discord.Attachment,
    image3: discord.Attachment,
    image4: discord.Attachment,
    image5: Optional[discord.Attachment] = None,
    image6: Optional[discord.Attachment] = None,
    image7: Optional[discord.Attachment] = None,
    image8: Optional[discord.Attachment] = None,
    image9: Optional[discord.Attachment] = None,
    image10: Optional[discord.Attachment] = None,
    ss: Optional[bool] = False,
    pss: Optional[bool] = False,
    brighten: Optional[bool] = True):
        """Redocument an existing room with new images and description."""
        print(f"[INFO] [{PRINT_PREFIX}] Redocument room '{roomname}' by {interaction.user}")
        await interaction.response.defer()
        
        level = await utils.permission_check(interaction.user)
        if level < 2:
            await interaction.followup.send("You do not have permission to redocument rooms. You need to be novice researcher or higher.", ephemeral=True)
            return
        
        # Check if room exists
        existing_room = room_db_handler.get_roominfo(roomname)
        if not existing_room:
            await interaction.followup.send(f"The room '{roomname}' does not exist.")
            return
        
        # Clear cached images for this room before uploading new ones
        await _r2_handler.delete_room_images(roomname)
        
        images = [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10] 
        images = [img for img in images if img is not None]
        image_links = await _get_image_links(images, brighten, roomname)

        # Make sure its only 10 images max
        image_links = image_links[:10]

        # Build tags list properly
        tags = []
        if ss:
            tags.append("SS")
        if pss:
            tags.append("PSS")

        redoc_timestamp = discord.utils.utcnow().timestamp()
        
        room_db_handler.document_room(
            room_name=roomname,
            roomtype=roomtype,
            picture_urls=image_links,
            description=description,
            doc_by_user_id=existing_room['doc_by_user_id'],  # Preserve original documenter
            tags=tags,
            timestamp=redoc_timestamp,
            edited_by_user_id=interaction.user.id  # Track who made this redocumentation
        )

        # Export to external API after local save (with edit tracking)
        api_response = await external_api.export_room_to_api(
            room_name=roomname,
            roomtype=roomtype,
            picture_urls=image_links,
            description=description,
            doc_by_user_id=interaction.user.id,
            tags=tags,
            last_edited_by=interaction.user.id,
            timestamp=redoc_timestamp
        )
        
        if not api_response.get("success"):
            if api_response.get("skipped"):
                print(f"[{PRINT_PREFIX}] Skipped external API export for '{roomname}': {api_response.get('error')}")
            else:
                print(f"[{PRINT_PREFIX}] Failed to export room '{roomname}' to external API: {api_response.get('error')}")

        embed = embeds.create_success_embed(
            "Room Redocumented",
            f"The room '{roomname}' has been successfully updated."
        )

        doc_embed, pictures = await embeds.send_room_documentation_embed(interaction.channel, {
            "room_name": roomname,
            "description": description,
            "doc_by_user_id": interaction.user.id,
            "last_updated": discord.utils.utcnow().timestamp(),
            "roomtype": roomtype,
            "tags": tags,
            "picture_urls": image_links,
            "edited_by_user_id": interaction.user.id
        }, return_embed=True)

        await interaction.channel.send(embed=doc_embed, files=pictures)
        await interaction.followup.send(embed=embed)

        await utils.global_reset(roomname)

    @app_commands.command(name="set_description", description="Set the description of a specific room.")
    @app_commands.describe(roomname="Name of the room", description="New description for the room")
    async def set_description(self, interaction: discord.Interaction, roomname: str, description: str):
        """Set the description of a specific room."""
        print(f"[INFO] [{PRINT_PREFIX}] Set description for '{roomname}' by {interaction.user}")
        await interaction.response.defer()

        level = await utils.permission_check(interaction.user)
        if level < 2:
            await interaction.followup.send("You do not have permission to set room descriptions. You need to be novice researcher or higher.", ephemeral=True)
            return
        
        success = room_db_handler.set_roomdescription(roomname, description, edited_by_user_id=interaction.user.id)
        if success:
            await utils.global_reset(roomname)
            
            # Export to external API after local save
            api_response = await external_api.update_room_description_api(
                room_name=roomname,
                description=description,
                edited_by=interaction.user.id
            )
            
            if not api_response.get("success"):
                if not api_response.get("skipped"):
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to update description for '{roomname}' on external API: {api_response.get('error')}")
            
            embed = embeds.create_success_embed(
                "Description Updated",
                f"The description for room '{roomname}' has been updated."
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = embeds.create_error_embed(
                "Update Failed",
                f"The room '{roomname}' does not exist in the database."
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="set_roomtype", description="Set the type of a specific room.")
    @app_commands.describe(roomname="Name of the room", roomtype="Type of the room")
    async def set_roomtype(self, interaction: discord.Interaction, roomname: str, roomtype: RoomType):
        """Set the type of a specific room."""
        print(f"[INFO] [{PRINT_PREFIX}] Set roomtype for '{roomname}' to '{roomtype}' by {interaction.user}")
        await interaction.response.defer()

        level = await utils.permission_check(interaction.user)
        if level < 2:
            await interaction.followup.send("You do not have permission to set room types. You need to be novice researcher or higher.", ephemeral=True)
            return
        
        success = room_db_handler.set_roomtype(roomname, roomtype, edited_by_user_id=interaction.user.id)
        if success:
            await utils.global_reset(roomname)
            
            # Export to external API after local save
            api_response = await external_api.update_room_roomtype_api(
                room_name=roomname,
                roomtype=roomtype,
                edited_by=interaction.user.id
            )
            
            if not api_response.get("success"):
                if not api_response.get("skipped"):
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to update roomtype for '{roomname}' on external API: {api_response.get('error')}")
            
            embed = embeds.create_success_embed(
                "Room Type Updated",
                f"The room '{roomname}' has been updated to type '{roomtype}'."
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = embeds.create_error_embed(
                "Update Failed",
                f"The room '{roomname}' does not exist in the database."
            )
            await interaction.followup.send(embed=embed)
        
    

    @app_commands.command(name="set_tags", description="Set/replace all tags for a room (replaces existing tags).")
    @app_commands.describe(roomname="Name of the room")
    async def set_tags(
        self,
        interaction: discord.Interaction,
        roomname: str,
        tag1: Optional[Tags] = None,
        tag2: Optional[Tags] = None,
        tag3: Optional[Tags] = None,
        tag4: Optional[Tags] = None,
        tag5: Optional[Tags] = None,
        tag6: Optional[Tags] = None,
        tag7: Optional[Tags] = None,
        tag8: Optional[Tags] = None,
        tag9: Optional[Tags] = None,
        tag10: Optional[Tags] = None
    ):
        """Set tags for a room (replaces existing tags)."""
        print(f"[INFO] [{PRINT_PREFIX}] Set tags for '{roomname}' by {interaction.user}")
        await interaction.response.defer()

        level = await utils.permission_check(interaction.user)
        if level < 1:
            await interaction.followup.send("You do not have permission to set room tags. You need to be trial researcher or higher.", ephemeral=True)
            return
        
        roomdata = room_db_handler.get_roominfo(roomname)
        if not roomdata:
            embed = embeds.create_error_embed(
                "Update Failed",
                f"The room '{roomname}' does not exist in the database."
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Collect all non-None tags and remove duplicates
        new_tags = list({tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9, tag10} - {None})
        
        if not new_tags:
            embed = embeds.create_error_embed(
                "No Tags Provided",
                f"You must provide at least one tag to set."
            )
            await interaction.followup.send(embed=embed)
            return

        success = room_db_handler.set_roomtags(roomname, new_tags, edited_by_user_id=interaction.user.id)
        if success:
            await utils.global_reset(roomname)
            
            # Export to external API after local save
            api_response = await external_api.update_room_tags_api(
                room_name=roomname,
                tags=new_tags,
                edited_by=interaction.user.id
            )
            
            if not api_response.get("success"):
                if not api_response.get("skipped"):
                    print(f"[{PRINT_PREFIX}] Failed to update tags for '{roomname}' on external API: {api_response.get('error')}")
            
            embed = embeds.create_success_embed(
                "Room Tags Replaced",
                f"The room '{roomname}' now has tags: {', '.join(new_tags)}."
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = embeds.create_error_embed(
                "Update Failed",
                f"Something went wrong while updating tags for room '{roomname}'."
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="add_tags", description="Add tags to a room (keeps existing tags).")
    @app_commands.describe(roomname="Name of the room")
    async def add_tags(self, interaction: discord.Interaction, roomname: str, tag1: Tags, tag2: Optional[Tags] = None, tag3: Optional[Tags] = None):
        """Add tags to a room (keeps existing tags)."""
        print(f"[INFO] [{PRINT_PREFIX}] Add tags to '{roomname}' by {interaction.user}")
        await interaction.response.defer()

        level = await utils.permission_check(interaction.user)
        if level < 1:
            await interaction.followup.send("You do not have permission to add room tags. You need to be trial researcher or higher.", ephemeral=True)
            return
        
        roomdata = room_db_handler.get_roominfo(roomname)
        if not roomdata:
            embed = embeds.create_error_embed(
                "Update Failed",
                f"The room '{roomname}' does not exist in the database."
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Make sure the tags are unique
        tags = list({tag1, tag2, tag3} - {None})

        room_tags = roomdata.get('tags', [])
        added_count = 0
        for tag in tags:
            if tag not in room_tags:
                room_tags.append(tag)
                added_count += 1

        if added_count == 0:
            embed = embeds.create_error_embed(
                "No Tags Added",
                f"All specified tags already exist on room '{roomname}'."
            )
            await interaction.followup.send(embed=embed)
            return

        success = room_db_handler.set_roomtags(roomname, room_tags, edited_by_user_id=interaction.user.id)
        if success:
            await utils.global_reset(roomname)
            
            # Export to external API after local save
            api_response = await external_api.update_room_tags_api(
                room_name=roomname,
                tags=room_tags,
                edited_by=interaction.user.id
            )
            
            if not api_response.get("success"):
                if not api_response.get("skipped"):
                    print(f"[{PRINT_PREFIX}] Failed to update tags for '{roomname}' on external API: {api_response.get('error')}")
            
            embed = embeds.create_success_embed(
                "Room Tags Added",
                f"Added {added_count} tag(s) to '{roomname}'. Current tags: {', '.join(room_tags)}."
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = embeds.create_error_embed(
                "Update Failed",
                f"Something went wrong while updating tags for room '{roomname}'."
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="remove_tags", description="Remove tags from a specific room.")
    @app_commands.describe(roomname="Name of the room")
    async def remove_tags(self, interaction: discord.Interaction, roomname: str, tag1: Tags, tag2: Optional[Tags] = None, tag3: Optional[Tags] = None):
        """Remove tags from a specific room."""
        print(f"[INFO] [{PRINT_PREFIX}] Remove tags from '{roomname}' by {interaction.user}")
        await interaction.response.defer()

        level = await utils.permission_check(interaction.user)
        if level < 1:
            await interaction.followup.send("You do not have permission to remove room tags. You need to be trial researcher or higher.", ephemeral=True)
            return
        
        roomdata = room_db_handler.get_roominfo(roomname)
        if not roomdata:
            embed = embeds.create_error_embed(
                "Update Failed",
                f"The room '{roomname}' does not exist in the database."
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Collect tags to remove
        tags_to_remove = list({tag1, tag2, tag3} - {None})
        
        # Get current tags and remove specified ones
        room_tags = roomdata.get('tags', [])
        original_count = len(room_tags)
        room_tags = [tag for tag in room_tags if tag not in tags_to_remove]
        removed_count = original_count - len(room_tags)
        
        if removed_count == 0:
            embed = embeds.create_error_embed(
                "No Tags Removed",
                f"None of the specified tags were found on room '{roomname}'."
            )
            await interaction.followup.send(embed=embed)
            return
        
        success = room_db_handler.set_roomtags(roomname, room_tags, edited_by_user_id=interaction.user.id)
        if success:
            await utils.global_reset(roomname)
            
            # Export to external API after local save
            api_response = await external_api.update_room_tags_api(
                room_name=roomname,
                tags=room_tags,
                edited_by=interaction.user.id
            )
            
            if not api_response.get("success"):
                if not api_response.get("skipped"):
                    print(f"[{PRINT_PREFIX}] Failed to update tags for '{roomname}' on external API: {api_response.get('error')}")
            
            embed = embeds.create_success_embed(
                "Room Tags Updated",
                f"Removed {removed_count} tag(s) from '{roomname}'. Remaining tags: {', '.join(room_tags) if room_tags else 'None'}."
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = embeds.create_error_embed(
                "Update Failed",
                f"Something went wrong while removing tags from room '{roomname}'."
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="rename", description="Rename a specific room.")
    @app_commands.describe(roomname="Current name of the room", newname="New name for the room")
    async def rename(self, interaction: discord.Interaction, roomname: str, newname: str):
        """Rename a specific room."""
        print(f"[INFO] [{PRINT_PREFIX}] Rename room '{roomname}' to '{newname}' by {interaction.user}")
        await interaction.response.defer()

        level = await utils.permission_check(interaction.user)
        if level < 3:
            await interaction.followup.send("You do not have permission to rename rooms. You need to be experienced researcher or higher.", ephemeral=True)
            return
        
        success = room_db_handler.rename_room(roomname, newname, edited_by_user_id=interaction.user.id)
        if success:
            await utils.global_reset(newname)
            
            # Export to external API after local save
            api_response = await external_api.rename_room_api(
                old_name=roomname,
                new_name=newname,
                edited_by=interaction.user.id
            )
            
            if not api_response.get("success"):
                if not api_response.get("skipped"):
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to rename room '{roomname}' to '{newname}' on external API: {api_response.get('error')}")
            
            embed = embeds.create_success_embed(
                "Room Renamed",
                f"The room '{roomname}' has been renamed to '{newname}'."
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = embeds.create_error_embed(
                "Rename Failed",
                f"The room '{roomname}' does not exist in the database."
            )
            await interaction.followup.send(embed=embed)



    @app_commands.command(name="deletedoc", description="Delete documentation for a specific room.")
    @app_commands.describe(roomname="Name of the room")
    async def deletedoc(self, interaction: discord.Interaction, roomname: str):
        """Delete room documentation."""
        await interaction.response.defer()

        level = await utils.permission_check(interaction.user)
        if level < 3:
            await interaction.followup.send("You do not have permission to delete room documentation. You need to be experienced researcher or higher.", ephemeral=True)
            return
        
        # Delete the room images from R2 and cache before deleting from database
        await _r2_handler.delete_room_images(roomname)
        
        success = room_db_handler.delete_room(roomname)
        
        if success:
            # Export deletion to external API after local delete
            api_response = await external_api.delete_room_api(roomname)
            
            if not api_response.get("success"):
                if not api_response.get("skipped"):
                    print(f"[ERROR] [{PRINT_PREFIX}] Failed to delete room '{roomname}' from external API: {api_response.get('error')}")
            
            embed = embeds.create_success_embed(
                "Documentation Deleted",
                f"The documentation for room '{roomname}' has been deleted."
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = embeds.create_error_embed(
                "Deletion Failed",
                f"The room '{roomname}' does not exist in the database."
            )
            await interaction.followup.send(embed=embed)

shared.FRD_bot.tree.add_command(ResearchCommands())