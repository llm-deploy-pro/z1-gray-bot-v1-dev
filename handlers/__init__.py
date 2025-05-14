# handlers/__init__.py

# Re-export constants for easier access and to decouple start_bot.py from specific step modules.

# From Step 1 (if any constants from step_1 were needed by start_bot, they'd go here)
# e.g., from .step_1 import SOME_STEP_1_CALLBACK_CONSTANT

# From Step 2 (constants needed by start_bot for Step 3 registration)
from .step_2 import CALLBACK_S3_VIEW_DIAGNOSIS

# From Step 3 (example for future steps)
# from .step_3 import CALLBACK_S4_ENTRY_EXAMPLE # Assuming this would be defined in step_3.py

# You can also re-export flow state constants if they are used across modules
# or in the main application logic, though typically callback data is more common here.
# from .step_2 import STEP_2_SCAN_COMPLETE_AWAITING_S3

__all__ = [
    'CALLBACK_S3_VIEW_DIAGNOSIS',
    # 'CALLBACK_S4_ENTRY_EXAMPLE', # Uncomment when Step 4 is added
    # 'STEP_2_SCAN_COMPLETE_AWAITING_S3', # Uncomment if needed elsewhere
]