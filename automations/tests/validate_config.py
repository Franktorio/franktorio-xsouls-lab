# This script validates the configuration files for the project.
# It should be run to ensure all configuration files are correctly formatted and contain valid settings.
# Checks the vars.py.example file to ensure all required variables are present.

# On home directory of the project, run:
# python -m automations.tests.validate_config
# OR
# python3 -m automations.tests.validate_config

# Make sure have vars.py file in config/ directory before running this script.
# Use vars.py.example as a template.



PRINT_PREFIX = "CONFIG VALIDATION"


try:
    from config import vars as config_vars
    with open("config/vars.py.example", "r") as example_file:
        example_content = example_file.read()
    to_check = {}
    exec(example_content, to_check)
except ImportError as e:
    print(f"[WARNING] [{PRINT_PREFIX}] Failed to import configuration module: {e}")
    print(f"[WARNING] [{PRINT_PREFIX}] Please ensure that 'config/vars.py' exists and is correctly formatted.")
    exit(1)

not_set = []
for key in to_check:
    if key.isupper():  # Only check uppercase variables
        if not hasattr(config_vars, key): # Variable not set
            not_set.append(key)
        elif getattr(config_vars, key) == to_check[key] and type(getattr(config_vars, key)) == str: # Variable set to default/example value as string
            not_set.append(key)

if not not_set:
    print(f"[INFO] [{PRINT_PREFIX}] All configuration variables are set correctly.")
else:
    print(f"[WARNING] [{PRINT_PREFIX}] The following configuration variables are not set: {', '.join(not_set)}: Please update 'config/vars.py' accordingly.")
    exit(1)