from telegram import Update
from telegram.ext import ContextTypes
from database import db
from config import DEFAULT_SETTINGS
from utils.decorators import admin_only, group_only

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
        f"⚙️ *Group Settings*\n\n"
        f"👋 Welcome: {welcome_status}\n"
        f"🛡️ Captcha: {captcha_status}\n"
        f"🔗 Link Filter: {link_status}\n"
        f"🚫 Word Filter: {word_status}\n\n"
        f"Use /setwelcome, /togglecaptcha, etc. to change.",
        parse_mode='Markdown'
    )

@admin_only
@group_only
async def setwelcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: `/setwelcome <message>`\n"
            "Variables: {mention}, {name}, {group}",
            parse_mode='Markdown'
        )
        return
    
    welcome_msg = ' '.join(context.args)
    
    settings = db.get_group_settings(chat.id) or DEFAULT_SETTINGS.copy()
    settings['welcome_message'] = welcome_msg
    db.set_group_settings(chat.id, chat.title, settings)
    
    await update.message.reply_text(
        "✅ Welcome message updated!\n\n"
        f"Preview:\n{welcome_msg}",
        parse_mode='Markdown'
    )
