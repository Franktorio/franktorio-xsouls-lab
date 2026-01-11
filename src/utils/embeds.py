# Franktorio's Research Division
# Author: Franktorio
# November 7th, 2025
# Embed utilities for documentation messages

PRINT_PREFIX = "EMBEDS"

# Standard library imports
import time
import urllib.parse
import io
from datetime import datetime, timezone

# Third-party imports
import discord

# Local imports
from src.api import r2_handler
from src import shared
from .utils import get_doc_message_link

IMAGE_MEMORY_CACHE = {}


async def send_room_documentation_embed(channel: discord.TextChannel, room_data: dict, return_embed: bool = False):
    """Send an embed message documenting a room to a specified Discord channel."""

    roomname = room_data.get("room_name")
    embed = discord.Embed(
        title=f"Room: {roomname}",
        description=room_data.get("description"),
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    # Set footer with bot avatar if available
    if shared.FRD_bot and shared.FRD_bot.user:
        embed.set_footer(text="Franktorio & xSoul's Research Division", icon_url=shared.FRD_bot.user.display_avatar.url)
    else:
        embed.set_footer(text="Franktorio & xSoul's Research Division")

    last_updater = room_data.get("edited_by_user_id")
    doc_by = room_data.get('doc_by_user_id')

    embed.add_field(name="Documented by:", value=f"<@{doc_by}>" if doc_by else "Unknown", inline=True)
    embed.add_field(name="Last updated:", value=f"<t:{int(room_data.get('last_updated', time.time()))}:R>", inline=True)
    
    # Always show "Last edited by" - use documenter if no editor is set
    if last_updater:
        embed.add_field(name="Last edited by:", value=f"<@{last_updater}>", inline=True)
    else:
        embed.add_field(name="Last edited by:", value=f"<@{doc_by}>" if doc_by else "Unknown", inline=True)
    embed.add_field(name="Roomtype", value=room_data.get("roomtype", "Unknown"), inline=False)


    
    tags = room_data.get("tags", [])
    tags_str = ""
    for tag in tags:
        tags_str += f"`{tag}` "
    
    if tags:
        embed.add_field(name="Tags", value=tags_str.strip(), inline=False)
    else:
        embed.add_field(name="Tags", value="None", inline=False)
    
    # Encode link
    roomname_link = urllib.parse.quote(roomname)

    embed.add_field(name="Documentation Link", value=f"https://pressure.xsoul.org/rooms/{roomname_link}", inline=False)

    image_files = await r2_handler.get_stored_images(room_data, roomname)

    # Make sure its only 10 images max
    image_files = image_files[:10]

    if return_embed:
        print(f"[DEBUG] [{PRINT_PREFIX}] Created room documentation embed for '{roomname}' (return mode)")
        return embed, image_files
    else:
        message = await channel.send(embed=embed, files=image_files)
        print(f"[INFO] [{PRINT_PREFIX}] Sent room documentation embed for '{roomname}' to channel {channel.id}")

    return message.id


def create_leaderboard_embed(leaderboard_data: dict):
    """Create a science-themed Research Leaderboard embed for Franktorio's & xSoul's Lab."""

    embed = discord.Embed(
        title="⚗️ Franktorio & xSoul's Research Division 🧬",
        description=(
            "**Research Leaderboard** 🏆\n"
            "🔬 Top-10 users with the most contributions! 🔬\n"
            "*Contributions include documentations and edits*"
        ),
        color=discord.Color.from_rgb(52, 152, 219),  # Science blue
        timestamp=datetime.now(timezone.utc)
    )

    embed.set_thumbnail(url=shared.FRD_bot.user.display_avatar.url)
    embed.set_footer(
        text="Franktorio & xSoul's Research Division",
        icon_url=shared.FRD_bot.user.display_avatar.url,
    )

    # Science-flavored rank symbols
    ranks = [
        "#1 - 🥇",  
        "#2 - 🥈",  
        "#3 - 🥉"   
    ]

    for i, (user_id, contribution_count) in enumerate(leaderboard_data.items()):
        rank_icon = ranks[i] if i < 3 else f"#{i+1} - 🧪"

        embed.add_field(
            name=f"{rank_icon}",
            value=f"ㆍ<@{user_id}> 🏆 **Contributions:** `{contribution_count}`",
            inline=False
        )

    embed.add_field(name="Want to contribute?", value="Join https://discord.gg/nightfalldiv and become a researcher!", inline=False)

    # Commented out to keep logs cleaner
    # print(f"[DEBUG] [{PRINT_PREFIX}] Created leaderboard embed with {len(leaderboard_data)} entries")
    return embed


def create_success_embed(title: str, description: str) -> discord.Embed:
    """Create a standardized success embed."""
    embed = discord.Embed(
        title=f"{title}",
        description=description,
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(
        text="Franktorio & xSoul's Research Division",
        icon_url=shared.FRD_bot.user.display_avatar.url,
    )
    print(f"[DEBUG] [{PRINT_PREFIX}] Created success embed: '{title}'")
    return embed

def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create a standardized error embed."""
    embed = discord.Embed(
        title=f"{title}",
        description=description,
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(
        text="Franktorio & xSoul's Research Division",
        icon_url=shared.FRD_bot.user.display_avatar.url,
    )
    print(f"[DEBUG] [{PRINT_PREFIX}] Created error embed: '{title}'")
    return embed

def create_search_result_embed(search_type: str, query: str, results: list, server_id: int) -> list:
    """Create a clean, styled embed for room search results out of a list of room data."""
    embeds = []

    # No results
    if not results:
        embed = discord.Embed(
            title=f"{search_type.capitalize()} Search Results for **{query}**",
            color=discord.Color.blurple(),
            description="### No rooms found\nTry refining your search query — Page 1",
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(
            text="Franktorio & xSoul's Research Division",
            icon_url=shared.FRD_bot.user.display_avatar.url,
        )
        return [embed]

    MAX_FIELDS = 20  # Increased from 10 to reduce total embed count

    # Base embed template
    def new_embed(page: int | None = None):
        title = f"{search_type.capitalize()} Results for **{query} - Results found: {len(results)}**"
        if page is not None:
            title += f" | Page {page}"
        else:
            title += " | Page 1"

        embed = discord.Embed(
            title=title,
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(
            text="Franktorio & xSoul's Research Division",
            icon_url=shared.FRD_bot.user.display_avatar.url,
        )
        return embed

    embed = new_embed()
    field_count = 0
    page = 1

    for room in results:
        doc_link = get_doc_message_link(server_id, room['room_name'])

        tag_text = ", ".join(room['tags']) if room['tags'] else "*No Tags*"

        field_name = f"📍 **{room['room_name'][:256]}**"
        field_value = (
            f"**Tags:** `{tag_text}`\n"
            f"**Local Docs:** {doc_link}\n"
            f"[Website Docs](https://pressure.xsoul.org/rooms/{urllib.parse.quote(room['room_name'])})"
        )

        embed.add_field(name=field_name, value=field_value, inline=False)
        field_count += 1

        # New page
        if field_count >= MAX_FIELDS:
            embeds.append(embed)
            page += 1
            embed = new_embed(page)
            field_count = 0

    # Add final embed
    if field_count > 0:
        embeds.append(embed)

    print(f"[INFO] [{PRINT_PREFIX}] Created {len(embeds)} search result embed(s) for query '{query}' ({len(results)} results)")
    return embeds


def create_edit_history_embed(room_name: str, room_data: dict) -> list:
    """Create a styled embed for room edit history with smart change detection."""
    embeds = []
    edits = room_data.get('edits', [])
    
    if not edits:
        embed = discord.Embed(
            title=f"📜 Edit History for **{room_name}**",
            color=discord.Color.blurple(),
            description="### No edit history\nThis room has never been edited since initial documentation.",
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(
            text="Franktorio & xSoul's Research Division",
            icon_url=shared.FRD_bot.user.display_avatar.url,
        )
        return [embed]
    
    MAX_FIELDS = 10
    
    def new_embed(page: int | None = None):
        title = f"📜 Edit History for **{room_name}**"
        if page is not None:
            title += f" — Page {page}"
        else:
            title += " — Page 1"
        
        embed = discord.Embed(
            title=title,
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(
            text="Franktorio & xSoul's Research Division",
            icon_url=shared.FRD_bot.user.display_avatar.url,
        )
        return embed
    
    embed = new_embed()
    field_count = 0
    page = 1
    
    # Get current state for comparison with most recent edit
    current_state = {
        'description': room_data.get('description', ''),
        'tags': room_data.get('tags', []),
        'roomtype': room_data.get('roomtype', ''),
        'picture_urls': room_data.get('picture_urls', [])
    }
    
    # Process edits in reverse order (newest first)
    for i, edit in enumerate(reversed(edits)):
        # Detect what changed
        changes = []
        
        prev_desc = edit.get('previous_description', '')
        prev_tags = edit.get('previous_tags', [])
        prev_type = edit.get('previous_roomtype', '')
        prev_imgs = edit.get('previous_picture_urls', [])
        prev_room_name = edit.get('previous_room_name', room_name)
        
        # Check if this was a rename action
        if edit.get('action') == 'rename' and prev_room_name != room_name:
            changes.append(f"🏷️ Renamed: `{prev_room_name}` → `{room_name}`")
        
        # Compare with current state for first edit, otherwise with previous edit
        if i == 0:
            compare_state = current_state
        else:
            compare_state = {
                'description': prev_desc,
                'tags': prev_tags,
                'roomtype': prev_type,
                'picture_urls': prev_imgs
            }
        
        # Check description change
        if i == 0 and current_state['description'] != prev_desc:
            changes.append("Description")
        
        # Check tags change
        if i == 0 and set(current_state['tags']) != set(prev_tags):
            added_tags = set(current_state['tags']) - set(prev_tags)
            removed_tags = set(prev_tags) - set(current_state['tags'])
            if added_tags:
                changes.append(f"🏷️ Tags Added: `{', '.join(added_tags)}`")
            if removed_tags:
                changes.append(f"🏷️ Tags Removed: `{', '.join(removed_tags)}`")
            if not added_tags and not removed_tags:
                changes.append("🏷️ Tags Modified")
        
        # Check roomtype change
        if i == 0 and current_state['roomtype'] != prev_type:
            changes.append(f"Type: `{prev_type}` → `{current_state['roomtype']}`")
        
        # Check image changes
        if i == 0 and len(current_state['picture_urls']) != len(prev_imgs):
            img_diff = len(current_state['picture_urls']) - len(prev_imgs)
            if img_diff > 0:
                changes.append(f"🖼️ Images Added: `+{img_diff}`")
            else:
                changes.append(f"🖼️ Images Removed: `{img_diff}`")
        
        if not changes:
            changes.append("Data Updated")
        
        editor_id = edit.get('edited_by_user_id')
        timestamp = edit.get('timestamp', 0)
        
        field_name = f"✏️ Edit #{len(edits) - i}"
        field_value = (
            f"**Edited by:** <@{editor_id}>\n"
            f"**Time:** <t:{int(timestamp)}:R>\n"
            f"**Changes:**\n" + "\n".join(f"• {change}" for change in changes)
        )
        
        embed.add_field(name=field_name, value=field_value, inline=False)
        field_count += 1
        
        # New page
        if field_count >= MAX_FIELDS:
            embeds.append(embed)
            page += 1
            embed = new_embed(page)
            field_count = 0
    
    # Add final embed
    if field_count > 0:
        embeds.append(embed)
    
    print(f"[INFO] [{PRINT_PREFIX}] Created {len(embeds)} edit history embed(s) for room '{room_name}' ({len(edits)} edits)")
    return embeds

def create_bug_report_embed(room_name: str, reports: list, room_data: dict = None) -> list:
    """Create paginated embeds for room bug reports with multiple reports per page.
    
    Args:
        room_name: The name of the room
        reports: List of report dictionaries containing report_id, report_text, reported_by_user_id, timestamp, resolved
        room_data: Optional room data dictionary containing picture_urls for thumbnail
    
    Returns:
        List of embed objects
    """
    embeds = []
    MAX_REPORTS_PER_PAGE = 5
    
    # Get first image URL for thumbnail if available
    thumbnail_url = None
    if room_data and room_data.get('picture_urls'):
        thumbnail_url = room_data['picture_urls'][0]
    
    def new_embed(page: int | None = None):
        title = f"🐞 Bug Reports for **{room_name}**"
        if page is not None:
            title += f" — Page {page}"
        else:
            title += " — Page 1"
        
        embed = discord.Embed(
            title=title,
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
            description=f"**Total Reports:** {len(reports)}"
        )
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        embed.set_footer(
            text="Franktorio & xSoul's Research Division",
            icon_url=shared.FRD_bot.user.display_avatar.url,
        )
        return embed
    
    embed = new_embed()
    report_count = 0
    page = 1
    
    for i, report in enumerate(reports, 1):
        status_emoji = "✅" if report.get('resolved', False) else "🔴"
        
        field_name = f"{status_emoji} Report #{report['report_id']}"
        field_value = (
            f"**Reported by:** <@{report['reported_by_user_id']}>\n"
            f"**Time:** <t:{int(report['timestamp'])}:R>\n"
            f"**Status:** {'Resolved' if report.get('resolved', False) else 'Open'}\n"
            f"**Issue:**\n{report['report_text'][:400]}{'...' if len(report['report_text']) > 400 else ''}"
        )
        
        embed.add_field(name=field_name, value=field_value, inline=False)
        report_count += 1
        
        # New page
        if report_count >= MAX_REPORTS_PER_PAGE and i < len(reports):
            embeds.append(embed)
            page += 1
            embed = new_embed(page)
            report_count = 0
    
    # Add final embed
    if report_count > 0:
        embeds.append(embed)
    
    print(f"[INFO] [{PRINT_PREFIX}] Created {len(embeds)} bug report embed(s) for room '{room_name}' ({len(reports)} reports)")
    return embeds


def create_all_bug_reports_embed(reports: list) -> list:
    """Create paginated embeds for all bug reports across rooms.
    
    Args:
        reports: List of report dictionaries containing report_id, room_name, report_text, 
                 reported_by_user_id, timestamp, resolved, deleted
    
    Returns:
        List of embed objects
    """
    from src.datamanager.db_handlers import room_db_handler
    
    embeds = []
    MAX_REPORTS_PER_PAGE = 5
    
    # Cache room data to avoid duplicate queries
    room_cache = {}
    
    def new_embed(page: int | None = None):
        title = "🐞 All Bug Reports"
        if page is not None:
            title += f" - Page {page}"
        else:
            title += " - Page 1"
        
        embed = discord.Embed(
            title=title,
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
            description=f"**Total Unresolved Reports:** {len(reports)}"
        )
        embed.set_footer(
            text="Franktorio & xSoul's Research Division",
            icon_url=shared.FRD_bot.user.display_avatar.url,
        )
        return embed
    
    embed = new_embed()
    report_count = 0
    page = 1
    
    for i, report in enumerate(reports, 1):
        status_emoji = "✅" if report.get('resolved', False) else "🔴"
        
        # Get room thumbnail for the first report on each page
        if report_count == 0:
            room_name = report['room_name']
            if room_name not in room_cache:
                room_cache[room_name] = room_db_handler.get_roominfo(room_name)
            room_data = room_cache[room_name]
            if room_data and room_data.get('picture_urls'):
                embed.set_thumbnail(url=room_data['picture_urls'][0])
        
        field_name = f"{status_emoji} Report #{report['report_id']} - **{report['room_name']}**"
        field_value = (
            f"**Reported by:** <@{report['reported_by_user_id']}>\n"
            f"**Time:** <t:{int(report['timestamp'])}:R>\n"
            f"**Status:** {'Resolved' if report.get('resolved', False) else 'Open'}\n"
            f"**Issue:**\n{report['report_text'][:350]}{'...' if len(report['report_text']) > 350 else ''}"
        )
        
        embed.add_field(name=field_name, value=field_value, inline=False)
        report_count += 1
        
        # New page
        if report_count >= MAX_REPORTS_PER_PAGE and i < len(reports):
            embeds.append(embed)
            page += 1
            embed = new_embed(page)
            report_count = 0
    
    # Add final embed
    if report_count > 0:
        embeds.append(embed)
    
    print(f"[INFO] [{PRINT_PREFIX}] Created {len(embeds)} embed(s) for all bug reports ({len(reports)} total reports)")
    return embeds

def create_single_bug_report_embed(report: dict) -> discord.Embed:
    """Create an embed for a single bug report.
    
    Args:
        report: A dictionary containing report_id, room_name, report_text, reported_by_user_id, timestamp, resolved, deleted
    Returns:
        A discord.Embed object
    """
    from src.datamanager.db_handlers import room_db_handler
    
    status_emoji = "✅" if report.get('resolved', False) else "🔴"
    
    embed = discord.Embed(
        title=f"{status_emoji} Bug Report #{report['report_id']} - **{report['room_name']}**",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc),
        description=(
            f"**Reported by:** <@{report['reported_by_user_id']}>\n"
            f"**Time:** <t:{int(report['timestamp'])}:R>\n"
            f"**Status:** {'Resolved' if report.get('resolved', False) else 'Open'}\n\n"
            f"**Issue:**\n{report['report_text']}"
        )
    )
    
    # Set thumbnail from room's first image if available
    room_data = room_db_handler.get_roominfo(report['room_name'])
    if room_data and room_data.get('picture_urls'):
        embed.set_thumbnail(url=room_data['picture_urls'][0])
    
    embed.set_footer(
        text="Franktorio & xSoul's Research Division",
        icon_url=shared.FRD_bot.user.display_avatar.url,
    )
    return embed
