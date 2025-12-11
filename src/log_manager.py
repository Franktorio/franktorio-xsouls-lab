# Franktorio's Research Division
# Author: Franktorio
# December 10th 2025
# Log Manager - Overrides print function to log outputs to a file

import builtins
import datetime

DEBUG_ENABLED = False # Toggles skipping over prints with [DEBUG] tag

# Reference to the original print function
original_print = builtins.print

# Create and/or open the bot logs file in append mode
bot_logs = open("logs/bot_logs.log", "a")

def logging_print(*args, **kwargs):
    """Custom print function for logging purposes."""
    global DEBUG_ENABLED
    # Skip debug prints if DEBUG_ENABLED is False
    if not DEBUG_ENABLED:
        for arg in args:
            if isinstance(arg, str) and "[DEBUG]" in arg:
                return
    original_print(*args, **kwargs)  # Print to console

    text_output = ""
    for arg in args:
        text_output += str(arg) + " "

    bot_logs.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text_output}\n")
    bot_logs.flush() # Force write to file

# Override the built-in print function with the custom logging print function
builtins.print = logging_print