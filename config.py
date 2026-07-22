import os
from dotenv import load_dotenv

# ==================================================
# Load Environment Variables
# ==================================================

load_dotenv()

# ==================================================
# Project Information
# ==================================================

BOT_NAME = "Project Judy"
BOT_VERSION = "1.3.0"

# ==================================================
# Discord
# ==================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# ==================================================
# Gemini AI
# ==================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ==================================================
# Embed Colors
# ==================================================

COLOR_SUCCESS = 0x57F287
COLOR_WARNING = 0xFEE75C
COLOR_ERROR = 0xED4245
COLOR_INFO = 0x5865F2
