import logging
import os
import random
import sqlite3
import time

from telegram import Update, ChatMemberAdministrator, ChatMemberOwner, InlineKeyboardMarkup, InlineKeyboardButton, \
    ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ChatAction
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters, ApplicationBuilder, CallbackContext, \
    CallbackQueryHandler, ConversationHandler

ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
KEYWORDS_DB = "keywords.db"
BOT_NAME = "@va13ntis_bot"
BOT_TOKEN = os.getenv("BOT_TOKEN")
BAN_KEYWORDS = []
ADD_KEYWORD, REMOVE_KEYWORD = range(2)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    with sqlite3.connect(KEYWORDS_DB) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS banned_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE NOT NULL
            )
        """)

        conn.commit()

        cursor.execute("SELECT keyword FROM banned_keywords")

        rows = cursor.fetchall()

    for keyword in [row[0] for row in rows]:
        BAN_KEYWORDS.append(keyword.rstrip("\r\n"))

    logger.info(f"Ban keywords: {BAN_KEYWORDS}")


def add_keyword_to_db(keyword: str):
    with sqlite3.connect(KEYWORDS_DB) as conn:
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO banned_keywords (keyword) VALUES (?)", (keyword.rstrip("\r\n"),))
            conn.commit()

            return True

        except sqlite3.IntegrityError:
            return False # already exists


def remove_keyword_from_db(keyword: str):
    with sqlite3.connect(KEYWORDS_DB) as conn:
        try:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM banned_keywords WHERE keyword = ?", (keyword.rstrip("\r\n"),))

            conn.commit()

            return  True
        except sqlite3.IntegrityError:
            return False # not found


def clear_keywords():
    with sqlite3.connect(KEYWORDS_DB) as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM banned_keywords")

        conn.commit()


def list_keywords():
    with sqlite3.connect(KEYWORDS_DB) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT keyword FROM banned_keywords")

        rows = cursor.fetchall()

    return [row[0] for row in rows]


def menu_reply_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📋 Menu")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


async def is_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        admins = await context.bot.get_chat_administrators(ADMIN_GROUP_ID)
        return any(admin.user.id == user_id for admin in admins)
    except Exception as e:
        print(f"Failed to verify admin: {e}")
        return False

async def handle_add_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip()
    if not keyword:
        await update.message.reply_text("⚠️ Keyword can't be empty.")
        return ADD_KEYWORD

    add_keyword_to_db(keyword)
    await update.message.reply_text(f"✅ Keyword '{keyword}' added.")
    return ConversationHandler.END


async def handle_remove_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip()
    if not keyword:
        await update.message.reply_text("⚠️ Keyword can't be empty.")
        return REMOVE_KEYWORD

    removed = remove_keyword_from_db(keyword)
    if removed:
        await update.message.reply_text(f"🗑️ Keyword '{keyword}' removed.")
    else:
        await update.message.reply_text(f"❌ Keyword '{keyword}' not found.")
    return ConversationHandler.END


async def clear_keywords_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id, context):
        await update.message.reply_text("🚫 Sorry, you’re not authorized to use this admin panel.")
        return


async def handle_messages(update: Update, context: CallbackContext):
    """Let the bot react naturally to group messages"""
    message = update.message.text.lower()
    chat_id = update.message.chat_id
    user_name = update.effective_user.first_name

    logger.info(f"Received message from user {user_name} in {chat_id}")

    # Simulate "thinking..."
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    time.sleep(random.uniform(1, 3))

    # Bot responds if someone mentions it
    if BOT_NAME in message:
        responses = [
            f"А, {user_name}, к вашим услугам. ☕",
            "Чудненько, сделаем сию секунду! 🎩",
            "Кто там?",
            "Разрешите вставить ремарку..."
        ]

        await update.message.reply_text(random.choice(responses))

    # React if someone mentions tea 🍵
    elif "привет" in message:
        await update.message.reply_text("И вам не хворать...")


async def handle_new_members(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id  # Get the group ID dynamically
    for member in update.message.new_chat_members:
        for keyword in BAN_KEYWORDS:
            if member.name and keyword.lower() in member.name.lower():
                await ban_message(context, update, member, chat_id)
                return
            elif member.full_name and keyword.lower() in member.full_name.lower():
                await ban_message(context, update, member, chat_id)
                return
            elif member.first_name and keyword.lower() in member.first_name.lower():
                await ban_message(context, update, member, chat_id)
                return
            elif member.last_name and keyword.lower() in member.last_name.lower():
                await ban_message(context, update, member, chat_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 Hello, {update.effective_user}! I'm Overseer.\nTap '📋 Menu' to get started!",
        reply_markup=menu_reply_keyboard()
    )


async def ban_message(context, update, member, chat_id):
    await context.bot.ban_chat_member(chat_id, member.id)
    await update.message.reply_text(f"Banned {member.full_name} for violating rules.")
    logger.info(f"Banned {member.username} ({member.id}) in group {chat_id}")
    return


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    # Only allow in private chat
    if chat.type != "private":
        await update.message.reply_text("⚠️ Please use this command in private chat.")
        return

    # Check if user is admin in your group
    if not await is_admin(user.id, context):
        await update.message.reply_text("🚫 You’re not allowed to access this menu.")
        return

    # Build the menu
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add Keyword", callback_data="add_keyword"),
            InlineKeyboardButton("➖ Remove Keyword", callback_data="remove_keyword"),
        ],
        [
            InlineKeyboardButton("📋 List Keywords", callback_data="list_keywords"),
        ]
    ])

    await update.message.reply_text("Welcome, Admin 👋\nWhat would you like to do?", reply_markup=keyboard)


async def handle_admin_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not await is_admin(user_id, context):
        await query.edit_message_text("🚫 Access denied.")
        return ConversationHandler.END

    action = query.data
    context.user_data["admin_action"] = action  # store the action in user_data

    if action == "add_keyword":
        await query.edit_message_text(
            "📝 Please send the keyword you'd like to *add*.",
            parse_mode="Markdown",
            reply_markup=back_to_menu_keyboard())
        return ADD_KEYWORD
    elif action == "remove_keyword":
        await query.edit_message_text(
            "🧹 Please send the keyword you'd like to *remove*.",
            parse_mode="Markdown",
            reply_markup=back_to_menu_keyboard())
        return REMOVE_KEYWORD
    elif action == "list_keywords":
        keywords = list_keywords()
        if keywords:
            keyword_list = "\n• " + "\n• ".join(keywords)
            await query.edit_message_text(f"📋 Current keywords:\n{keyword_list}")
        else:
            await query.edit_message_text("📋 No keywords found.")
        return ConversationHandler.END


def back_to_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
    ])


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_admin_menu_callback)],
    states={
        ADD_KEYWORD: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
                handle_add_keyword
            )
        ],
        REMOVE_KEYWORD: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
                handle_remove_keyword
            )
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & filters.Regex("^📋 Menu$"),
        admin_menu
    ))

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))

    # Ban unwanted users when they join
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))

    # Listen for chat messages and engage in conversations
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    logger.info("Bot started...")

    while True:
        try:
            app.run_polling()
        except Exception as e:
            print(f"Bot crashed: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
