# Config constants for XAutomation

# Delay between sending messages in seconds (10 minutes = 600)
MESSAGE_DELAY_SECONDS = 600

# OpenRouter AI settings (can be overridden from the UI)
OPENROUTER_API_KEY = ""
OPENROUTER_MODEL = ""

# Base URL
TWITTER_BASE_URL = "https://x.com"

# Default files
DEFAULT_INPUT_FILE = "input.xlsx"

# Playwright Selectors
SELECTORS = {
    # Profile "Message" button
    "dm_button": "[data-testid='sendDMFromProfile']",

    # DM Composer — try both the testid and the placeholder
    # Twitter's DM box is a contenteditable div
    "dm_textbox": "div[data-testid='dmComposerTextInput']",
    "dm_textbox_role": "div[role='textbox'][data-testid='dmComposerTextInput']",
    "dm_send_button": "[data-testid='dmComposerSendButton']",

    # Message thread entries (for reply detection)
    "message_entry": "[data-testid='messageEntry']",
}
