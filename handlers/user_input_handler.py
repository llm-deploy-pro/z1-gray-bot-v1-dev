# handlers/user_input_handler.py

from telegram import Update
from telegram.ext import ContextTypes # Ensure this is the correct import for your PTB version
from datetime import datetime
import os
import csv

# Attempt to import settings from the config module
try:
    from config.settings import (
        ADMIN_TELEGRAM_ID,
        USER_MESSAGE_FORWARD_KEYWORDS,
        USER_MESSAGES_LOGFILE,
        USER_INPUTS_CSVFILE,
        # You might want to add a default logger from your bot_loader or settings
        # For now, we'll use context.logger if available, or print
    )
except ImportError:
    # Fallback or default values if settings.py is not found or variables are missing
    # This is crucial for standalone testing or if settings are structured differently
    print("WARNING: Could not import settings from config.settings. Using fallback values for user_input_handler.")
    ADMIN_TELEGRAM_ID = None # Must be set for forwarding to work
    USER_MESSAGE_FORWARD_KEYWORDS = ['help', 'stuck', 'issue', 'problem', 'support', 'question', 'assist'] # Default English keywords
    LOGS_DIR_DEFAULT = "logs"
    USER_MESSAGES_LOGFILE = os.path.join(LOGS_DIR_DEFAULT, "user_messages.log")
    USER_INPUTS_CSVFILE = os.path.join(LOGS_DIR_DEFAULT, "user_inputs.csv")


async def handle_user_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles non-command text messages from users.
    Logs the message to a .log file and a .csv file.
    Forwards the message to the admin if it contains specific keywords.
    """
    # Ensure there's a message and text content
    if not update.message or not update.message.text:
        if hasattr(context, 'logger') and context.logger:
            context.logger.warning("[USER_INPUT_HANDLER] Received an update without message or message text.")
        else:
            print("[USER_INPUT_HANDLER] WARNING: Received an update without message or message text.")
        return

    user = update.effective_user
    if not user:
        if hasattr(context, 'logger') and context.logger:
            context.logger.warning("[USER_INPUT_HANDLER] Received a message without an effective_user.")
        else:
            print("[USER_INPUT_HANDLER] WARNING: Received a message without an effective_user.")
        return
        
    user_id = user.id
    username = user.username if user.username else "N/A" # Handle cases where username might be None
    message_text = update.message.text
    timestamp_utc = datetime.utcnow()
    timestamp_str_log = timestamp_utc.strftime('%Y-%m-%d %H:%M:%S UTC') # For .log file
    timestamp_iso_csv = timestamp_utc.isoformat() # For .csv file

    # --- Ensure logs directory exists ---
    log_dir = os.path.dirname(USER_MESSAGES_LOGFILE) # Assumes USER_MESSAGES_LOGFILE includes 'logs/' path
    if not log_dir: # Handle case where USER_MESSAGES_LOGFILE might be just a filename
        log_dir = "logs" # Default to "logs" if path part is missing
    
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        if hasattr(context, 'logger') and context.logger:
            context.logger.error(f"[USER_INPUT_HANDLER] Error creating logs directory '{log_dir}': {e}")
        else:
            print(f"[USER_INPUT_HANDLER] ERROR: Error creating logs directory '{log_dir}': {e}")
        # Decide if you want to return or continue without logging if dir creation fails
        # For now, we'll attempt to log anyway, which might fail if dir doesn't exist.

    # --- Write to .log file (Solution C - Part 1) ---
    try:
        with open(USER_MESSAGES_LOGFILE, "a", encoding="utf-8") as f:
            f.write(f"{timestamp_str_log} | UserID: {user_id} | @{username} | Message: {message_text}\n")
        if hasattr(context, 'logger') and context.logger:
            context.logger.info(f"[USER_INPUT_LOG] UserID: {user_id}, @{username}, Message logged to .log: '{message_text[:70]}...'")
        else:
            print(f"[USER_INPUT_LOG] UserID: {user_id}, @{username}, Message logged to .log: '{message_text[:70]}...'")
    except Exception as e:
        if hasattr(context, 'logger') and context.logger:
            context.logger.error(f"[USER_INPUT_HANDLER] Error writing to .log file '{USER_MESSAGES_LOGFILE}': {e}")
        else:
            print(f"[USER_INPUT_HANDLER] ERROR: Error writing to .log file '{USER_MESSAGES_LOGFILE}': {e}")

    # --- Write to .csv file (Solution C - Part 2) ---
    try:
        # Ensure the directory for CSV also exists
        csv_dir = os.path.dirname(USER_INPUTS_CSVFILE)
        if not csv_dir:
            csv_dir = "logs"
        os.makedirs(csv_dir, exist_ok=True)

        file_exists = os.path.isfile(USER_INPUTS_CSVFILE)
        fieldnames_csv = ["timestamp_iso", "user_id", "username", "message_text"] # Renamed for clarity

        with open(USER_INPUTS_CSVFILE, "a", newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames_csv)
            if not file_exists or os.path.getsize(USER_INPUTS_CSVFILE) == 0: # Check if file is empty too
                writer.writeheader()
            writer.writerow({
                "timestamp_iso": timestamp_iso_csv,
                "user_id": user_id,
                "username": username,
                "message_text": message_text
            })
        # Optional log for CSV writing
        # if hasattr(context, 'logger') and context.logger:
        #     context.logger.info(f"[USER_INPUT_CSV] UserID: {user_id}, @{username}, Message logged to .csv.")
    except Exception as e:
        if hasattr(context, 'logger') and context.logger:
            context.logger.error(f"[USER_INPUT_HANDLER] Error writing to .csv file '{USER_INPUTS_CSVFILE}': {e}")
        else:
            print(f"[USER_INPUT_HANDLER] ERROR: Error writing to .csv file '{USER_INPUTS_CSVFILE}': {e}")

    # --- Conditional Forwarding to Admin (Solution A Variant) ---
    if ADMIN_TELEGRAM_ID: # Only attempt to forward if ADMIN_TELEGRAM_ID is set
        message_lower = message_text.lower()
        # Ensure USER_MESSAGE_FORWARD_KEYWORDS is a list/iterable
        keywords_to_check = USER_MESSAGE_FORWARD_KEYWORDS if isinstance(USER_MESSAGE_FORWARD_KEYWORDS, (list, tuple, set)) else []
        
        if any(keyword.lower() in message_lower for keyword in keywords_to_check):
            try:
                forward_text = (
                    f"📥 **User Message Alert** (Keyword Triggered)\n\n"
                    f"👤 **User:** @{username} (ID: `{user_id}`)\n"
                    # f"🕒 **Time (UTC):** {timestamp_str_log}\n\n" # Optional timestamp in forward
                    f"💬 **Message:**\n`{message_text}`" # Using markdown for formatting
                )
                await context.bot.send_message(
                    chat_id=ADMIN_TELEGRAM_ID,
                    text=forward_text,
                    parse_mode='MarkdownV2' # Or 'HTML' if you prefer
                )
                if hasattr(context, 'logger') and context.logger:
                    context.logger.info(f"[ADMIN_FORWARD] Message from UserID: {user_id} (@{username}) forwarded to admin due to keyword match.")
                else:
                    print(f"[ADMIN_FORWARD] Message from UserID: {user_id} (@{username}) forwarded to admin due to keyword match.")
            except Exception as e:
                if hasattr(context, 'logger') and context.logger:
                    context.logger.error(f"[ADMIN_FORWARD] Error forwarding message to admin {ADMIN_TELEGRAM_ID}: {e}")
                else:
                    print(f"[ADMIN_FORWARD] ERROR: Error forwarding message to admin {ADMIN_TELEGRAM_ID}: {e}")
        # else: # Optional: Log if no keyword match for debugging forward logic
            # if hasattr(context, 'logger') and context.logger:
            #     context.logger.debug(f"[ADMIN_FORWARD] Message from UserID: {user_id} did not match keywords for forwarding.")
    else:
        if hasattr(context, 'logger') and context.logger:
            context.logger.warning("[ADMIN_FORWARD] ADMIN_TELEGRAM_ID not set. Cannot forward user messages.")
        else:
            print("[ADMIN_FORWARD] WARNING: ADMIN_TELEGRAM_ID not set. Cannot forward user messages.")

    # Note on further processing:
    # If this handler is meant to be a final catch-all for text messages that aren't handled by
    # more specific handlers (like ConversationHandlers or other MessageHandlers with more specific filters),
    # no further action (like `return ConversationHandler.END`) is typically needed here unless it's
    # part of such a conversation flow. For a simple, global text message logger/forwarder, this is fine.