from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils.decorators import admin_only, group_only
from utils.helpers import mention_user, format_time
from datetime import datetime, timedelta

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
        await update.message.reply_text(
            f"✅ {mention_user(target)} কে আনব্যান করা হলো!",
            parse_mode='Markdown'
        )
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
            permissions={
                'can_send_messages': False,
                'can_send_media_messages': False
            }
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
        
        await update.message.reply_text(
            f"👢 {mention_user(target)} কে কিক করা হলো!",
            parse_mode='Markdown'
        )
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
            f"⚠️ {mention_user(target)} এর ৩টি ওয়ার্নিং পূর্ণ!\n"
            f"🔨 অটো ব্যান করা হলো!\n"
            f"কারণ: {reason}",
            parse_mode='Markdown'
        )
        db.reset_warns(target.id)
    else:
        await update.message.reply_text(
            f"⚠️ {mention_user(target)} কে ওয়ার্ন করা হলো!\n"
            f"মোট ওয়ার্নিং: {warns}/3\n"
            f"কারণ: {reason}",
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
    
    await update.message.reply_text(
        f"✅ {mention_user(target)} এর সব ওয়ার্নিং মুছে ফেলা হলো!",
        parse_mode='Markdown'
      )
