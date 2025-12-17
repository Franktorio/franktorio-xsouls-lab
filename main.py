# Franktorio's Research Bot

# Standard library imports
import datetime
import threading

# Third-party imports
import discord
import uvicorn
from discord.ext import commands

# Local imports
from src.datamanager.db_handlers import room_db_handler
import config
import src.shared as shared

# Override print function to log outputs to file
import src.log_manager as log_manager # This module overrides the print function
import automations.tests.validate_config # Will auto-run test on import

if config.vars.DEBUG_ENABLED:
    print("[WARNING] [MAIN] Debug logging is ENABLED")
else:
    print("[WARNING] [MAIN] Debug logging is DISABLED")

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

import src.datamanager.database_manager as database_manager
import src.datamanager.backup_manager as backup_manager
import src.tasks.init_tasks as init_tasks
from src.api.research_api import app as api_app

def run_api_server():
    """Run the FastAPI server in a separate thread."""
    uvicorn.run(api_app, host="0.0.0.0", port=config.vars.API_PORT, log_level="info")

# Initialize database
print("[INFO] [MAIN] Initializing databases...")
database_manager.init_databases()
print("[INFO] [MAIN] Initializing backup manager...")
backup_manager.init_backup_manager()

# Start API server in a separate thread
print("[INFO] [MAIN] Starting API server...")
api_thread = threading.Thread(target=run_api_server, daemon=True)
api_thread.start()
print(f"[INFO] [MAIN] API server started on http://0.0.0.0:{config.vars.API_PORT}")


@FRD_bot.event
async def on_ready():

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Print startup information
    print("="*50)
    print("[INFO] [MAIN] Bot is online")
    print(f"[INFO] [MAIN] Time: {now}")
    print(f"[INFO] [MAIN] Logged in as: {FRD_bot.user} (ID: {FRD_bot.user.id})")
    print(f"[INFO] [MAIN] Connected to {len(FRD_bot.guilds)} guild(s)")
    print("="*50)
    
    # Start background tasks
    init_tasks.start_all_tasks()
    
    # Sync command tree
    print("[INFO] [MAIN] Syncing command tree...")
    try:
        synced = await FRD_bot.tree.sync()
        print(f"[INFO] [MAIN] Successfully synced {len(synced)} command(s)")
    except Exception as e:
        print(f"[ERROR] [MAIN] Failed to sync commands: {e}")
        print("[WARNING] [MAIN] Bot will continue running but slash commands may not be available")
    
    # Set status to how many documented rooms there are
    documented_rooms = len(room_db_handler.get_all_room_names())
    await FRD_bot.change_presence(activity=discord.Game(name=f"Documented Rooms: {documented_rooms}"))
    print(f"[INFO] [MAIN] Set bot status to 'Documented Rooms: {documented_rooms}'")

print("="*50)
print("[INFO] [MAIN] Starting bot connection to Discord...")
FRD_bot.run(config.vars.BOT_TOKEN)