# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# On guild add event handler

# Standard library imports
import io
import json

# Third-party imports
import discord
from discord.ext import commands
from discord import app_commands

# Local imports
from src import shared
from src import datamanager
import config.vars as vars


@shared.FRD_bot.event
async def on_guild_join(guild: discord.Guild):
    """Event handler for when the bot joins a new guild."""
    
    owner = guild.owner
    if owner:
        try:
            embed = discord.Embed(
                title="Thank You for Inviting Franktorio & xSoul's Lab!",
                description=(
                    "Hello! Thank you for inviting Franktorio & xSoul's Research Division Bot to your server. "
                    "This bot helps sharing and viewing documented rooms in Pressure!.\n\n"
                    "To get started, please use the `/setup init` command in your server. "
                    "This will create the necessary channels for documentation and leaderboards.\n\n"
                    "You do not need all those channels so feel free to delete the ones you don't need after setup.\n\n"
                ),
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(
                name="Website & Support",
                value=("For support, talk to the developers in https://discord.gg/nightfalldiv and visit our website at https://pressure.xsoul.org/"),
                inline=False
            )
            embed.set_footer(text="Franktorio & xSoul's Research Division", icon_url=shared.FRD_bot.user.display_avatar.url)
            await owner.send(embed=embed)

            perms_needed_embed = discord.Embed(
                title="Important: Bot Permissions Needed",
                description=(
                    "To ensure the bot functions correctly, please make sure it has the following permissions in your server:\n"
                    "- Manage Channels: Create/delete documented and leaderboard channels\n"
                    "- Manage Messages: Purge bot messages, delete documentation messages\n"
                    "- Send Messages: Post documentation and leaderboard content\n"
                    "- Embed Links: Send rich embeds for documentation\n"
                    "- Attach Files: Upload images for room documentation\n"
                    "- Read Message History: Fetch messages for updates and purges\n"
                    "- Add Reactions: Add reactions for confirmation prompts\n\n"
                    "Without these permissions, the bot may not be able to create channels, post documentation, or manage messages properly."
                ),
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            perms_needed_embed.set_footer(text="Franktorio & xSoul's Research Division", icon_url=shared.FRD_bot.user.display_avatar.url)
            await owner.send(embed=perms_needed_embed)
        except Exception as e:
            print(f"❌ Could not send welcome message to guild owner: {e}")