# Franktorio's Research Division Bot
A discord bot & API for collaborative game research and documentation

> This is not an official bot or tool. We are not affiliated with the Pressure development team or staff.

Franktorio's Research Division (FRD) is designed to facilitate collaborative research and documentation for the Roblox game *Pressure*. The bot's main features are the following:

- **Room Documentation System**: Store images and descriptions about in-game rooms featuring categorizing and tagging for easy search.
- **Research API**: API system that connects with the room documentation system to allow the bot to synchronize with external data sources.
- **Franktorio's Research Scanner**: This bot provides full backend support for the [franktorio-research-scanner](https://github.com/Franktorio/franktorio-pressure-scanner), allowing for the mass-collection of room data and the real-time display of what the research community has documented while playing.
- **In-game Bug Report Support**: Community-driven bug reports linked to rooms, facilitating the diagnosing and fixing for room generation bugs.
- **Role-based Permissions**: Tiered permission system to control who can modify the documentations.
- **Automated Database Synchronization**: Automatically synchronizes data with the external data source if configured.
- **Leaderboards**: To show recognition to the contributors, a leaderboard is maintained displaying top contributors.


## Features

### Room Documenting
- Allows upload for up to 10 images, which are stored in an r2 cloudflare for public use.
- Roomtype and tags categorization for complex search
- Automatic brightening of images via gamma

### Research Division
- Hirearchy system to contain dangereous permissions higher up the trust chain
  - Viewer → Trial Researcher → Novice Researcher → Experienced Researcher → Head Researcher
- Multi-server with home-server setup, allowing for the database be displayed in multiple server but only modified by researchers in the home-server

### Scanner Integration
- Encounter-based data gathering
- Each encounter is stored in it's own session, allowing for easy categorizing
- Sessions time out after two hours of being created


## Installation & Setup

Must have:
- Discord bot token
- R2 bucket for image storage
- Python 3.12+

1. **Clone the repository**
```bash
git clone https://github.com/Franktorio/franktorio-xsouls-lab.git
cd franktorio-xsouls-lab
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure the bot**
   - Copy `config/vars.py.example` to `config/vars.py`
   - Fill in your configuration values:
     ```python
     BOT_TOKEN = "your_discord_bot_token"
     API_PORT = 8000
     LOCAL_KEY = "your_secure_api_key"
     # ... see vars.py.example for all options (use python automations/tests/validate_config.py to validate config)
     ```

4. **Initialize databases**
   - Databases are automatically created on first run
   - Located in `databases/` directory
   - Three SQLite databases: `frd_room.db`, `frd_server.db`, `frd_scanner.db`

5. **Run the bot**
```bash
python main.py
```

The bot will:
- Initialize all databases
- Start the FastAPI server (default port: 8000)
- Connect to Discord
- Sync slash commands
- Begin background tasks


## Development

### Validate Configurations Variables
```bash
python automations/tests/validate_config.py
```

### Database Migrations
```bash
python automations/scripts/migrate_db.py
```

### Initializing Databases
```bash
python automations/scripts/init_dbs.py
```

## Todo
- [ ] Document external API in a .md
- [ ] Document research & scanner API in a .md
- [ ] Document commands in .md
- [ ] Add commands to analyze and view scanner data

### Current Task
- **Document commands in .md**
 - [x] Dev commands
 - [x] Management commands
 - [x] Research commands
 - [x] Room commands
 - [x] Setup commands


## Contact information
**Franktorio** - Main Bot Developer
- Discord user: `mr_franktorio` (1181432574317436948)
- Reach out to me if there is an issue with the **bot**.

**xSoul** - Main Web Developer
- Discord user: `xsoul.org` (589010329900679184)
- Reach out to him if I `(franktorio)` am unreachable.