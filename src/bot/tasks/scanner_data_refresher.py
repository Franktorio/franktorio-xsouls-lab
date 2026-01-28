# Franktorio's Research Division
# Author: Franktorio
# January 17th, 2026
# Scanner Data Analyzer Module

PRINT_PREFIX = "SCANNER DATA ANALYZER"

"""
This module has a collection of functions designed to analyze and process the data stored frd_scanner.db
collected from various users uisng the scannner. It includes utilities for parsing, validating, and extracting
meaningful insights from raw scanner data inputs.
"""

# Standard library imports
import threading
import time
from math import inf

# Local imports
from src.datamanager.db_handlers import action_json_handler, scanner_db_handler

def _get_sessions_with_length_above(threshold: int, upper_threshold: int | None = inf, ambiguity_percent: int | None = 0) -> dict[str, list[tuple]]:
    """
    Retrieve all scanner sessions where the session length exceeds the specified threshold.

    Args:
        threshold (int): The minimum session length to filter by.
        upper_threshold (int | None = inf): The maximum session length to filter by.
        ambiguity_percent (int | None = 0): An optional parameter to account for minor discrepancies in session length 
            (If threshold is 50 but a room with 49 appears, if it is within the ambiguity range, it will still be considered)

    Returns:
        dict[str, list[tuple]]: A dictionary where keys are session IDs and values are lists of room tuples (room_name, found_at) that meet the length criteria.
    """
    print(f"[INFO] [{PRINT_PREFIX}] Retrieving sessions with length above {threshold} (±{ambiguity_percent}%)")
    sessions = scanner_db_handler.get_sessions()

    qualifying_sessions = {}

    for session in sessions:
        # Ignore open sessions
        if session['closed'] != 1:
            continue
        
        session_id = session['session_id']
        rooms_of_session = scanner_db_handler.get_session_rooms(session_id)

        if len(rooms_of_session) > threshold - (threshold * ambiguity_percent / 100):
            print(f"[DEBUG] [{PRINT_PREFIX}] Session {session_id} qualifies with length {len(rooms_of_session)}")
            qualifying_sessions[session_id] = rooms_of_session[:upper_threshold] # Trim to upper threshold if applicable

    print(f"[INFO] [{PRINT_PREFIX}] Found {len(qualifying_sessions)} sessions above length threshold of {threshold} (±{ambiguity_percent}%)")
    return qualifying_sessions

def _remove_duplicates_from_qualifying_sessions(sessions: dict[str, list[tuple]], similarity_percent: int | None = 100) -> dict[str, list[tuple]]:
    """
    Remove duplicate sessions if there are sessions a certain percentage similar to each other.
    Ignores timestamps and only compares room data.

    Args:
        sessions (dict[str, list[tuple]]): A dictionary where keys are session IDs and values are lists of room tuples (room_name, found_at).
        similarity_percent (int | None = 100): The percentage similarity threshold to consider sessions as duplicates.
            A similarity of 100% means sessions must be identical to be considered duplicates.
    Returns:
        dict[str, list[tuple]]: A dictionary of unique sessions after removing duplicates.
    """
    print(f"[INFO] [{PRINT_PREFIX}] Removing duplicate sessions with similarity threshold of {similarity_percent}%")

    unique_sessions = {}

    for session_id, rooms in sessions.items():
        room_names = [room[0] for room in rooms]
        
        for session_id_cmp, rooms_cmp in unique_sessions.items():
            room_names_cmp = [room[0] for room in rooms_cmp]
            
            min_length = min(len(room_names), len(room_names_cmp))
            max_length = max(len(room_names), len(room_names_cmp))
            
            # Count matching rooms in the same positions
            matching_positions = sum(1 for i in range(min_length) if room_names[i] == room_names_cmp[i])
            
            # Similarity is based on how many positions match relative to the longer sequence
            similarity = (matching_positions / max_length) * 100

            if similarity >= similarity_percent:
                print(f"[INFO] [{PRINT_PREFIX}] Session {session_id} is too similar to {session_id_cmp} ({similarity:.2f}%), skipping.")
                break
        else:
            unique_sessions[session_id] = rooms
            print(f"[DEBUG] [{PRINT_PREFIX}] Session {session_id} is unique, adding to results.")
    
    print(f"[INFO] [{PRINT_PREFIX}] Reduced to {len(unique_sessions)} unique sessions after duplicate removal.")
    return unique_sessions


def _get_clean_data(threshold: int, upper_threshold: int | None = None, ambiguity_percent: int | None = 0, similarity_percent: int | None = 100) -> dict[str, list[tuple]]:
    """
    Get clean scanner session data by filtering sessions based on length and removing duplicates.

    Args:
        threshold (int): The minimum session length to filter by.
        ambiguity_percent (int | None = 0): An optional parameter to account for minor discrepancies in session length.
        similarity_percent (int | None = 100): The percentage similarity threshold to consider sessions as duplicates.

    Returns:
        dict[str, list[tuple]]: A dictionary of clean scanner sessions with room tuples (room_name, found_at).
    """
    print(f"[INFO] [{PRINT_PREFIX}] Getting clean data with length threshold {threshold}, ambiguity {ambiguity_percent}%, similarity {similarity_percent}%")

    sessions_above_threshold = _get_sessions_with_length_above(threshold, upper_threshold, ambiguity_percent)
    clean_sessions = _remove_duplicates_from_qualifying_sessions(sessions_above_threshold, similarity_percent)

    return clean_sessions


def _refresh_cleaned_data() -> None:
    """
    Perform refresh of the cleaned scanner data.
    This function clears existing cleaned data and repopulates it based on the latest scanner sessions.
    """
    print(f"[INFO] [{PRINT_PREFIX}] Starting daily data refresh...")

    # Clear existing cleaned data
    scanner_db_handler.clear_cleaned_data()

    # Define thresholds for different categories
    categories = {
        "hundred": 100,
        "fifty": 50,
        "twentyfive": 25,
        "all": 0
    }

    # Define where to trim datasets
    upper_limits = {
        "hundred": 100,
        "fifty": 50,
        "twentyfive": 25,
        "all": None
    }

    for category, threshold in categories.items():
        print(f"[INFO] [{PRINT_PREFIX}] Processing category '{category}' with threshold {threshold}...")
        clean_data = _get_clean_data(threshold, upper_threshold=upper_limits[category], similarity_percent=90) # Using 90% similarity for duplicate removal

        for session_id, rooms in clean_data.items():
            success = scanner_db_handler.add_validated_session(session_id, rooms, category)
            if success:
                print(f"[DEBUG] [{PRINT_PREFIX}] Added validated session {session_id} to category '{category}'.")
            else:
                print(f"[ERROR] [{PRINT_PREFIX}] Failed to add validated session {session_id} to category '{category}'.")

    print(f"[INFO] [{PRINT_PREFIX}] Daily data refresh completed.")

def _analyze_data() -> None:
    """
    Wrapper function to perform various analyses on the cleaned scanner data.
    """

    _most_common_rooms_analysis()
    _activity_over_time_analysis()

def _most_common_rooms_analysis() -> None:
    """
    Analyze the most common rooms in the cleaned scanner data.
    Analysis focuses on identifying rooms that appear most frequently across all validated sessions.

    Splits into categories based on session lengths (25, 50, 100, all).
    """
    print(f"[INFO] [{PRINT_PREFIX}] Analyzing most common rooms in cleaned scanner data...")
    
    categories = ["hundred", "fifty", "twentyfive", "all"]
    
    for category in categories:
        print(f"[INFO] [{PRINT_PREFIX}] Analyzing category '{category}'...")
        
        # Get all validated sessions for this category
        validated_sessions = scanner_db_handler.get_validated_sessions(category)
        
        if not validated_sessions:
            print(f"[INFO] [{PRINT_PREFIX}] No validated sessions found for category '{category}'. Skipping.")
            continue
        
        # Count room occurrences
        room_frequency = {}
        total_rooms = 0
        
        for session_id, rooms in validated_sessions.items():
            for room_name, _ in rooms:
                room_frequency[room_name] = room_frequency.get(room_name, 0) + 1
                total_rooms += 1
        
        # Sort rooms by frequency (descending; most common first)
        sorted_rooms = sorted(room_frequency.items(), key=lambda x: x[1], reverse=True)
        
        # Store top 50 most common rooms and their percentages
        top_50_rooms = []
        for room_name, count in sorted_rooms[:50]:
            percentage = (count / total_rooms) * 100 if total_rooms > 0 else 0
            top_50_rooms.append({
                "room_name": room_name,
                "count": count,
                "percentage": round(percentage, 2)
            })
        
        # Store the analysis result
        stat_name = f"most_common_rooms_{category}"
        stat_data = {
            "total_sessions": len(validated_sessions),
            "total_rooms": total_rooms,
            "unique_rooms": len(room_frequency),
            "top_50": top_50_rooms,
            "updated_at": int(time.time())
        }
        
        scanner_db_handler.set_statistic(stat_name, stat_data)
        print(f"[INFO] [{PRINT_PREFIX}] Stored analysis for category '{category}': {len(top_50_rooms)} top rooms from {len(validated_sessions)} sessions.")
    
    print(f"[INFO] [{PRINT_PREFIX}] Most common rooms analysis completed.")

def _activity_over_time_analysis() -> None:
    """
    Analyze scanner activity over time from the cleaned data.
    Analysis focuses on documented room encounters over different time periods.

    Basically graphing how often rooms are reported over time. Bundled by day.
    """
    print(f"[INFO] [{PRINT_PREFIX}] Analyzing scanner activity over time...")
    
    # Calculate cutoff time (1 month ago in UTC)
    one_month_ago = int(time.time()) - (30 * 86400)  # 30 days in seconds
    
    # Get all validated sessions (using "all" category to get everything)
    validated_sessions = scanner_db_handler.get_validated_sessions("all")
    
    if not validated_sessions:
        print(f"[INFO] [{PRINT_PREFIX}] No validated sessions found. Skipping activity analysis.")
        return
    
    daily_bundles = {}
    
    for session_id, rooms in validated_sessions.items():
        for room_name, timestamp in rooms:
            # Skip encounters older than 1 month
            if timestamp < one_month_ago:
                continue
            
            # Group by day (start of day in UTC)
            day_key = int(timestamp // 86400) * 86400
            
            if day_key not in daily_bundles:
                daily_bundles[day_key] = 0
            
            daily_bundles[day_key] += 1
    
    # Convert to sorted list of daily counts
    daily_data = sorted(
        [{"timestamp": ts, "count": count} for ts, count in daily_bundles.items()],
        key=lambda x: x["timestamp"]
    )
    
    # Calculate peak activity day
    peak_day = max(daily_data, key=lambda x: x["count"]) if daily_data else None
    
    # Store the analysis result
    stat_name = "activity_over_time"
    stat_data = {
        "total_sessions": len(validated_sessions),
        "daily_activity": daily_data,
        "peak_day": peak_day,
        "days_tracked": len(daily_data),
        "total_encounters": sum(entry["count"] for entry in daily_data),
        "updated_at": int(time.time())
    }
    
    scanner_db_handler.set_statistic(stat_name, stat_data)
    print(f"[INFO] [{PRINT_PREFIX}] Stored activity analysis: {len(daily_data)} days tracked (last 30 days).")
    
    print(f"[INFO] [{PRINT_PREFIX}] Activity over time analysis completed.")

class DataRefreshTask():
    """Class representing the daily data refresh task."""

    def __init__(self):
        self._task_thread = threading.Thread(target=self._run_task)
        self._is_running = False

    def _run_task(self):
        """Run the data refresh task."""
        
        while True:
            self._is_running = True
            
            last_refresh = action_json_handler.get_action("last_scanner_data_refresh", default=0)

            # Calculate time till next refresh (24 hours)
            time_since_last_refresh = time.time() - last_refresh
            time_until_next_refresh = max(0, 86400 - time_since_last_refresh)

            time.sleep(time_until_next_refresh)

            _refresh_cleaned_data()
            _analyze_data()
            action_json_handler.set_action("last_scanner_data_refresh", time.time())

    def start(self):
        """Start the data refresh task."""
        if not self._is_running:
            self._task_thread = threading.Thread(target=self._run_task)
            self._task_thread.start()

    def is_running(self) -> bool:
        """Check if the task is currently running."""
        return self._is_running

refresh_scanner_data_task = DataRefreshTask()