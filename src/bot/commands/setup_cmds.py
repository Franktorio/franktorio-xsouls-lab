# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Server setup command

PRINT_PREFIX = "SETUP COMMANDS"

# Standard library imports
import asyncio

# Third-party imports
import discord
from discord import app_commands
from discord.ext import commands

# Local imports
import config
from src import datamanager, shared
from src.utils import embeds


class Setup(app_commands.Group):
    """Group for setup-related commands."""
    def __init__(self):
        super().__init__(name="setup", description="Setup and configuration commands.")

    def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the user has administrator permission."""
        return interaction.user.guild_permissions.administrator or interaction.user.id == config.vars.OWNER_ID

    @app_commands.command(name="init", description="Setup the bot in this server.")
    async def setup_init(self, interaction: discord.Interaction):
        """Setup command to initialize the bot in a server."""
        print(f"[INFO] [{PRINT_PREFIX}] Server setup initiated by {interaction.user} in {interaction.guild.name}")
        bot = shared.get_bot()
        
        await interaction.response.defer()

        # Check if server already has a profile
        server_id = interaction.guild.id
        profile = datamanager.server_db_handler.get_server_profile(server_id)

        if profile:
            # Ask for confirmation before overwriting
            embed = discord.Embed(
                title="Server Already Set Up",
                description=(
                    "This server is already set up with the bot. "
                    "Running setup again will forget the existing channels and rebuild them.\n\n"
                    "React with to confirm and proceed, or to cancel."
                ),
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Bot Website", value=f"https://franktorio.dev/frd-api/", inline=False)
            msg = await interaction.followup.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check(reaction, user):
                return (
                    user == interaction.user
                    and str(reaction.emoji) in ["✅", "❌"]
                    and reaction.message.id == msg.id
                )

            try:
                reaction, user = await bot.wait_for("reaction_add", check=check, timeout=15.0)
            except asyncio.TimeoutError:
                await msg.delete()
                return

            if str(reaction.emoji) == "❌":
                await msg.edit(content="Setup cancelled.")
                return
            else:
                await msg.edit(content="Re-initializing server setup.", embed=None)

        try:
            # Create a category for research channels
            category = await interaction.guild.create_category(
                "Franktorio & xSoul's Research Division", reason="FXL Bot Setup"
            )

            # Create channels: researched and leaderboard
            researched_channel = await interaction.guild.create_text_channel(
                "documented-rooms", reason="FXL Bot Setup",
                category=category
            )
            leaderboard_channel = await interaction.guild.create_text_channel(
                "research-leaderboard", reason="FXL Bot Setup",
                category=category
            )
            print(f"[INFO] [{PRINT_PREFIX}] Created setup channels in {interaction.guild.name}")
        except discord.Forbidden:
            embed = embeds.create_error_embed(
                "Permission Denied",
                "I don't have permission to create channels or categories. Please give me the 'Manage Channels' permission."
            )
            await interaction.followup.send(embed=embed)
            return
        except Exception as e:
            print(f"[ERROR] [{PRINT_PREFIX}] Error while creating setup channels: {e}")
            embed = embeds.create_error_embed(
                "Setup Failed",
                f"An error occurred while creating channels: {str(e)}"
            )
            await interaction.followup.send(embed=embed)
            return

        # Make @everyone unable to send messages in these channels
        # But ensure the bot itself can send messages
        try:
            await researched_channel.set_permissions(
                interaction.guild.default_role,
                send_messages=False,
                reason="FRD Bot Setup"
            )
            await researched_channel.set_permissions(
                interaction.guild.me,
                send_messages=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                reason="FRD Bot Setup - Bot permissions"
            )
            await leaderboard_channel.set_permissions(
                interaction.guild.default_role,
                send_messages=False,
                reason="FRD Bot Setup"
            )
            await leaderboard_channel.set_permissions(
                interaction.guild.me,
                send_messages=True,
                embed_links=True,
                read_message_history=True,
                reason="FRD Bot Setup - Bot permissions"
            )
            print(f"[INFO] [{PRINT_PREFIX}] Set channel permissions in {interaction.guild.name}")
        except discord.Forbidden:
            embed = embeds.create_error_embed(
                "Permission Denied",
                "I don't have permission to set channel permissions. Please give me the 'Manage Permissions' permission."
            )
            await interaction.followup.send(embed=embed)
            return

        # Create or update server profile in the database
        # Clear old doc_msg_ids when re-initializing to avoid trying to update deleted messages
        datamanager.server_db_handler.create_server_profile(
            server_id=server_id,
            documented_channel_id=researched_channel.id,
            leaderboard_channel_id=leaderboard_channel.id,
            doc_msg_ids={}  # Clear old message IDs when recreating channels
        )
        
        embed = embeds.create_success_embed(
            "Setup Complete",
            (
                "The bot has been successfully set up in this server!\n\n"
                f"Research Channel: {researched_channel.mention}\n"
                f"Leaderboard Channel: {leaderboard_channel.mention}\n\n"
                "Building documentation channel now. This may take a few hours depending on the number of rooms."
            )
        )
        
        print(f"[INFO] [{PRINT_PREFIX}] Setup complete for {interaction.guild.name}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="leaderboard", description="Reset and rebuild the research leaderboard.")
    async def reset_leaderboard(self, interaction: discord.Interaction):
        """Reset and rebuild the research leaderboard."""
        print(f"[INFO] [{PRINT_PREFIX}] Reset leaderboard by {interaction.user} in {interaction.guild.name}")
        await interaction.response.defer()
        
        try:
            profile = datamanager.server_db_handler.get_server_profile(interaction.guild.id)

            if not profile:
                await interaction.followup.send(
                    "This server is not set up yet. Please run `/setup init` first.",
                    ephemeral=True
                )
                return
            
            # Try to delete previous leaderboard message if it exists
            channel = interaction.guild.get_channel(profile.get('leaderboard_channel_id'))
            if channel:
                try:
                    await channel.delete(reason="/setup leaderboard command issued.")
                except discord.Forbidden:
                    embed = embeds.create_error_embed(
                        "Permission Denied",
                        "I don't have permission to delete the old leaderboard channel. Please give me the 'Manage Channels' permission."
                    )
                    await interaction.followup.send(embed=embed)
                    return
                except Exception as e:
                    print(f"[{PRINT_PREFIX}] Error while trying to delete leaderboard channel: {e}")

            try:
                new_channel = await interaction.guild.create_text_channel(
                    "research-leaderboard", reason="/setup leaderboard command issued.",
                    category=channel.category if channel else None
                )
                
                # Set permissions: deny @everyone, allow bot
                await new_channel.set_permissions(
                    interaction.guild.default_role,
                    send_messages=False,
                    reason="/setup leaderboard command issued."
                )
                await new_channel.set_permissions(
                    interaction.guild.me,
                    send_messages=True,
                    embed_links=True,
                    read_message_history=True,
                    reason="Bot permissions for leaderboard channel"
                )
            except discord.Forbidden:
                embed = embeds.create_error_embed(
                    "Permission Denied",
                    "I don't have permission to create or configure channels. Please give me the 'Manage Channels' and 'Manage Permissions' permissions."
                )
                await interaction.followup.send(embed=embed)
                return

            datamanager.server_db_handler.set_leaderboard_channel(
                server_id=interaction.guild.id,
                channel_id=new_channel.id
            )

            embed = embeds.create_success_embed(
                "Leaderboard Reset",
                (
                    "The research leaderboard has been reset and a new channel has been created:\n"
                    f"{new_channel.mention}\n\n"
                )
            )
            embed.add_field(name="Bot Website", value=f"https://franktorio.dev/frd-api/", inline=False)
            print(f"[INFO] [{PRINT_PREFIX}] Leaderboard reset complete for {interaction.guild.name}")
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            embed = embeds.create_error_embed(
                "Leaderboard Reset Failed",
                f"An unexpected error occurred: {str(e)}"
            )
            await interaction.followup.send(embed=embed)
            print(f"[ERROR] [{PRINT_PREFIX}] Error in reset_leaderboard: {e}")

    @app_commands.command(name="documented", description="Reset and rebuild the research documentation channel.")
    async def reset_documented(self, interaction: discord.Interaction):
        """Reset and rebuild the research documentation channel."""
        print(f"[INFO] [{PRINT_PREFIX}] Reset documented channel by {interaction.user} in {interaction.guild.name}")
        await interaction.response.defer()
        
        try:
            profile = datamanager.server_db_handler.get_server_profile(interaction.guild.id)

            if not profile:
                await interaction.followup.send(
                    "This server is not set up yet. Please run `/setup init` first.",
                    ephemeral=True
                )
                return
            
            # Try to delete previous documented channel if it exists
            channel = interaction.guild.get_channel(profile.get('documented_channel_id'))
            if channel:
                try:
                    await channel.delete(reason="/setup documented command issued.")
                except discord.Forbidden:
                    embed = embeds.create_error_embed(
                        "Permission Denied",
                        "I don't have permission to delete the old documented channel. Please give me the 'Manage Channels' permission."
                    )
                    await interaction.followup.send(embed=embed)
                    return
                except Exception as e:
                    print(f"[ERROR] [{PRINT_PREFIX}] Error while trying to delete documented channel: {e}")

            try:
                new_channel = await interaction.guild.create_text_channel(
                    "documented-rooms", reason="/setup documented command issued.",
                    category=channel.category if channel else None
                )

                # Set permissions: deny @everyone, allow bot
                await new_channel.set_permissions(
                    interaction.guild.default_role,
                    send_messages=False,
                    reason="/setup documented command issued."
                )
                await new_channel.set_permissions(
                    interaction.guild.me,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    read_message_history=True,
                    reason="Bot permissions for documented channel"
                )
            except discord.Forbidden:
                embed = embeds.create_error_embed(
                    "Permission Denied",
                    "I don't have permission to create or configure channels. Please give me the 'Manage Channels' and 'Manage Permissions' permissions."
                )
                await interaction.followup.send(embed=embed)
                return

            datamanager.server_db_handler.set_documented_channel(
                server_id=interaction.guild.id,
                channel_id=new_channel.id
            )

            datamanager.server_db_handler.clear_doc_ids(
                server_id=interaction.guild.id
            )

            embed = embeds.create_success_embed(
                "Documented Channel Reset",
                (
                    "The research documentation channel has been reset and a new channel has been created:\n"
                    f"{new_channel.mention}\n\n"
                    "Building documentation channel now. This may take a few hours depending on the number of rooms."
                )
            )
            embed.add_field(name="Bot Website", value=f"https://franktorio.dev/frd-api/", inline=False)
            print(f"[INFO] [{PRINT_PREFIX}] Documented channel reset complete for {interaction.guild.name}")
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            embed = embeds.create_error_embed(
                "Documented Channel Reset Failed",
                f"An unexpected error occurred: {str(e)}"
            )
            await interaction.followup.send(embed=embed)
            print(f"[ERROR] [{PRINT_PREFIX}] Error in reset_documented: {e}")


shared.FRD_bot.tree.add_command(Setup())