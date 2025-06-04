# config/settings.py

import os
from dotenv import load_dotenv # Optional: for loading .env file in local development

# Optional: Load .env file if it exists (useful for local development)
# Create a .env file in your project root with lines like:
# ADMIN_TELEGRAM_ID_ENV="1234567890"
# You would then run `pip install python-dotenv`
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # Assumes .env is in project root
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"[CONFIG_SETTINGS] Loaded environment variables from: {dotenv_path}")
else:
    print(f"[CONFIG_SETTINGS] .env file not found at {dotenv_path}, will rely on system environment variables.")


# --- Admin Telegram ID ---
# Load from environment variable first, with a fallback for local testing if needed (though env var is best)
# ⚠️ IMPORTANT: For production, ensure 'ADMIN_TELEGRAM_ID_ENV' is set in your deployment environment (e.g., Render, Heroku).
ADMIN_TELEGRAM_ID_STR = os.environ.get("ADMIN_TELEGRAM_ID_ENV")
ADMIN_TELEGRAM_ID = None

if ADMIN_TELEGRAM_ID_STR and ADMIN_TELEGRAM_ID_STR.isdigit():
    ADMIN_TELEGRAM_ID = int(ADMIN_TELEGRAM_ID_STR)
    print(f"[CONFIG_SETTINGS] ADMIN_TELEGRAM_ID loaded from environment variable: {ADMIN_TELEGRAM_ID}")
else:
    # Fallback or warning if not set or not a valid integer
    # For production, you might want to raise an error if it's not set.
    print(f"[CONFIG_SETTINGS] WARNING: ADMIN_TELEGRAM_ID_ENV not set in environment or is not a valid integer ('{ADMIN_TELEGRAM_ID_STR}'). User message forwarding to admin will be disabled unless set directly in code (not recommended for production).")
    # You could set a default test ID here for local dev if you don't use .env, but it's better to use .env or actual env vars.
    # ADMIN_TELEGRAM_ID = 123456789 # Example: FOR LOCAL TESTING ONLY if no env var and no .env

# --- User Message Forwarding Keywords (English) ---
# These can be kept directly in settings or loaded from another config source if they change often.
USER_MESSAGE_FORWARD_KEYWORDS = [
    'help', 'issue', 'stuck', 'error', 'question', 'support', 'bug', 
    'feedback', 'problem', 'agent', 'contact', 'assistance', 'trouble',
    'confused', 'dont understand', "don't understand", 'how to', 'howto'
]
print(f"[CONFIG_SETTINGS] Loaded {len(USER_MESSAGE_FORWARD_KEYWORDS)} keywords for admin forwarding.")

# --- Logging Configuration ---
LOGS_DIR_NAME = "logs" # Define the directory name

# Construct absolute paths for log files to avoid ambiguity,
# assuming settings.py is inside a 'config' directory, and 'logs' is at the project root.
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOGS_DIR_PATH = os.path.join(PROJECT_ROOT_DIR, LOGS_DIR_NAME)

USER_MESSAGES_LOGFILE = os.path.join(LOGS_DIR_PATH, "user_messages.log")
USER_INPUTS_CSVFILE = os.path.join(LOGS_DIR_PATH, "user_inputs.csv")

print(f"[CONFIG_SETTINGS] USER_MESSAGES_LOGFILE path: {USER_MESSAGES_LOGFILE}")
print(f"[CONFIG_SETTINGS] USER_INPUTS_CSVFILE path: {USER_INPUTS_CSVFILE}")

# --- Other Potential Bot Settings (Examples) ---
# BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") # You likely have this in start_bot.py, but could centralize
# DEFAULT_LANGUAGE = "en"
# MAX_MESSAGE_LENGTH_TO_LOG = 2000

# You can add print statements for all loaded settings for easier debugging during startup
# print(f"[CONFIG_SETTINGS] Final ADMIN_TELEGRAM_ID: {ADMIN_TELEGRAM_ID}")