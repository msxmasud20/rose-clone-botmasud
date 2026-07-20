import random
import string
from datetime import datetime, timedelta

def generate_captcha():
    return ''.join(random.choices(string.digits, k=6))

def mention_user(user):
    if user.username:
        return f"@{user.username}"
    return f"[{user.first_name}](tg://user?id={user.id})"

def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0:
        parts.append(f"{secs}s")
    
    return " ".join(parts) if parts else "0s"

def get_banned_words():
    return ["spam", "scam", "fake", "fraud", "hack", "crack", "porn", "xxx"]

def contains_link(text):
    link_indicators = ['http://', 'https://', 'www.', '.com', '.net', '.org', 't.me/']
    return any(indicator in text.lower() for indicator in link_indicators)
