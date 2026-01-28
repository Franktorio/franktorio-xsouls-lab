# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Admin commands

PRINT_PREFIX = "DEV COMMANDS"

# Standard library imports
import asyncio
import io
import json
import os
from typing import Optional

# Third-party imports
import discord
from discord import app_commands

# Local imports
import config.vars as vars
from src import datamanager, shared
from src.utils import r2_handler
from src.utils import embeds, utils

class Admin(app_commands.Group):
    def __init__(self):
        super().__init__(name="dev", description="Developer only commands")

    @app_commands.command(name="restart", description="Shut down the bot and service will turn it on automatically.")
    async def restart_bot(self, interaction: discord.Interaction):
        """Restart the bot (shuts down, service will restart it)."""
        await interaction.response.defer()
        
        print(f"[INFO] [{PRINT_PREFIX}] Restart command invoked by {interaction.user}")
        
        level = await utils.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
            return
        
        embed = embeds.create_success_embed(
            title="Bot Restarting",
            description="The bot is restarting now. It will be back online shortly."
        )
        await interaction.followup.send(embed=embed)
        
        print(f"[INFO] [{PRINT_PREFIX}] Shutting down bot for restart")
        
        # Shutdown the bot
        await shared.FRD_bot.close()
        os._exit(0)

    @app_commands.command(name="room_reset", description="Delete the room documentation across all servers. The build_documented task will re-send it later.")
    async def room_reset(self, interaction: discord.Interaction, room_name: str):
        """Global reset a room across all servers."""
        await interaction.response.defer()
        
        print(f"[INFO] [{PRINT_PREFIX}] Room reset invoked by {interaction.user} for room '{room_name}'")
        
        level = await utils.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
            return
        
        room_profile = datamanager.room_db_handler.get_roominfo(room_name)
        if not room_profile:
            embed = embeds.create_error_embed(
                title="Room Not Found",
                description=f"The room '{room_name}' does not exist in the database."
            )
            await interaction.followup.send(embed=embed)
            return
        
        await utils.global_reset(room_name)

        embed = embeds.create_success_embed(
            title="Room Reset Complete",
            description=f"The room '{room_name}' has been reset across all servers."
        )
        await interaction.followup.send(embed=embed)
        print(f"[INFO] [{PRINT_PREFIX}] Room '{room_name}' reset complete across all servers")

    @app_commands.command(name="global_reset_documented", description="Bulk deletes every message in the documented channel across all servers.")
    async def global_reset_documented(self, interaction: discord.Interaction):
        """Bulk deletes every message in the documented channel across all servers."""
        await interaction.response.defer()
        
        print(f"[INFO] [{PRINT_PREFIX}] Global reset documented invoked by {interaction.user}")
        
        level = await utils.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
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
                
                print(f"[INFO] [{PRINT_PREFIX}] Clearing documented channel in guild {guild.name} ({guild.id})")
                deleted = await channel.purge(check=is_bot_message, limit=None)
                datamanager.server_db_handler.clear_doc_ids(guild.id)
                print(f"[INFO] [{PRINT_PREFIX}] Cleared {len(deleted)} messages in guild {guild.name}")
                return len(deleted)
            except Exception as e:
                print(f"[ERROR] [{PRINT_PREFIX}] Failed to clear documented channel in guild {guild.name} ({guild.id}): {e}")
                failed_servers.append(guild.name)
                return 0

        # Run all guild clears concurrently
        tasks = [clear_guild_channel(guild) for guild in shared.FRD_bot.guilds]
        results = await asyncio.gather(*tasks)
        total_deleted = sum(results)

        embed_desc = f"Successfully deleted a total of {total_deleted} messages from documented channels across {len(shared.FRD_bot.guilds)} server(s)."
        if failed_servers:
            embed_desc += f"\nFailed to clear documented channels in the following servers: {', '.join(failed_servers)}"

        embed = embeds.create_success_embed(
            title="Global Documented Channel Reset Complete",
            description=embed_desc
        )
        print(f"[INFO] [{PRINT_PREFIX}] Global documented reset complete: {total_deleted} messages deleted")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="cache_all_rooms", description="Cache all rooms from the database to R2")
    async def cache_all_rooms(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        print(f"[INFO] [{PRINT_PREFIX}] Cache all rooms invoked by {interaction.user}")
        
        level = await utils.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
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
            embed.add_field(name="Cached", value=str(cached_rooms), inline=False)
            embed.add_field(name="Failed", value=str(cached_failed_rooms), inline=False)
            embed.add_field(name="Progress", value=f"{((cached_rooms+cached_failed_rooms)/total_rooms)*100:.2f}%", inline=False)
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
            title="Caching Started",
            description=f"Starting caching of {total_rooms} rooms from database.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        await interaction.followup.send(embed=r_embed)
        
        print(f"[INFO] [{PRINT_PREFIX}] Starting cache loop for {total_rooms} rooms")

        for room_name in rooms:
            room_info = datamanager.room_db_handler.get_roominfo(room_name)
            image_urls = room_info.get('picture_urls', [])

            try:
                edit_cd += 1
                if edit_cd >= 100:
                    message_id = await _edit_or_send_embed(message_id)
                    edit_cd = 0
            except Exception as e:
                print(f"[ERROR] [{PRINT_PREFIX}] Error updating cache progress message: {e}")

            cache_failed = False
            for url in image_urls:

                path = await r2_handler.get_cached_image_path(url)
                
        
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
            final_embed.add_field(name="Failed Rooms", value=", ".join(failed_rooms), inline=False)
        elif cached_failed_rooms > 10:
            final_embed.add_field(name="Failed Rooms", value="Too many to list.", inline=False)

        print(f"[INFO] [{PRINT_PREFIX}] Cache complete: {cached} cached, {failed} failed")
        
        msg = await channel.fetch_message(message_id)
        await msg.edit(embed=final_embed)

    
    @app_commands.command(name="get_room_json", description="Json representation of the room database")
    async def get_room_json(self, interaction: discord.Interaction):
        """
        Get the JSON representation of the room database.
        """
        await interaction.response.defer(ephemeral=True)
        
        print(f"[INFO] [{PRINT_PREFIX}] Get room JSON requested by {interaction.user}")
        
        level = await utils.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
            return
        
        room_data = datamanager.room_db_handler.jsonify_room_db()
        
        # Send room data as a json file
        json_file = discord.File(fp=io.BytesIO(json.dumps(room_data, indent=4).encode()), filename="frd_room_db.json")
        print(f"[INFO] [{PRINT_PREFIX}] Room database JSON exported to {interaction.user}")
        await interaction.followup.send(file=json_file, ephemeral=True)
    
    @app_commands.command(name="get_room_db", description="Get the raw database file")
    async def get_room_db(self, interaction: discord.Interaction):
        """
        Get the raw database file.
        """
        await interaction.response.defer(ephemeral=True)
        
        print(f"[INFO] [{PRINT_PREFIX}] Get room DB requested by {interaction.user}")
        
        level = await utils.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
            return
        
        db_path = datamanager.room_db_handler.DB_PATH
        # Read file content into memory to avoid keeping file descriptor open
        with open(db_path, 'rb') as f:
            file_data = f.read()
        db_file = discord.File(fp=io.BytesIO(file_data), filename="frd_room.db")
        print(f"[INFO] [{PRINT_PREFIX}] Room database file exported to {interaction.user}")
        await interaction.followup.send(file=db_file, ephemeral=True)
    

    @app_commands.command(name="room_data", description="Get data for a specific room as a json file")
    async def room_data(self, interaction: discord.Interaction, room_name: str):
        """
        Get data for a specific room as a json file.
        """
        await interaction.response.defer(ephemeral=True)
        
        print(f"[INFO] [{PRINT_PREFIX}] Room data requested for '{room_name}' by {interaction.user}")
        
        level = await utils.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
            return
        
        room_data = datamanager.room_db_handler.get_roominfo(room_name)
        if not room_data:
            await interaction.followup.send(f"Room '{room_name}' not found in the database.", ephemeral=True)
            return
        
        # Send room data as a json file
        json_file = discord.File(fp=io.BytesIO(json.dumps(room_data, indent=4).encode()), filename=f"{room_name}_data.json")
        print(f"[INFO] [{PRINT_PREFIX}] Room data for '{room_name}' exported to {interaction.user}")
        await interaction.followup.send(file=json_file, ephemeral=True)

    @app_commands.command(name="purge_scanner_db", description="Purge all data from the scanner database.")
    @app_commands.describe(confirm="Type CONFIRM to confirm purging the scanner database.")
    async def purge_scanner_db(self, interaction: discord.Interaction, confirm: Optional[str] = None):
        """
        Purge all data from the scanner database.
        """
        await interaction.response.defer(ephemeral=True)
        
        print(f"[INFO] [{PRINT_PREFIX}] Purge scanner database requested by {interaction.user}")
        
        level = await utils.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
            return
        
        if confirm != "CONFIRM":
            await interaction.followup.send("To confirm purging the scanner database, please add `confirm=CONFIRM` to the command.", ephemeral=True)
            return
        
        datamanager.scanner_db_handler.purge_database()
        await interaction.followup.send("Scanner database purged successfully.", ephemeral=True)
        print(f"[INFO] [{PRINT_PREFIX}] Scanner database purged by {interaction.user}")

    @app_commands.command(name="migrate_cdn_to_webp", description="Migrate all non-WebP images in R2 to WebP format.")
    @app_commands.describe(confirm="Type CONFIRM to start the migration.")
    async def migrate_cdn_to_webp(self, interaction: discord.Interaction, confirm: Optional[str] = None):
        """
        Migrate all non-WebP images in the R2 bucket to WebP format.
        This will download each image, convert it to WebP, re-upload, and delete the original.
        """
        await interaction.response.defer()
        
        print(f"[INFO] [{PRINT_PREFIX}] CDN WebP migration requested by {interaction.user}")
        
        level = await utils.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("You do not have permission to use this command.")
            return
        
        if confirm != "CONFIRM":
            await interaction.followup.send("To confirm migrating the CDN to WebP, please add `confirm=CONFIRM` to the command.")
            return
        
        # Send initial message
        await interaction.followup.send("Starting CDN migration to WebP format... This may take a while.")
        
        # Run the migration
        stats = await r2_handler.migrate_cdn_to_webp()
        
        # Send results
        if "error" in stats:
            embed = embeds.create_error_embed(
                title="Migration Failed",
                description=f"Error: {stats['error']}"
            )
        else:
            # Update room database URLs
            url_mappings = stats.get("url_mappings", {})
            rooms_updated = 0
            
            if url_mappings:
                # Get all room names
                room_names = datamanager.room_db_handler.get_all_room_names()
                
                for room_name in room_names:
                    room_data = datamanager.room_db_handler.get_roominfo(room_name)
                    if not room_data:
                        continue
                    
                    picture_urls = room_data.get("picture_urls", [])
                    updated_urls = []
                    changed = False
                    
                    for url in picture_urls:
                        if url in url_mappings:
                            updated_urls.append(url_mappings[url])
                            changed = True
                        else:
                            updated_urls.append(url)
                    
                    # Update if any URLs changed
                    if changed:
                        datamanager.room_db_handler.replace_imgs(room_name, updated_urls)
                        rooms_updated += 1
                        print(f"[INFO] [{PRINT_PREFIX}] Updated URLs for room: {room_name}")
            
            embed = embeds.create_success_embed(
                title="CDN Migration Complete",
                description=f"**Total images:** {stats['total']}\n"
                           f"**Converted:** {stats['converted']}\n"
                           f"**Skipped (already WebP):** {stats['skipped']}\n"
                           f"**Failed:** {stats['failed']}\n"
                           f"**Rooms updated:** {rooms_updated}"
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"[INFO] [{PRINT_PREFIX}] CDN migration completed by {interaction.user}: {stats}")

    @app_commands.command(name="fix_webp_urls", description="Update all database URLs to use .webp extensions.")
    @app_commands.describe(confirm="Type CONFIRM to update URLs.")
    async def fix_webp_urls(self, interaction: discord.Interaction, confirm: Optional[str] = None):
        """
        Update all room picture URLs in the database to use .webp extensions.
        This only updates the database, not the actual files in R2.
        """
        await interaction.response.defer(ephemeral=True)
        
        print(f"[INFO] [{PRINT_PREFIX}] Fix WebP URLs requested by {interaction.user}")
        
        level = await utils.permission_check(interaction.user)
        if level < 5:
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
            return
        
        if confirm != "CONFIRM":
            await interaction.followup.send("To confirm updating URLs, please add `confirm=CONFIRM` to the command.", ephemeral=True)
            return
        
        # Get all room names
        room_names = datamanager.room_db_handler.get_all_room_names()
        
        rooms_updated = 0
        total_urls_updated = 0
        
        for room_name in room_names:
            room_data = datamanager.room_db_handler.get_roominfo(room_name)
            if not room_data:
                continue
            
            picture_urls = room_data.get("picture_urls", [])
            updated_urls = []
            changed = False
            
            for url in picture_urls:
                # Replace extension with .webp
                if not url.lower().endswith('.webp'):
                    # Split URL and replace extension
                    base_url = url.rsplit('.', 1)[0] if '.' in url.split('/')[-1] else url
                    new_url = f"{base_url}.webp"
                    updated_urls.append(new_url)
                    changed = True
                    total_urls_updated += 1
                else:
                    updated_urls.append(url)
            
            # Update if any URLs changed
            if changed:
                datamanager.room_db_handler.replace_imgs(room_name, updated_urls)
                rooms_updated += 1
                print(f"[INFO] [{PRINT_PREFIX}] Updated URLs for room: {room_name}")
        
        embed = embeds.create_success_embed(
            title="WebP URLs Updated",
            description=f"**Rooms checked:** {len(room_names)}\n"
                       f"**Rooms updated:** {rooms_updated}\n"
                       f"**URLs changed:** {total_urls_updated}"
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"[INFO] [{PRINT_PREFIX}] Fixed WebP URLs: {rooms_updated} rooms, {total_urls_updated} URLs updated by {interaction.user}")

shared.FRD_bot.tree.add_command(Admin())