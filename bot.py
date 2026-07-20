import os
import logging
import sqlite3
import json
import random
import string
from datetime import datetime, timedelta
from functools import wraps

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8989482245:AAHK2XcjjqS6_Te84Jv3GZuNEV0STaz5BnU")
PORT = int(os.getenv("PORT", "8443"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
ADMIN_IDS = [7875919383]

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

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== DATABASE ==========
class Database:
    def __init__(self, db_path="rosebot.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                warns INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0,
                muted INTEGER DEFAULT 0,
                joined_date TEXT,
                last_active TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                group_name TEXT,
                settings TEXT,
                total_messages INTEGER DEFAULT 0,
                created_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                user_id INTEGER,
                message_type TEXT,
                timestamp TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS captcha (
                user_id INTEGER,
                group_id INTEGER,
                code TEXT,
                expires_at TEXT,
                verified INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, group_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                keyword TEXT,
                response TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username, first_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date, last_active)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, now, now))
        conn.commit()
        conn.close()
    
    def update_user_activity(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
        conn.commit()
        conn.close()
    
    def warn_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET warns = warns + 1 WHERE user_id = ?', (user_id,))
        cursor.execute('SELECT warns FROM users WHERE user_id = ?', (user_id,))
        warns = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return warns
    
    def reset_warns(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET warns = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    def get_group_settings(self, group_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT settings FROM groups WHERE group_id = ?', (group_id,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0]:
            return json.loads(result[0])
        return None
    
    def set_group_settings(self, group_id, group_name, settings):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        settings_json = json.dumps(settings)
        cursor.execute('''
            INSERT OR REPLACE INTO groups (group_id, group_name, settings, created_at)
            VALUES (?, ?, ?, ?)
        ''', (group_id, group_name, settings_json, now))
        conn.commit()
        conn.close()
    
    def log_message(self, group_id, user_id, message_type="text"):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO messages (group_id, user_id, message_type, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (group_id, user_id, message_type, now))
        cursor.execute('''
            UPDATE groups SET total_messages = total_messages + 1 WHERE group_id = ?
        ''', (group_id,))
        conn.commit()
        conn.close()
    
    def get_group_stats(self, group_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT total_messages FROM groups WHERE group_id = ?', (group_id,))
        total = cursor.fetchone()
        total_messages = total[0] if total else 0
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE group_id = ? AND date(timestamp) = ?
        ''', (group_id, today))
        today_count = cursor.fetchone()[0]
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id) FROM messages WHERE group_id = ?
        ''', (group_id,))
        active_users = cursor.fetchone()[0]
        conn.close()
        return {
            "total_messages": total_messages,
            "today_messages": today_count,
            "active_users": active_users
        }
    
    def set_captcha(self, user_id, group_id, code, expires_at):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO captcha (user_id, group_id, code, expires_at, verified)
            VALUES (?, ?, ?, ?, 0)
        ''', (user_id, group_id, code, expires_at))
        conn.commit()
        conn.close()
    
    def verify_captcha(self, user_id, group_id, code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT code, expires_at FROM captcha 
            WHERE user_id = ? AND group_id = ? AND verified = 0
        ''', (user_id, group_id))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "No pending captcha"
        stored_code, expires_at = result
        now = datetime.now().isoformat()
        if now > expires_at:
            cursor.execute('DELETE FROM captcha WHERE user_id = ? AND group_id = ?', (user_id, group_id))
            conn.commit()
            conn.close()
            return False, "Captcha expired"
        if code != stored_code:
            conn.close()
            return False, "Wrong code"
        cursor.execute('UPDATE captcha SET verified = 1 WHERE user_id = ? AND group_id = ?', (user_id, group_id))
        conn.commit()
        conn.close()
        return True, "Verified"
    
    def add_filter(self, group_id, keyword, response):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO filters (group_id, keyword, response)
            VALUES (?, ?, ?)
        ''', (group_id, keyword, response))
        conn.commit()
        conn.close()
    
    def get_filters(self, group_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT keyword, response FROM filters WHERE group_id = ?', (group_id,))
        results = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in results}
    
    def remove_filter(self, group_id, keyword):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM filters WHERE group_id = ? AND keyword = ?', (group_id, keyword))
        conn.commit()
        conn.close()

db = Database()

# ========== HELPERS ==========
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

# ========== DECORATORS ==========
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat = update.effective_chat
        if user_id in ADMIN_IDS:
            return await func(update, context)
        if chat.type in ['group', 'supergroup']:
            member = await chat.get_member(user_id)
            if member.status in ['administrator', 'creator']:
                return await func(update, context)
        await update.message.reply_text("⛔ *শুধু অ্যাডমিনরা এই কমান্ড ব্যবহার করতে পারে!*", parse_mode='Markdown')
    return wrapper

def group_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type == 'private':
            await update.message.reply_text("⚠️ এই কমান্ড শুধু গ্রুপে কাজ করে!")
            return
        return await func(update, context)
    return wrapper

# ========== HANDLERS ==========
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    settings = db.get_group_settings(chat.id)
    if not settings:
        settings = DEFAULT_SETTINGS.copy()
        db.set_group_settings(chat.id, chat.title, settings)
    if not settings.get('welcome_enabled', True):
        return
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue
        db.add_user(member.id, member.username, member.first_name)
        if settings.get('captcha_enabled', True):
            await send_captcha(update, context, member)
            return
        welcome_msg = settings.get('welcome_message', DEFAULT_SETTINGS['welcome_message'])
        welcome_msg = welcome_msg.replace('{mention}', mention_user(member))
        welcome_msg = welcome_msg.replace('{name}', member.first_name)
        welcome_msg = welcome_msg.replace('{group}', chat.title)
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def goodbye_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.message.left_chat_member
    if user.id == context.bot.id:
        return
    await update.message.reply_text(
        f"👋 {mention_user(user)} গ্রুপ ছেড়ে চলে গেলেন।\nভালো থাকবেন!",
        parse_mode='Markdown'
    )

async def send_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE, member):
    chat = update.effective_chat
    code = generate_captcha()
    expires = (datetime.now() + timedelta(minutes=5)).isoformat()
    db.set_captcha(member.id, chat.id, code, expires)
    await context.bot.restrict_chat_member(
        chat_id=chat.id,
        user_id=member.id,
        permissions={
            'can_send_messages': False,
            'can_send_media_messages': False,
            'can_send_polls': False,
            'can_send_other_messages': False,
            'can_add_web_page_previews': False
        }
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Verify", callback_data=f"captcha_{member.id}_{chat.id}")]
    ])
    await update.message.reply_text(
        f"🛡️ *Security Check*\n\n"
        f"হ্যালো {mention_user(member)}!\n\n"
        f"গ্রুপে মেসেজ পাঠানোর আগে CAPTCHA সমাধান করুন:\n"
        f"🔢 *Code: `{code}`*\n\n"
        f"⏰ 5 মিনিটের মধ্যে Verify বাটনে ক্লিক করুন।",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def verify_captcha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    user_id = int(data[1])
    group_id = int(data[2])
    if query.from_user.id != user_id:
        await query.edit_message_text("⛔ তুমি অন্যের CAPTCHA ভেরিফাই করতে পারবে না!")
        return
    await query.edit_message_text("✅ CAPTCHA Verified!\n\nএখন তুমি গ্রুপে মেসেজ পাঠাতে পারবে।")
    await context.bot.restrict_chat_member(
        chat_id=group_id,
        user_id=user_id,
        permissions={
            'can_send_messages': True,
            'can_send_media_messages': True,
            'can_send_polls': True,
            'can_send_other_messages': True,
            'can_add_web_page_previews': True
        }
    )

@admin_only
@group_only
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ কাকে ব্যান করতে চাও? মেসেজে রিপ্লাই দাও!")
        return
    target = update.message.reply_to_message.from_user
    try:
        await chat.ban_member(target.id)
        await update.message.reply_text(
            f"🔨 {mention_user(target)} কে ব্যান করা হলো!\n"
            f"কারণ: {' '.join(context.args) if context.args else 'No reason provided'}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

@admin_only
@group_only
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ কাকে আনব্যান করতে চাও? মেসেজে রিপ্লাই দাও!")
        return
    target = update.message.reply_to_message.from_user
    try:
        await chat.unban_member(target.id)
        await update.message.reply_text(f"✅ {mention_user(target)} কে আনব্যান করা হলো!", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

@admin_only
@group_only
async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ কাকে মিউট করতে চাও? মেসেজে রিপ্লাই দাও!")
        return
    target = update.message.reply_to_message.from_user
    duration = 60
    if context.args:
        try:
            duration = int(context.args[0])
        except:
            pass
    until_date = datetime.now() + timedelta(minutes=duration)
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target.id,
            until_date=until_date,
            permissions={'can_send_messages': False, 'can_send_media_messages': False}
        )
        await update.message.reply_text(
            f"🔇 {mention_user(target)} কে {format_time(duration * 60)} এর জন্য মিউট করা হলো!",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

@admin_only
@group_only
async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ কাকে কিক করতে চাও? মেসেজে রিপ্লাই দাও!")
        return
    target = update.message.reply_to_message.from_user
    try:
        await chat.ban_member(target.id)
        await chat.unban_member(target.id)
        await update.message.reply_text(f"👢 {mention_user(target)} কে কিক করা হলো!", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

@admin_only
@group_only
async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ কাকে ওয়ার্ন করতে চাও? মেসেজে রিপ্লাই দাও!")
        return
    target = update.message.reply_to_message.from_user
    warns = db.warn_user(target.id)
    reason = ' '.join(context.args) if context.args else "No reason"
    if warns >= 3:
        await update.effective_chat.ban_member(target.id)
        await update.message.reply_text(
            f"⚠️ {mention_user(target)} এর ৩টি ওয়ার্নিং পূর্ণ!\n🔨 অটো ব্যান করা হলো!\nকারণ: {reason}",
            parse_mode='Markdown'
        )
        db.reset_warns(target.id)
    else:
        await update.message.reply_text(
            f"⚠️ {mention_user(target)} কে ওয়ার্ন করা হলো!\nমোট ওয়ার্নিং: {warns}/3\nকারণ: {reason}",
            parse_mode='Markdown'
        )

@admin_only
@group_only
async def unwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ কার ওয়ার্ন রিসেট করতে চাও?")
        return
    target = update.message.reply_to_message.from_user
    db.reset_warns(target.id)
    await update.message.reply_text(f"✅ {mention_user(target)} এর সব ওয়ার্নিং মুছে ফেলা হলো!", parse_mode='Markdown')

async def message_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    message = update.message
    if not message or not message.text:
        return
    db.log_message(chat.id, user.id)
    db.update_user_activity(user.id)
    settings = db.get_group_settings(chat.id)
    if not settings:
        settings = DEFAULT_SETTINGS.copy()
        db.set_group_settings(chat.id, chat.title, settings)
    text = message.text.lower()
    if settings.get('link_filter_enabled', True):
        if contains_link(text):
            allowed = settings.get('allowed_links', ['t.me'])
            if not any(link in text for link in allowed):
                await message.delete()
                await message.reply_text(
                    f"🚫 {user.mention_html()}!\nঅননুমোদিত লিংক শেয়ার করা নিষেধ!",
                    parse_mode='HTML'
                )
                return
    if settings.get('word_filter_enabled', True):
        banned_words = settings.get('banned_words', get_banned_words())
        for word in banned_words:
            if word.lower() in text:
                await message.delete()
                await message.reply_text(
                    f"🚫 {user.mention_html()}!\nনিষিদ্ধ শব্দ ব্যবহার করা যাবে না!",
                    parse_mode='HTML'
                )
                return
    filters = db.get_filters(chat.id)
    for keyword, response in filters.items():
        if keyword.lower() in text:
            await message.reply_text(response)
            return

async def add_filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: `/filter <keyword> <response>`", parse_mode='Markdown')
        return
    keyword = context.args[0]
    response = ' '.join(context.args[1:])
    db.add_filter(chat.id, keyword, response)
    await update.message.reply_text(
        f"✅ ফিল্টার যোগ করা হলো!\n🔤 Keyword: `{keyword}`\n💬 Response: {response}",
        parse_mode='Markdown'
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    else:
        target = update.effective_user
    user_id = target.id
    await update.message.reply_text(
        f"👤 *User Info*\n\n🆔 ID: `{user_id}`\n👤 Name: {target.first_name}\n🔗 Username: @{target.username or 'N/A'}\n📊 Status: {'Admin' if user_id in ADMIN_IDS else 'Member'}",
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    stats = db.get_group_stats(chat.id)
    await update.message.reply_text(
        f"📊 *Group Statistics*\n\n💬 Total Messages: {stats['total_messages']}\n📅 Today's Messages: {stats['today_messages']}\n👥 Active Users: {stats['active_users']}\n\n📈 Keep chatting!",
        parse_mode='Markdown'
    )

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    await update.message.reply_text(
        f"🆔 *Your ID:* `{user.id}`\n💬 *Chat ID:* `{chat.id}`",
        parse_mode='Markdown'
    )

@admin_only
@group_only
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    settings = db.get_group_settings(chat.id)
    if not settings:
        settings = DEFAULT_SETTINGS.copy()
        db.set_group_settings(chat.id, chat.title, settings)
    welcome_status = "✅" if settings.get('welcome_enabled') else "❌"
    captcha_status = "✅" if settings.get('captcha_enabled') else "❌"
    link_status = "✅" if settings.get('link_filter_enabled') else "❌"
    word_status = "✅" if settings.get('word_filter_enabled') else "❌"
    await update.message.reply_text(
        f"⚙️ *Group Settings*\n\n👋 Welcome: {welcome_status}\n🛡️ Captcha: {captcha_status}\n🔗 Link Filter: {link_status}\n🚫 Word Filter: {word_status}\n\nUse /setwelcome to change.",
        parse_mode='Markdown'
    )

@admin_only
@group_only
async def setwelcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: `/setwelcome <message>`\nVariables: {mention}, {name}, {group}",
            parse_mode='Markdown'
        )
        return
    welcome_msg = ' '.join(context.args)
    settings = db.get_group_settings(chat.id) or DEFAULT_SETTINGS.copy()
    settings['welcome_message'] = welcome_msg
    db.set_group_settings(chat.id, chat.title, settings)
    await update.message.reply_text(
        f"✅ Welcome message updated!\n\nPreview:\n{welcome_msg}",
        parse_mode='Markdown'
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌹 *RoseGuard Bot*\n\n"
        "আমি একটা প্রফেশনাল গ্রুপ ম্যানেজমেন্ট বট।\n"
        "আমাকে তোমার গ্রুপে অ্যাডমিন হিসেবে যোগ করো!\n\n"
        "📋 *Commands:*\n"
        "/help - সব কমান্ড দেখো\n"
        "/settings - সেটিংস\n\n"
        "⚡️ *Features:*\n"
        "• Anti-Spam\n"
        "• CAPTCHA\n"
        "• Link Filter\n"
        "• Word Filter\n"
        "• Auto Welcome\n"
        "• Admin Tools",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *RoseGuard Commands*\n\n"
        "*User Commands:*\n"
        "/start - বট শুরু\n"
        "/help - সাহায্য\n"
        "/id - আইডি দেখো\n"
        "/info - ইউজার ইনফো\n"
        "/stats - গ্রুপ স্ট্যাটস\n\n"
        "*Admin Commands:*\n"
        "/ban - ব্যান (রিপ্লাই)\n"
        "/unban - আনব্যান\n"
        "/mute - মিউট (রিপ্লাই)\n"
        "/kick - কিক (রিপ্লাই)\n"
        "/warn - ওয়ার্ন (রিপ্লাই)\n"
        "/unwarn - ওয়ার্ন রিসেট\n"
        "/settings - সেটিংস\n"
        "/setwelcome - ওয়েলকাম সেট\n"
        "/filter - কাস্টম ফিল্টার"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ কিছু একটা ভুল হয়েছে!")

# ========== MAIN ==========
def main():
    logger.info("🌹 RoseGuard Bot starting...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("kick", kick_command))
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CommandHandler("unwarn", unwarn_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("setwelcome", setwelcome_command))
    application.add_handler(CommandHandler("filter", add_filter_command))
    
    application.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_member))
    
    application.add_handler(CallbackQueryHandler(verify_captcha_callback, pattern="^captcha_"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_filter))
    
    application.add_error_handler(error_handler)
    
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
        logger.info(f"🌐 Webhook: {webhook_url}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=webhook_url,
            secret_token=BOT_TOKEN
        )
    else:
        logger.info("🔄 Polling mode...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
