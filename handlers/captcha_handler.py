from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from database import db
from utils.helpers import generate_captcha, mention_user

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
    
    await query.edit_message_text(
        "✅ CAPTCHA Verified!\n\n"
        "এখন তুমি গ্রুপে মেসেজ পাঠাতে পারবে।"
    )
    
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
