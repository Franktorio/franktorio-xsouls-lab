# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Management Commands (head researcher+ only commands)

PRINT_PREFIX = "MANAGEMENT COMMANDS"

# Standard library imports
from typing import Literal

# Third-party imports
import discord
from discord import app_commands

# Local imports
import config.vars as vars
from src import shared
from src.api import external_api
from src.tasks.sync_databases import sync_databases
from src.utils import utils
from src.utils.embeds import create_error_embed, create_success_embed
from src.utils import embeds
from src.datamanager.db_handlers import room_db_handler

FRD_bot = shared.FRD_bot

class Management(app_commands.Group):
    def __init__(self):
        super().__init__(name="management", description="Management commands")

    @app_commands.command(name="sync", description="Manually trigger database synchronization across servers.")
    async def sync_databases(self, interaction: discord.Interaction):
        """Manually trigger database synchronization across servers."""
        print(f"[{PRINT_PREFIX}] Manual database sync triggered by {interaction.user}")
        await interaction.response.defer()
        
        level = await utils.permission_check(interaction.user)
        if level < 4:
            embed = create_error_embed(title="Permission Denied", description="You do not have permission to use this command. You need to be a Head Researcher or higher.")
            await interaction.followup.send(embed=embed)
            return
        try:
            sync_databases.restart()
            embed = create_success_embed(title="Database Synchronization Triggered", description="Database synchronization across servers has been manually triggered.")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_error_embed(title="Synchronization Failed", description=f"An error occurred while triggering synchronization: {str(e)}")
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="role", description="Set the role of an user.")
    @app_commands.describe(user="The user to set the permission level for.", role="The permission role to assign.")
    async def set_permission_level(self, interaction: discord.Interaction, user: discord.User, role: Literal["Viewer", "Trial Researcher", "Novice Researcher", "Experienced Researcher", "Head Researcher"]):
        """Set the permission level of a user."""
        print(f"[{PRINT_PREFIX}] Set permission level for {user} to '{role}' by {interaction.user}")
        await interaction.response.defer()
        
        level = await utils.permission_check(interaction.user)
        if level < 4:
            embed = create_error_embed(title="Permission Denied", description="You do not have permission to use this command. You need to be a Head Researcher or higher.")
            await interaction.followup.send(embed=embed)
            return

        role_map = {
            "Viewer": None,
            "Trial Researcher": vars.TRIAL_RESEARCHER,
            "Novice Researcher": vars.NOVICE_RESEARCHER,
            "Experienced Researcher": vars.EXPERIENCED_RESEARCHER,
            "Head Researcher": vars.HEAD_RESEARCHER
        }

        guild = shared.FRD_bot.get_guild(vars.HOME_GUILD_ID)
        member = guild.get_member(user.id)
        if member is None:
            embed = create_error_embed(title="User Not Found", description="The specified user is not a member of the home server.")
            await interaction.followup.send(embed=embed)
            return

        # Remove all research roles first
        research_roles = [
            vars.TRIAL_RESEARCHER,
            vars.NOVICE_RESEARCHER,
            vars.EXPERIENCED_RESEARCHER,
            vars.HEAD_RESEARCHER
        ]
        
        for r_id in research_roles:
            r_role = guild.get_role(r_id)
            if r_role in member.roles:
                await member.remove_roles(r_role)

        # Assign new role if not Viewer
        if role_map[role]:
            new_role = guild.get_role(role_map[role])
            await member.add_roles(new_role)

        # Sync role to external API
        try:
            api_response = await external_api.set_user_role_api(user.id, role)
            if api_response.get("success"):
                embed = create_success_embed(title="Permission Level Updated", description=f"Set **{user}**'s permission level to **{role}** on both Discord and the web dashboard.")
            elif api_response.get("error") == "External data source is disabled":
                embed = create_success_embed(title="Permission Level Updated", description=f"Set **{user}**'s permission level to **{role}** on Discord.")
            else:
                embed = create_success_embed(title="Permission Level Partially Updated", description=f"Set **{user}**'s permission level to **{role}** on Discord, but failed to sync to web dashboard: {api_response.get('error')}\nPlease try again.")
        except Exception as e:
            embed = create_success_embed(title="Permission Level Partially Updated", description=f"Set **{user}**'s permission level to **{role}** on Discord, but failed to sync to web dashboard: {str(e)}\nPlease try again.")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="delete_report", description="Delete a bug report.")
    @app_commands.describe(report_id="The ID of the bug report to delete.")
    async def delete_report(self, interaction: discord.Interaction, report_id: int):
        """Delete a bug report (soft delete)."""
        print(f"[{PRINT_PREFIX}] Delete bug report #{report_id} by {interaction.user}")
        await interaction.response.defer()
        
        report = room_db_handler.get_bug_report(report_id)
        if not report:
            embed = embeds.create_error_embed("Report Not Found", f"No bug report found with ID: **{report_id}**")
            await interaction.followup.send(embed=embed)
            return
        
        if report['deleted']:
            embed = embeds.create_error_embed("Already Deleted", f"Bug report #{report_id} has already been deleted.")
            await interaction.followup.send(embed=embed)
            return
        
        success = room_db_handler.delete_bug_report(report_id)
        if success:
            embed = embeds.create_success_embed("Report Deleted", f"Bug report #{report_id} for room **{report['room_name']}** has been deleted.")
            await interaction.followup.send(embed=embed)
        else:
            embed = embeds.create_error_embed("Failed to Delete", f"Failed to delete bug report #{report_id}.")
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="resolve_report", description="Mark a bug report as resolved.")
    @app_commands.describe(report_id="The ID of the bug report to resolve.")
    async def resolve_report(self, interaction: discord.Interaction, report_id: int):
        """Mark a bug report as resolved."""
        print(f"[{PRINT_PREFIX}] Resolve bug report #{report_id} by {interaction.user}")
        await interaction.response.defer()
        
        report = room_db_handler.get_bug_report(report_id)
        if not report:
            embed = embeds.create_error_embed("Report Not Found", f"No bug report found with ID: **{report_id}**")
            await interaction.followup.send(embed=embed)
            return
        
        if report['resolved']:
            embed = embeds.create_error_embed("Already Resolved", f"Bug report #{report_id} is already marked as resolved.")
            await interaction.followup.send(embed=embed)
            return
        
        success = room_db_handler.mark_bug_report_resolved(report_id)
        if success:
            embed = embeds.create_success_embed("Report Resolved", f"Bug report #{report_id} for room **{report['room_name']}** has been marked as resolved.")
            await interaction.followup.send(embed=embed)
        else:
            embed = embeds.create_error_embed("Failed to Resolve", f"Failed to mark bug report #{report_id} as resolved.")
            await interaction.followup.send(embed=embed)

shared.FRD_bot.tree.add_command(Management())