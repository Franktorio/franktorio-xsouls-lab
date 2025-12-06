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
import src.shared as shared


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

import src.datamanager.helpers as data_manager
import src.tasks.init_tasks as init_tasks
from src.api.research_api import app as api_app

def run_api_server():
    """Run the FastAPI server in a separate thread."""
    uvicorn.run(api_app, host="0.0.0.0", port=config.vars.API_PORT, log_level="info")

# Initialize database
data_manager.init_db()

@FRD_bot.event
async def on_ready():

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Print startup information
    print("🟢 Bot is online.")
    print(f"🕒 Time: {now}")
    print(f"👤 Logged in as: {FRD_bot.user} (ID: {FRD_bot.user.id})")
    print("")
    
    # Start API server in a separate thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    print(f"🌐 API server started on http://0.0.0.0:{config.vars.API_PORT}")
    
    # Start background tasks
    init_tasks.start_all_tasks()
    
    # Sync command tree
    try:
        synced = await FRD_bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

FRD_bot.run(config.vars.BOT_TOKEN)