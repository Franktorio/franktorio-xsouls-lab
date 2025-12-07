# This script validates the configuration files for the project.
# It should be run to ensure all configuration files are correctly formatted and contain valid settings.
# Checks the vars.py.example file to ensure all required variables are present.

# On home directory of the project, run:
# python -m automations.tests.validate_config
# OR
# python3 -m automations.tests.validate_config

# Make sure have vars.py file in config/ directory before running this script.
# Use vars.py.example as a template.


try:
    from config import vars as config_vars
except ImportError as e:
    print(f"❌ Failed to import configuration module: {e}")
    print("Please ensure that 'config/vars.py' exists and is correctly formatted.")
    exit(1)

not_set = []
for name, value in config_vars.__dict__.items():
    print(f"Checking configuration variable: {name}")
    if name.isupper():
        if value is None or (isinstance(value, str) and value.startswith("YOUR_")):
            print(f"❌ Configuration variable '{name}' is not set.")
            not_set.append(name)

if not not_set:
    print("✅ All configuration variables are set correctly.")
    exit(0)
else:
    print(f"❌ The following configuration variables are not set: {', '.join(not_set)}")
    exit(1)