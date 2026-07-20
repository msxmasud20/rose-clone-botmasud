from telegram import Update
from telegram.ext import ContextTypes
from database import db
from config import DEFAULT_SETTINGS
from utils.helpers import mention_user

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
            from handlers.captcha_handler import send_captcha
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
        f"👋 {mention_user(user)} গ্রুপ ছেড়ে চলে গেলেন।\n"
        f"ভালো থাকবেন!",
        parse_mode='Markdown'
    )
