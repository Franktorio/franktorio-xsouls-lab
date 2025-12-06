# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Admin commands

# Standard library imports
import io
import json
from math import e
import re
from urllib import response
from typing import Optional
import aiohttp
import asyncio
import discord
import os
from discord.ext import commands
from discord import app_commands

# Local imports
from src import shared
from src import datamanager
from ..utils import _helpers
import config.vars as vars
from src.api import _r2_handler
from src.utils import embeds

class Admin(app_commands.Group):
    def __init__(self):
        super().__init__(name="dev", description="Developer only commands")

    @app_commands.command(name="restart", description="Shut down the bot and service will turn it on automatically.")
    async def restart_bot(self, interaction: discord.Interaction):
        """Restart the bot (shuts down, service will restart it)."""
        await interaction.response.defer()
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        embed = embeds.create_success_embed(
            title="Bot Restarting",
            description="The bot is restarting now. It will be back online shortly."
        )
        await interaction.followup.send(embed=embed)
        
        # Shutdown the bot
        await shared.FRD_bot.close()
        os._exit(0)

    @app_commands.command(name="global_reset_documented", description="Bulk deletes every message in the documented channel across all servers.")
    async def global_reset_documented(self, interaction: discord.Interaction):
        """Bulk deletes every message in the documented channel across all servers."""
        await interaction.response.defer()
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        total_deleted = 0
        failed_servers = []

        async def clear_guild_channel(guild):
            """Clear documented channel for a single guild."""
            try:
                server_profile = datamanager.server_db_handler.get_server_profile(guild.id)
                documented_channel_id = server_profile.get('documented_channel_id')
                if not documented_channel_id:
                    return 0
                
                channel = guild.get_channel(documented_channel_id)
                if not channel:
                    return 0
                
                def is_bot_message(message):
                    return message.author.id == shared.FRD_bot.user.id
                
                print(f"🗑️ Clearing documented channel in guild {guild.name} ({guild.id})")
                deleted = await channel.purge(check=is_bot_message, limit=None)
                datamanager.server_db_handler.clear_doc_ids(guild.id)
                print(f"✅ Cleared {len(deleted)} messages in guild {guild.name}")
                return len(deleted)
            except Exception as e:
                print(f"❌ Failed to clear documented channel in guild {guild.name} ({guild.id}): {e}")
                failed_servers.append(guild.name)
                return 0

        # Run all guild clears concurrently
        tasks = [clear_guild_channel(guild) for guild in shared.FRD_bot.guilds]
        results = await asyncio.gather(*tasks)
        total_deleted = sum(results)

        embed_desc = f"✅ Successfully deleted a total of {total_deleted} messages from documented channels across {len(shared.FRD_bot.guilds)} server(s)."
        if failed_servers:
            embed_desc += f"\n⚠️ Failed to clear documented channels in the following servers: {', '.join(failed_servers)}"

        embed = embeds.create_success_embed(
            title="Global Documented Channel Reset Complete",
            description=embed_desc
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="test_send_message", description="Tries to send a message in the research and leaderboard channels")
    async def test_send_message(self, interaction: discord.Interaction):
        """
        Test command to send a message in the research and leaderboard channels.
        """
        await interaction.response.defer(ephemeral=True)
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        server_profile = datamanager.server_db_handler.get_server_profile(interaction.guild.id)
        research_channel_id = server_profile.get('documented_channel_id')
        leaderboard_channel_id = server_profile.get('leaderboard_channel_id')

        research_channel = interaction.guild.get_channel(research_channel_id)
        leaderboard_channel = interaction.guild.get_channel(leaderboard_channel_id)

        test_embed = embeds.create_success_embed(
            "Test Message",
            "This is a test message sent to verify channel configurations."
        )

        r_message = None
        l_message = None

        # Try each channel individually and report results
        try:
            if research_channel:
                r_message = await research_channel.send(embed=test_embed)
                r_embed = embeds.create_success_embed(
                    "Research Channel Test Successful",
                    f"Message successfully sent in {research_channel.mention}."
                )
                await interaction.followup.send(embed=r_embed, ephemeral=True)
            else:
                r_embed = embeds.create_error_embed(
                    "Research Channel Not Found",
                    "The research channel ID is not set or the channel does not exist."
                )
                await interaction.followup.send(embed=r_embed, ephemeral=True)
        except Exception as e:
            r_embed = embeds.create_error_embed(
                "Research Channel Test Failed",
                f"Failed to send message in research channel: {str(e)}"
            )
            await interaction.followup.send(embed=r_embed, ephemeral=True)
        
        try:           
            if leaderboard_channel:
                l_message = await leaderboard_channel.send(embed=test_embed)
                l_embed = embeds.create_success_embed(
                    "Leaderboard Channel Test Successful",
                    f"Message successfully sent in {leaderboard_channel.mention}."
                )
                await interaction.followup.send(embed=l_embed, ephemeral=True)
            else:
                l_embed = embeds.create_error_embed(
                    "Leaderboard Channel Not Found",
                    "The leaderboard channel ID is not set or the channel does not exist."
                )
                await interaction.followup.send(embed=l_embed, ephemeral=True)
        except Exception as e:
            l_embed = embeds.create_error_embed(
                "Leaderboard Channel Test Failed",
                f"Failed to send message in leaderboard channel: {str(e)}"
            )
            await interaction.followup.send(embed=l_embed, ephemeral=True)

        await asyncio.sleep(10)

        # Clean up test messages
        try:
            if r_message:
                await r_message.delete()
            if l_message:
                await l_message.delete()
        except:
            pass
        

    @app_commands.command(name="cache_all_rooms", description="Cache all rooms from the database to R2")
    async def cache_all_rooms(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        
        rooms = datamanager.room_db_handler.get_all_room_names(sort_by="last_updated")
        total_rooms = len(rooms)
        cached = 0
        failed = 0
        cached_rooms = 0
        cached_failed_rooms = 0
        failed_rooms = []

        message_id = None
        channel = interaction.channel

        edit_cd = 0 # iterations

        async def _edit_or_send_embed(message_id: int):
            embed = discord.Embed(
                title="📦 Caching Rooms",
                description=f"Database cache loop.",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="📦 Total Rooms", value=str(total_rooms), inline=False)
            embed.add_field(name="✅ Cached", value=str(cached_rooms), inline=False)
            embed.add_field(name="❌ Failed", value=str(cached_failed_rooms), inline=False)
            embed.add_field(name="⏳ Progress", value=f"{((cached_rooms+cached_failed_rooms)/total_rooms)*100:.2f}%", inline=False)
            embed.add_field(name="🖼️ Images Cached", value=str(cached), inline=True)
            embed.add_field(name="🛑 Images Failed", value=str(failed), inline=True)
            embed.set_footer(text="Franktorio's & xSoul's Research Division", icon_url=shared.FRD_bot.user.display_avatar.url)

            if message_id is None:
                msg = await channel.send(embed=embed)
                return msg.id
            else:
                msg = await channel.fetch_message(message_id)
                await msg.edit(embed=embed)
                return message_id
            
        r_embed = discord.Embed(
            title="✅ Caching Started",
            description=f"Starting caching of {total_rooms} rooms from database.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        await interaction.followup.send(embed=r_embed)

        for room_name in rooms:
            room_info = datamanager.room_db_handler.get_roominfo(room_name)
            image_urls = room_info.get('picture_urls', [])

            try:
                edit_cd += 1
                if edit_cd >= 100:
                    message_id = await _edit_or_send_embed(message_id)
                    edit_cd = 0
            except Exception as e:
                print(f"❌ Error updating cache progress message: {e}")

            cache_failed = False
            for url in image_urls:

                path = await _r2_handler.get_cached_image_path(url)
                
        
                if path is None:
                    failed += 1
                    cache_failed = True
                else:
                    cached += 1
            
            if not cache_failed:
                cached_rooms += 1
            else:
                cached_failed_rooms += 1
                failed_rooms.append(room_name)
                
            
        final_embed = embeds.create_success_embed(
            "Caching Complete",
            f"**Total Rooms:** {total_rooms}\n**Cached:** {cached}\n**Failed:** {failed}"
        )
        if failed_rooms and cached_failed_rooms <= 10:
            final_embed.add_field(name="⚠️ Failed Rooms", value=", ".join(failed_rooms), inline=False)
        elif cached_failed_rooms > 10:
            final_embed.add_field(name="⚠️ Failed Rooms", value="❌ Too many to list.", inline=False)

        msg = await channel.fetch_message(message_id)
        await msg.edit(embed=final_embed)



    @app_commands.command(name="apply_web_db", description="Sync the database from the web API")
    async def apply_web_db(self, interaction: discord.Interaction):
        """
        Fetch the complete database from the web API and sync it locally.
        """
        await interaction.response.defer(ephemeral=True)
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        try:
            # Fetch data from API
            headers = {
                'Authorization': f'Bearer {vars.API_KEY}'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{vars.API_BASE_URL}/database/export", headers=headers) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(f"❌ API request failed with status {resp.status}")
                        return
                    
                    data = await resp.json()
            
            if not data.get('success'):
                await interaction.followup.send("❌ API returned unsuccessful response")
                return
            
            rooms = data.get('rooms', {})
            total_rooms = len(rooms)
            migrated = 0
            updated = 0
            failed = 0
            deleted = 0
            failed_rooms = []
            
            embed = discord.Embed(
                title="⏳ Web Database Sync Started",
                description=f"Starting sync of {total_rooms} rooms from web API.\nExported at: {data.get('exported_at')}",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Get all local rooms to check for deletions
            local_rooms = set(datamanager.room_db_handler.get_all_room_names(sort_by="room_name"))
            web_rooms = set(rooms.keys())
            
            # Rooms to delete (in local but not in web)
            rooms_to_delete = local_rooms - web_rooms
            
            for room_name, room_info in rooms.items():
                try:
                    # Extract data from API format
                    picture_urls = room_info.get("images", [])
                    description = room_info.get("description", "")
                    tags = room_info.get("tags", [])
                    roomtype = room_info.get("roomtype", "Unclassified")
                    doc_by_user_id = room_info.get("documented_by", 0)
                    last_edited = room_info.get("last_edited", discord.utils.utcnow().timestamp())
                    edited_by_user_id = room_info.get("last_edited_by", None)
                    edits = room_info.get("edits", [])
                    
                    # Check if room already exists
                    existing_room = datamanager.room_db_handler.get_roominfo(room_name)
                    
                    if existing_room:
                        # Room exists, use replace_doc to completely replace it with API data
                        success = datamanager.room_db_handler.replace_doc(
                            room_name=room_name,
                            picture_urls=picture_urls,
                            description=description,
                            doc_by_user_id=doc_by_user_id,
                            tags=tags,
                            roomtype=roomtype,
                            timestamp=last_edited,
                            edited_by_user_id=edited_by_user_id,
                            edits=edits
                        )
                        if success:
                            updated += 1
                        else:
                            failed += 1
                            failed_rooms.append(room_name)
                    else:
                        # Room doesn't exist, use replace_doc to create it with API data
                        success = datamanager.room_db_handler.replace_doc(
                            room_name=room_name,
                            picture_urls=picture_urls,
                            description=description,
                            doc_by_user_id=doc_by_user_id,
                            tags=tags,
                            roomtype=roomtype,
                            timestamp=last_edited,
                            edited_by_user_id=edited_by_user_id,
                            edits=edits
                        )
                        if success:
                            migrated += 1
                        else:
                            failed += 1
                            failed_rooms.append(room_name)
                        
                except Exception as e:
                    print(f"❌ Error syncing room '{room_name}': {e}")
                    failed += 1
                    failed_rooms.append(f"{room_name} ({str(e)})")
            
            # Delete rooms that are not in the web database
            for room_name in rooms_to_delete:
                try:
                    success = datamanager.room_db_handler.delete_room(room_name)
                    if success:
                        deleted += 1
                        print(f"🗑️ Deleted room '{room_name}' (not in web database)")
                    else:
                        print(f"⚠️ Failed to delete room '{room_name}'")
                except Exception as e:
                    print(f"❌ Error deleting room '{room_name}': {e}")
            
            # Send summary
            summary_desc = (
                f"**Total Rooms:** {total_rooms}\n"
                f"**Synced:** {migrated} | **Updated:** {updated}\n"
                f"**Deleted:** {deleted} | **Failed:** {failed}"
            )
            final_embed = embeds.create_success_embed("Web Database Sync Complete", summary_desc)
            
            if failed_rooms and failed <= 10:
                failed_list = "\n".join(failed_rooms)
                final_embed.add_field(name="⚠️ Failed Rooms", value=failed_list, inline=False)
            elif failed > 10:
                final_embed.add_field(name="⚠️ Failed Rooms", value="❌ Too many to list.", inline=False)
            
            # Add API stats if available
            stats = data.get('stats', {})
            if stats:
                stats_text = "\n".join([f"{k}: {v}" for k, v in stats.items()])
                final_embed.add_field(name="📊 API Stats", value=stats_text, inline=False)
            
            await interaction.followup.send(embed=final_embed)

        except aiohttp.ClientError as e:
            await interaction.followup.send(f"❌ Network error: {str(e)}")
        except Exception as e:
            await interaction.followup.send(f"❌ Sync failed: {str(e)}")


    @app_commands.command(name="apply_json", description="Migrate research JSON data to the room database")
    async def apply_json(self, interaction: discord.Interaction, json_file: discord.Attachment):
        """
        Migrate research data from a JSON file to the database.
        
        Args:
            json_file: JSON file with research data structured like research.json
        """
        await interaction.response.defer(ephemeral=True)
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        # Check if file is JSON
        if not json_file.filename.endswith('.json'):
            await interaction.followup.send("❌ Please provide a JSON file.", ephemeral=True)
            return
        
        try:
            # Download and parse the JSON file
            file_bytes = await json_file.read()
            file_content = file_bytes.decode('utf-8')
            research_data = json.loads(file_content)
            
            total_rooms = len(research_data)
            migrated = 0
            updated = 0
            failed = 0
            failed_rooms = []
            
            embed = discord.Embed(
                title="⏳ Migration Started",
                description=f"Starting migration of {total_rooms} rooms...",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            msg = await interaction.followup.send(embed=embed)

            datamanager.room_db_handler.clear_room_db()
            
            for room_name, room_info in research_data.items():
                try:
                    # Extract data from research.json format
                    picture_urls = room_info.get("images", [])
                    description = room_info.get("description", "")
                    tags = room_info.get("tags", [])
                    doc_by_user_id = room_info.get("documented_by", 0)
                    if room_info.get("redocumented_by"):
                        doc_by_user_id = room_info["redocumented_by"]
                    last_edited = room_info.get("last_edited", 0)

                    if room_info["pss"]: 
                        tags.append("pss")
                    if room_info["ss"]:
                        tags.append("ss")
                    
                    # Check if room already exists
                    existing_room = datamanager.room_db_handler.get_roominfo(room_name)
                    
                    # Document the room (create or update)
                    success = datamanager.room_db_handler.document_room(
                        room_name=room_name,
                        picture_urls=picture_urls,
                        description=description,
                        doc_by_user_id=doc_by_user_id,
                        tags=tags,
                        roomtype=room_info.get("roomtype", "Unknown - Please update!"),
                        timestamp=last_edited
                    )
                    
                    if success:
                        if existing_room:
                            updated += 1
                        else:
                            migrated += 1
                    else:
                        failed += 1
                        failed_rooms.append(room_name)
                            
                except Exception as e:
                    print(f"❌ Error migrating room '{room_name}': {e}")
                    failed += 1
                    failed_rooms.append(f"{room_name} ({str(e)})")
            
            # Send summary with emojis
            migration_desc = (
                f"**Total Rooms:** {total_rooms}\n"
                f"**Migrated:** {migrated} | **Updated:** {updated} | **Failed:** {failed}"
            )
            final_embed = embeds.create_success_embed("Migration Complete", migration_desc)
            
            if failed_rooms and failed <= 10:
                failed_list = "\n".join(failed_rooms)
                final_embed.add_field(name="⚠️ Failed Rooms", value=failed_list, inline=False)
            elif failed > 10:
                final_embed.add_field(name="⚠️ Failed Rooms", value="❌ Too many to list.", inline=False)
            
            await interaction.followup.send(embed=final_embed)

        except json.JSONDecodeError as e:
            await interaction.followup.send(f"❌ Error: Invalid JSON format. {str(e)}")
        except Exception as e:
            await interaction.followup.send(f"❌ Migration failed: {str(e)}")

    
    @app_commands.command(name="get_room_json", description="Json representation of the room database")
    async def get_room_json(self, interaction: discord.Interaction):
        """
        Get the JSON representation of the room database.
        """
        await interaction.response.defer(ephemeral=True)
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        room_data = datamanager.room_db_handler.jsonify_room_db()
        
        # Send room data as a json file
        json_file = discord.File(fp=io.BytesIO(json.dumps(room_data, indent=4).encode()), filename="room_data.json")
        await interaction.followup.send(file=json_file, ephemeral=True)
    
    @app_commands.command(name="get_room_db", description="Get the raw database file")
    async def get_db(self, interaction: discord.Interaction):
        """
        Get the raw database file.
        """
        await interaction.response.defer(ephemeral=True)
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        db_path = datamanager.room_db_handler.DB_PATH
        db_file = discord.File(fp=open(db_path, 'rb'), filename="frd_bot_database.db")
        await interaction.followup.send(file=db_file, ephemeral=True)

    @app_commands.command(name="reset_room_db", description="Reset the room database (deletes all data)")
    async def reset_db(self, interaction: discord.Interaction):
        """
        Reset the room database (deletes all data).
        """
        await interaction.response.defer(ephemeral=True)
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        datamanager.room_db_handler.clear_room_db()
        await interaction.followup.send("✅ Room database has been reset.", ephemeral=True)
    
    @app_commands.command(name="reset_server_profiles", description="Reset all server profiles (deletes all server data)")
    async def reset_server_profiles(self, interaction: discord.Interaction):
        """
        Reset all server profiles (deletes all server data).
        """
        await interaction.response.defer(ephemeral=True)
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        datamanager.server_db_handler.clear_server_profiles()
        await interaction.followup.send("✅ All server profiles have been reset.", ephemeral=True)
    
    @app_commands.command(name="check_invalid_urls", description="Check for rooms with invalid image URLs (file paths)")
    async def check_invalid_urls(self, interaction: discord.Interaction):
        """
        Check for rooms with invalid image URLs (file paths instead of HTTP URLs).
        """
        await interaction.response.defer(ephemeral=True)
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        # Get all rooms
        all_rooms = datamanager.room_db_handler.get_all_room_names()
        
        invalid_rooms = []
        for room_name in all_rooms:
            room_data = datamanager.room_db_handler.get_roominfo(room_name)
            if not room_data:
                continue
            
            picture_urls = room_data.get("picture_urls", [])
            valid_urls = [url for url in picture_urls if url.startswith(("http://", "https://"))]
            invalid_urls = [url for url in picture_urls if not url.startswith(("http://", "https://"))]
            
            if len(invalid_urls) > 0:
                invalid_rooms.append({
                    "name": room_name,
                    "total": len(picture_urls),
                    "valid": len(valid_urls),
                    "invalid": len(invalid_urls),
                    "invalid_urls": invalid_urls
                })
        
        if not invalid_rooms:
            await interaction.followup.send("✅ All rooms have valid HTTP(S) URLs!", ephemeral=True)
            return
        
        # Create embeds in chunks (10 fields per embed to avoid hitting limits)
        embeds_to_send = []
        current_embed = discord.Embed(
            title="🔍 Rooms with Invalid URLs",
            description=f"Found {len(invalid_rooms)} room(s) with invalid image URLs (file paths)",
            color=discord.Color.orange()
        )
        fields_in_current = 0
        
        for room in invalid_rooms:
            # Truncate URLs if too long
            invalid_urls_str = "\n".join([f"`{url[:80]}{'...' if len(url) > 80 else ''}`" for url in room['invalid_urls']])
            
            field_value = f"Valid: {room['valid']}/{room['total']} | Invalid: {room['invalid']}\n{invalid_urls_str}"
            
            # Check if adding this field would exceed embed limits
            if fields_in_current >= 10 or len(current_embed) + len(field_value) > 5800:
                embeds_to_send.append(current_embed)
                current_embed = discord.Embed(
                    title="🔍 Rooms with Invalid URLs (continued)",
                    color=discord.Color.orange()
                )
                fields_in_current = 0
            
            current_embed.add_field(
                name=f"🗂️ {room['name']}",
                value=field_value,
                inline=False
            )
            fields_in_current += 1
        
        # Add the last embed if it has fields
        if fields_in_current > 0:
            embeds_to_send.append(current_embed)
        
        # Send first embed as followup
        if embeds_to_send:
            await interaction.followup.send(embed=embeds_to_send[0], ephemeral=True)
            
            # Send remaining embeds as separate messages
            for embed in embeds_to_send[1:]:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="room_data", description="Get data for a specific room as a json file")
    async def room_data(self, interaction: discord.Interaction, room_name: str):
        """
        Get data for a specific room as a json file.
        """
        await interaction.response.defer(ephemeral=True)
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        room_data = datamanager.room_db_handler.get_roominfo(room_name)
        if not room_data:
            await interaction.followup.send(f"❌ Room '{room_name}' not found in the database.", ephemeral=True)
            return
        
        # Send room data as a json file
        json_file = discord.File(fp=io.BytesIO(json.dumps(room_data, indent=4).encode()), filename=f"{room_name}_data.json")
        await interaction.followup.send(file=json_file, ephemeral=True)
    
    @app_commands.command(name="upload_images", description="Upload images to R2 for a specific room")
    @app_commands.describe(
        room_name="Name of the room (determines upload path)",
        image1="First image",
        image2="Second image",
        image3="Third image",
        image4="Fourth image",
        image5="Fifth image (optional)",
        image6="Sixth image (optional)",
        image7="Seventh image (optional)",
        image8="Eighth image (optional)",
        image9="Ninth image (optional)",
        image10="Tenth image (optional)"
    )
    async def upload_images(
        self,
        interaction: discord.Interaction,
        room_name: str,
        image1: discord.Attachment,
        image2: discord.Attachment,
        image3: discord.Attachment,
        image4: discord.Attachment,
        image5: Optional[discord.Attachment] = None,
        image6: Optional[discord.Attachment] = None,
        image7: Optional[discord.Attachment] = None,
        image8: Optional[discord.Attachment] = None,
        image9: Optional[discord.Attachment] = None,
        image10: Optional[discord.Attachment] = None
    ):
        """Upload images to R2 storage for a specific room. Generates the correct CDN URLs."""
        await interaction.response.defer(ephemeral=True)
        
        level = await _helpers.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        # Collect all images
        images = [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10]
        images = [img for img in images if img is not None]
        
        # Upload each image to R2
        uploaded_urls = []
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for i, img in enumerate(images, 1):
                try:
                    # Download image
                    async with session.get(img.url) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            
                            # Upload to R2
                            r2_url = await _r2_handler.upload_to_r2(data, room_name, i)
                            if r2_url:
                                uploaded_urls.append(r2_url)
                                print(f"[UPLOAD] ✅ Uploaded image {i} for '{room_name}': {r2_url}")
                            else:
                                print(f"[UPLOAD] ❌ Failed to upload image {i} for '{room_name}'")
                        else:
                            print(f"[UPLOAD] ❌ Failed to download image {i}: Status {resp.status}")
                except Exception as e:
                    print(f"[UPLOAD] ❌ Error processing image {i}: {e}")
        
        if not uploaded_urls:
            await interaction.followup.send("❌ Failed to upload any images.", ephemeral=True)
            return
        
        # Create embed with results
        embed = discord.Embed(
            title="✅ Images Uploaded to R2",
            description=f"Uploaded {len(uploaded_urls)} image(s) for room `{room_name}`",
            color=discord.Color.green()
        )
        
        urls_text = "\n".join([f"{i}. `{url}`" for i, url in enumerate(uploaded_urls, 1)])
        embed.add_field(name="CDN URLs", value=urls_text, inline=False)
        embed.set_footer(text="These URLs can be used to replace invalid file paths in the database")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

shared.FRD_bot.tree.add_command(Admin())