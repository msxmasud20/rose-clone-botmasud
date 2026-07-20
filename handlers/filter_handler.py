from telegram import Update
from telegram.ext import ContextTypes
from database import db
from config import DEFAULT_SETTINGS
from utils.helpers import contains_link, get_banned_words

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
                    f"🚫 {user.mention_html()}!\n"
                    f"অননুমোদিত লিংক শেয়ার করা নিষেধ!",
                    parse_mode='HTML'
                )
                return
    
    if settings.get('word_filter_enabled', True):
        banned_words = settings.get('banned_words', get_banned_words())
        for word in banned_words:
            if word.lower() in text:
                await message.delete()
                await message.reply_text(
                    f"🚫 {user.mention_html()}!\n"
                    f"নিষিদ্ধ শব্দ ব্যবহার করা যাবে না!",
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
        await update.message.reply_text(
            "⚠️ Usage: `/filter <keyword> <response>`",
            parse_mode='Markdown'
        )
        return
    
    keyword = context.args[0]
    response = ' '.join(context.args[1:])
    
    db.add_filter(chat.id, keyword, response)
    
    await update.message.reply_text(
        f"✅ ফিল্টার যোগ করা হলো!\n"
        f"🔤 Keyword: `{keyword}`\n"
        f"💬 Response: {response}",
        parse_mode='Markdown'
    )
