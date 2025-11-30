# Franktorio's Research Bot

# Standard library imports
import asyncio
import datetime
import threading

# Third-party imports
import discord
from discord.ext import commands
import uvicorn

# Local imports
import config
import shared

"""
REQUIRED BOT PERMISSIONS:
=========================
The bot requires the following Discord permissions to function properly:

Server Permissions:
- Manage Channels: Create/delete documented and leaderboard channels
- Manage Messages: Purge bot messages, delete documentation messages
- Send Messages: Post documentation and leaderboard content
- Embed Links: Send rich embeds for documentation
- Attach Files: Upload images for room documentation
- Read Message History: Fetch messages for updates and purges
- Add Reactions: Add reactions for confirmation prompts
- Use External Emojis: (Optional) For enhanced embeds

Channel-Specific Permissions:
- In documented channels: Send Messages, Embed Links, Attach Files, Read Message History
- In leaderboard channels: Send Messages, Embed Links, Read Message History
- Deny @everyone Send Messages in documented/leaderboard channels

OAuth2 Scopes:
- bot
- applications.commands

Bot Invite Link should include permissions integer: 277025770560
(Manage Channels, Manage Messages, Send Messages, Embed Links, Attach Files, 
 Read Message History, Add Reactions, Use External Emojis)
"""

# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

FRD_bot = commands.Bot(command_prefix='!', intents=intents, description="Franktorio's Research Bot")

# Set bot in shared module so all other modules can access it
shared.set_bot(FRD_bot)

# Import modules that register commands and tasks
import src.commands  # Commands will auto-register via decorators
import src.events  # Event handlers will auto-register via decorators

import src.datamanager.init_db as data_manager
import src.tasks.init_tasks as init_tasks
from src.api.research_api import app as api_app

def run_api_server():
    """Run the FastAPI server in a separate thread."""
    uvicorn.run(api_app, host="0.0.0.0", port=8651, log_level="info")

@FRD_bot.event
async def on_ready():

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Print startup information
    print("🟢 Bot is online.")
    print(f"🕒 Time: {now}")
    print(f"👤 Logged in as: {FRD_bot.user} (ID: {FRD_bot.user.id})")
    print("")

    # Initialize database
    data_manager.init_db()
    
    # Start API server in a separate thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    print("🌐 API server started on http://0.0.0.0:8651")
    
    # Start background tasks
    init_tasks.start_all_tasks()
    
    # Sync command tree
    try:
        synced = await FRD_bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

FRD_bot.run(config.vars.BOT_TOKEN)