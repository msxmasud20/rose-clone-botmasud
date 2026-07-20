import os

# Telegram Bot Token (তোমার টোকেন)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8989482245:AAHK2XcjjqS6_Te84Jv3GZuNEV0STaz5BnU")

# Render Settings
PORT = int(os.getenv("PORT", "8443"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# Bot Info
BOT_NAME = "RoseGuard"
BOT_USERNAME = "roseguard_bot"

# Admin IDs (তোমার User ID)
ADMIN_IDS = [7875919383]

# Default Settings
DEFAULT_SETTINGS = {
    "welcome_enabled": True,
    "welcome_message": "👋 স্বাগতম {mention}!\n\n📋 গ্রুপের নিয়ম:\n• স্প্যাম করবে না\n• অশ্লীল কথা বলবে না\n• অননুমোদিত লিংক শেয়ার করবে না",
    "antiflood_enabled": True,
    "antiflood_limit": 5,
    "antiflood_action": "mute",
    "link_filter_enabled": True,
    "allowed_links": ["t.me"],
    "word_filter_enabled": True,
    "banned_words": ["spam", "scam", "fake", "fraud", "hack", "crack", "porn", "xxx"],
    "captcha_enabled": True,
    "captcha_timeout": 300,
}

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///rosebot.db")
