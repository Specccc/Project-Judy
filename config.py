import os
from pathlib import Path

from dotenv import load_dotenv


# ==================================================
# Project Paths
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"

ASSETS_FOLDER = PROJECT_ROOT / "assets"
COGS_FOLDER = PROJECT_ROOT / "cogs"
DATABASE_FOLDER = PROJECT_ROOT / "database"
MEMORY_FOLDER = PROJECT_ROOT / "memory"
PROMPTS_FOLDER = PROJECT_ROOT / "prompts"

AMBIENT_RESPONSES_FILE = (
    ASSETS_FOLDER / "ambient_responses.json"
)

CONVERSATION_MEMORY_FILE = (
    MEMORY_FOLDER / "conversation_cache.json"
)

JUDY_MEMORY_FILE = (
    MEMORY_FOLDER / "judy_memory.json"
)

AI_SYSTEM_PROMPT_FILE = (
    PROMPTS_FOLDER / "system_prompt.txt"
)

CORE_DATABASE_FILE = DATABASE_FOLDER / "judy.db"
CHAT_DATABASE_FILE = DATABASE_FOLDER / "chat.db"
AMBIENT_DATABASE_FILE = DATABASE_FOLDER / "ambient.db"
XP_DATABASE_FILE = DATABASE_FOLDER / "xp.db"
MODERATION_DATABASE_FILE = (
    DATABASE_FOLDER / "moderation.db"
)
GUILD_DATABASE_FILE = DATABASE_FOLDER / "guilds.db"


# ==================================================
# Environment
# ==================================================

load_dotenv(ENV_FILE)


# ==================================================
# Project Information
# ==================================================

BOT_NAME = "Project Judy"
BOT_VERSION = "2.0.0"
COMMAND_PREFIX = "!"

PROJECT_REPOSITORY_URL = (
    "https://github.com/Specccc/Project-Judy"
)

PRIVACY_POLICY_URL = (
    f"{PROJECT_REPOSITORY_URL}/blob/main/"
    "privacy-policy.md"
)

TERMS_OF_SERVICE_URL = (
    f"{PROJECT_REPOSITORY_URL}/blob/main/"
    "terms-of-service.md"
)

SUPPORT_URL = (
    f"{PROJECT_REPOSITORY_URL}/issues"
)


# ==================================================
# API Keys
# ==================================================

DISCORD_TOKEN = os.getenv(
    "DISCORD_TOKEN",
    ""
).strip()

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()

SERPER_API_KEY = os.getenv(
    "SERPER_API_KEY",
    ""
).strip()


# ==================================================
# Gemini
# ==================================================

GEMINI_CHAT_MODEL = os.getenv(
    "GEMINI_CHAT_MODEL",
    "gemini-3.5-flash"
).strip()

GEMINI_AMBIENT_MODEL = os.getenv(
    "GEMINI_AMBIENT_MODEL",
    GEMINI_CHAT_MODEL
).strip()

AI_REQUEST_TIMEOUT_SECONDS = 45
AI_MAX_CONCURRENT_REQUESTS = 2
AI_MAX_RETRIES = 2
AI_RETRY_DELAY_SECONDS = 1
AI_MAX_INPUT_CHARACTERS = 16000
AI_CHAT_MESSAGE_MAX_CHARACTERS = 4000
AI_CONVERSATION_MAX_CHARACTERS = 5000
AI_MEMORY_MAX_CHARACTERS = 2000
AI_AMBIENT_MESSAGE_MAX_CHARACTERS = 1000


# ==================================================
# Chat
# ==================================================

CHAT_HISTORY_LIMIT = 20
CHAT_MAX_REPLY_LENGTH = 2000
CHAT_USER_COOLDOWN_SECONDS = 6
CHAT_GUILD_COOLDOWN_SECONDS = 2

CHAT_ERROR_MESSAGE = (
    "Something shorted out on my end. "
    "Give it a second, choom."
)


# ==================================================
# Memory
# ==================================================

MEMORY_MAX_CONVERSATION_MESSAGES = 20
MEMORY_MAX_FACT_LENGTH = 1000
MEMORY_MAX_FACTS_PER_USER = 50


# ==================================================
# Ambient Presence
# ==================================================

AMBIENT_SERVER_COOLDOWN_SECONDS = 300
AMBIENT_USER_COOLDOWN_SECONDS = 1800

AMBIENT_REACTION_WEIGHT = 72
AMBIENT_TEXT_WEIGHT = 20
AMBIENT_GIF_WEIGHT = 7
AMBIENT_GEMINI_WEIGHT = 1

AMBIENT_ACTION_WEIGHTS = {
    "reaction": AMBIENT_REACTION_WEIGHT,
    "text": AMBIENT_TEXT_WEIGHT,
    "gif": AMBIENT_GIF_WEIGHT,
    "gemini": AMBIENT_GEMINI_WEIGHT
}

AMBIENT_TRIGGER_PROBABILITIES = {
    2: 0.08,
    3: 0.14,
    4: 0.20,
    5: 0.28
}


# ==================================================
# XP
# ==================================================

XP_COOLDOWN_SECONDS = 60
XP_MINIMUM_AWARD = 15
XP_MAXIMUM_AWARD = 25
XP_BASE_REQUIREMENT = 100


# ==================================================
# Image Search
# ==================================================

IMAGE_SEARCH_COUNTRY = "za"
IMAGE_SEARCH_LANGUAGE = "en"
IMAGE_SEARCH_MAX_RESULTS = 10
IMAGE_CACHE_SECONDS = 3600
IMAGE_COMMAND_COOLDOWN_SECONDS = 10


# ==================================================
# Moderation
# ==================================================

MODERATION_MAX_WARNING_RESULTS = 20
MODERATION_MAX_TIMEOUT_DAYS = 28
MODERATION_MAX_PURGE_MESSAGES = 100


# ==================================================
# Colors
# ==================================================

COLOR_SUCCESS = 0x57F287
COLOR_WARNING = 0xFEE75C
COLOR_ERROR = 0xED4245
COLOR_INFO = 0x5865F2
COLOR_JUDY = 0x6B4EFF


# ==================================================
# Validation
# ==================================================

def validate_configuration():
    errors = []
    warnings = []

    if not DISCORD_TOKEN:
        errors.append(
            "DISCORD_TOKEN is missing."
        )

    if not GEMINI_API_KEY:
        errors.append(
            "GEMINI_API_KEY is missing."
        )

    if not SERPER_API_KEY:
        warnings.append(
            "SERPER_API_KEY is missing. "
            "Image search will use Wikimedia."
        )

    if not AMBIENT_RESPONSES_FILE.exists():
        warnings.append(
            "assets/ambient_responses.json "
            "was not found."
        )

    if not AI_SYSTEM_PROMPT_FILE.exists():
        warnings.append(
            "prompts/system_prompt.txt was not found. "
            "The built-in fallback prompt will be used."
        )

    if sum(
        AMBIENT_ACTION_WEIGHTS.values()
    ) <= 0:
        errors.append(
            "All ambient interaction weights are zero."
        )

    if AI_MAX_CONCURRENT_REQUESTS <= 0:
        errors.append(
            "AI_MAX_CONCURRENT_REQUESTS must be positive."
        )

    if AI_REQUEST_TIMEOUT_SECONDS <= 0:
        errors.append(
            "AI_REQUEST_TIMEOUT_SECONDS must be positive."
        )

    return errors, warnings


def safe_configuration_summary():
    return {
        "bot_name": BOT_NAME,
        "bot_version": BOT_VERSION,
        "chat_model": GEMINI_CHAT_MODEL,
        "ambient_model": GEMINI_AMBIENT_MODEL,
        "ai_timeout_seconds": (
            AI_REQUEST_TIMEOUT_SECONDS
        ),
        "ai_max_concurrency": (
            AI_MAX_CONCURRENT_REQUESTS
        ),
        "chat_history_limit": CHAT_HISTORY_LIMIT,
        "ambient_server_cooldown": (
            AMBIENT_SERVER_COOLDOWN_SECONDS
        ),
        "ambient_user_cooldown": (
            AMBIENT_USER_COOLDOWN_SECONDS
        ),
        "ambient_weights": dict(
            AMBIENT_ACTION_WEIGHTS
        ),
        "xp_cooldown": XP_COOLDOWN_SECONDS,
        "xp_award_range": (
            XP_MINIMUM_AWARD,
            XP_MAXIMUM_AWARD
        ),
        "image_max_results": (
            IMAGE_SEARCH_MAX_RESULTS
        ),
        "image_cache_seconds": (
            IMAGE_CACHE_SECONDS
        ),
        "discord_token_loaded": bool(
            DISCORD_TOKEN
        ),
        "gemini_key_loaded": bool(
            GEMINI_API_KEY
        ),
        "serper_key_loaded": bool(
            SERPER_API_KEY
        )
    }
