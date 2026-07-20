import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from config import BOT_TOKEN, PORT, RENDER_EXTERNAL_URL
from database import db

from handlers.greeting_handler import welcome_new_member, goodbye_member
from handlers.captcha_handler import verify_captcha_callback
from handlers.admin_handler import (
    ban_command, unban_command, mute_command, 
    kick_command, warn_command, unwarn_command
)
from handlers.filter_handler import message_filter, add_filter_command
from handlers.info_handler import info_command, stats_command, id_command
from handlers.settings_handler import settings_command, setwelcome_command

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
