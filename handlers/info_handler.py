from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils.helpers import mention_user

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    else:
        target = update.effective_user
    
    user_id = target.id
    
    await update.message.reply_text(
        f"👤 *User Info*\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"👤 Name: {target.first_name}\n"
        f"🔗 Username: @{target.username or 'N/A'}\n"
        f"📊 Status: {'Admin' if user_id in [7875919383] else 'Member'}",
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    
    stats = db.get_group_stats(chat.id)
    
    await update.message.reply_text(
        f"📊 *Group Statistics*\n\n"
        f"💬 Total Messages: {stats['total_messages']}\n"
        f"📅 Today's Messages: {stats['today_messages']}\n"
        f"👥 Active Users: {stats['active_users']}\n\n"
        f"📈 Keep chatting!",
        parse_mode='Markdown'
    )

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    
    await update.message.reply_text(
        f"🆔 *Your ID:* `{user.id}`\n"
        f"💬 *Chat ID:* `{chat.id}`",
        parse_mode='Markdown'
  )
