# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Research Commands

PRINT_PREFIX = "ROOM COMMANDS"

# Standard library imports
from typing import Optional

# Third-party imports
import discord
from discord import app_commands

# Local imports
from config.vars import RoomType, Tags
from src import shared
from src.datamanager.db_handlers import room_db_handler
from src.utils import embeds

class RoomCommands(app_commands.Group):
    """Commands related to room searching and information."""
    def __init__(self):
        super().__init__(name="room", description="Commands related to room searching and information.")
    
    @app_commands.command(name="info", description="Get information about a specific room.")
    @app_commands.describe(room_name="The name of the room to get information about.")
    async def room_info(self, interaction: discord.Interaction, room_name: str):
        """Fetch and display information about a specific room."""
        print(f"[INFO] [{PRINT_PREFIX}] Room info requested for '{room_name}' by {interaction.user}")
        await interaction.response.defer()
        
        room = room_db_handler.get_roominfo(room_name)
        if not room:
            embed = embeds.create_error_embed("Room Not Found", f"No information found for room: **{room_name}**")
            await interaction.followup.send(embed=embed)
            return
        
        embed, images = await embeds.send_room_documentation_embed(interaction.channel, room, return_embed=True)
        await interaction.followup.send(embed=embed, files=images)
    
    @app_commands.command(name="search", description="Search for rooms by name.")
    @app_commands.describe(name="The search query for room names.", tag="Tag to filter rooms by.", roomtype="Type of room to filter by.")
    async def room_search(self, interaction: discord.Interaction, name: Optional[str] = None, tag: Optional[Tags] = None, roomtype: Optional[RoomType] = None):
        """Search for rooms by name."""
        print(f"[INFO] [{PRINT_PREFIX}] Room search by {interaction.user} - name:{name}, tag:{tag}, type:{roomtype}")
        await interaction.response.defer()
        
        if not name and not tag and not roomtype:
            r_embed = embeds.create_error_embed("Invalid Search", "Please provide at least one search parameter: name, tag, or roomtype.")
            await interaction.followup.send(embed=r_embed)
            return
        if name:
            name_result = room_db_handler.search_rooms_by_name(name)
        
        if tag:
            tag_result = room_db_handler.search_rooms_by_tag(tag)

        if roomtype:
            type_result = room_db_handler.search_rooms_by_roomtype(roomtype)

        search_type = ""

        # Only show rooms that match all provided criteria
        if name and tag and roomtype:
            results = [room for room in name_result if room in tag_result and room in type_result]
            search_type = "tag & type & name"
        elif name and tag:
            results = [room for room in name_result if room in tag_result]
            search_type = "tag & name"
        elif name and roomtype:
            results = [room for room in name_result if room in type_result]
            search_type = "type & name"
        elif tag and roomtype:
            results = [room for room in tag_result if room in type_result]
            search_type = "tag & type"
        elif name:
            results = name_result
            search_type = "name"
        elif tag:
            results = tag_result
            search_type = "tag"
        elif roomtype:
            results = type_result
            search_type = "type"

        query_parts = []
        if name:
            query_parts.append(name)
        if tag:
            query_parts.append(f"Tag: {tag}")
        if roomtype:
            query_parts.append(f"Type: {roomtype}")
        query = ", ".join(query_parts)
    
        if not results:
            r_embed = embeds.create_error_embed("No Results", f"No rooms found matching your query: **{query}**")
            await interaction.followup.send(embed=r_embed)
            return
        
        
        result_embeds = embeds.create_search_result_embed(search_type, query, results, interaction.guild_id)
        result_embeds = result_embeds[:20]  # Limit to 20 embeds
        first_embed = result_embeds.pop(0)
        await interaction.followup.send(embed=first_embed)
        for embed in result_embeds:
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="history", description="View the edit history of a room.")
    @app_commands.describe(room_name="The name of the room to view history for.")
    async def room_history(self, interaction: discord.Interaction, room_name: str):
        """View the edit history of a room."""
        print(f"[INFO] [{PRINT_PREFIX}] Room history requested for '{room_name}' by {interaction.user}")
        await interaction.response.defer()
        
        room = room_db_handler.get_roominfo(room_name)
        if not room:
            embed = embeds.create_error_embed("Room Not Found", f"No information found for room: **{room_name}**")
            await interaction.followup.send(embed=embed)
            return
        
        history_embeds = embeds.create_edit_history_embed(room_name, room)
        history_embeds = history_embeds[:20]  # Limit to 20 embeds
        first_embed = history_embeds.pop(0)
        await interaction.followup.send(embed=first_embed)
        for embed in history_embeds:
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="bug_report", description="Report an issue with a room.")
    @app_commands.describe(room_name="The name of the room to report an issue for.", issue_description="Description of the issue encountered. Be detailed (30-1000 characters).")
    async def room_bug_report(self, interaction: discord.Interaction, room_name: str, issue_description: str):
        """Report an issue with a room."""
        print(f"[INFO] [{PRINT_PREFIX}] Room bug report for '{room_name}' by {interaction.user}")
        await interaction.response.defer()

        issue_description = issue_description[:1000]  # Limit to 1000 characters

        if len(issue_description) < 30:
            embed = embeds.create_error_embed("Issue Description Too Short", "Please provide a more detailed description of the issue (at least 30 characters).")
            await interaction.followup.send(embed=embed)
            return
        
        room = room_db_handler.get_roominfo(room_name)
        if not room:
            embed = embeds.create_error_embed("Room Not Found", f"No information found for room: **{room_name}**")
            await interaction.followup.send(embed=embed)
            return
        
        success, id = room_db_handler.report_room_bug(room_name=room_name, report_text=issue_description, reported_by_user_id=interaction.user.id)
        if not success:
            embed = embeds.create_error_embed("Report Failed", "An error occurred while submitting your bug report. Please try again later.")
            await interaction.followup.send(embed=embed)
            return
        embed = embeds.create_success_embed("Bug Report Submitted", f"Your bug report for room **{room_name}** has been stored with ID: `{id}`.")
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="view_room_reports", description="View bug reports for a specific room.")
    @app_commands.describe(room_name="The name of the room to view bug reports for.")
    async def view_room_reports(self, interaction: discord.Interaction, room_name: str):
        """View bug reports for a specific room."""
        print(f"[INFO] [{PRINT_PREFIX}] View room reports for '{room_name}' by {interaction.user}")
        await interaction.response.defer()
        
        room = room_db_handler.get_roominfo(room_name)
        if not room:
            embed = embeds.create_error_embed("Room Not Found", f"No information found for room: **{room_name}**")
            await interaction.followup.send(embed=embed)
            return
        
        reports = room_db_handler.get_room_bug_reports(room_name)
        if not reports:
            embed = embeds.create_error_embed("No Reports Found", f"No bug reports found for room: **{room_name}**")
            await interaction.followup.send(embed=embed)
            return
        
        report_embeds = embeds.create_bug_report_embed(room_name, reports, room_data=room)
        report_embeds = report_embeds[:20]  # Limit to 20 embeds
        first_embed = report_embeds.pop(0)
        await interaction.followup.send(embed=first_embed)
        for embed in report_embeds:
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="view_all_reports", description="View all bug reports across all rooms.")
    async def view_all_reports(self, interaction: discord.Interaction, include_resolved: Optional[bool] = True):
        """View all bug reports."""
        print(f"[INFO] [{PRINT_PREFIX}] View all bug reports by {interaction.user}")
        await interaction.response.defer()
        
        reports = room_db_handler.get_all_bug_reports(include_resolved=include_resolved)
        if not reports:
            embed = embeds.create_error_embed("No Reports Found", "No unresolved bug reports found.")
            await interaction.followup.send(embed=embed)
            return
        
        report_embeds = embeds.create_all_bug_reports_embed(reports)
        report_embeds = report_embeds[:20]  # Limit to 20 embeds
        first_embed = report_embeds.pop(0)
        await interaction.followup.send(embed=first_embed)
        for embed in report_embeds:
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="view_report", description="View a specific bug report by its ID.")
    @app_commands.describe(report_id="The ID of the bug report to view.")
    async def view_report(self, interaction: discord.Interaction, report_id: int):
        """View a specific bug report by its ID."""
        print(f"[INFO] [{PRINT_PREFIX}] View bug report #{report_id} by {interaction.user}")
        await interaction.response.defer()
        
        report = room_db_handler.get_bug_report(report_id)
        if not report:
            embed = embeds.create_error_embed("Report Not Found", f"No bug report found with ID: **{report_id}**")
            await interaction.followup.send(embed=embed)
            return
        
        report_embed = embeds.create_single_bug_report_embed(report)
        await interaction.followup.send(embed=report_embed)
    





shared.FRD_bot.tree.add_command(RoomCommands())
