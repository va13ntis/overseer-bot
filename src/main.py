import logging
import os
import random
import sqlite3
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters, ApplicationBuilder, CallbackContext


ADMIN_IDS = [
    int(id_str.strip())
    for id_str in os.getenv("ADMIN_IDS", "").split(",")
    if id_str.strip().isdigit()
]

KEYWORDS_DB = "keywords.db"
BOT_NAME = "@va13ntis_bot"
BOT_TOKEN = os.getenv("BOT_TOKEN")
BAN_KEYWORDS = []


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    conn = sqlite3.connect(KEYWORDS_DB)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS banned_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def add_keyword(keyword: str):
    with sqlite3.connect(KEYWORDS_DB) as conn:
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO banned_keywords (keyword) VALUES (?)", (keyword.rstrip("\r\n"),))
            conn.commit()

            return True

        except sqlite3.IntegrityError:
            return False # already exists


def remove_keyword(keyword: str):
    with sqlite3.connect(KEYWORDS_DB) as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM banned_keywords WHERE keyword = ?", (keyword.rstrip("\r\n"),))

        conn.commit()


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


def is_admin(user_id: int):
    return user_id in ADMIN_IDS


async def add_keyword_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You don't have permission.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /add_keyword <word>")
        return

    keyword = " ".join(context.args).strip().lower()
    success = add_keyword(keyword)
    if success:
        await update.message.reply_text(f"Keyword '{keyword}' added.")
    else:
        await update.message.reply_text(f"Keyword '{keyword}' already exists.")


async def remove_keyword_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You don't have permission.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /remove_keyword <word>")
        return

    keyword = " ".join(context.args).strip().lower()
    remove_keyword(keyword)
    await update.message.reply_text(f"Keyword '{keyword}' removed (if it existed).")


async def clear_keywords_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You don't have permission.")
        return


async def list_keywords_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You don't have permission.")
        return

    keywords = list_keywords()
    if keywords:
        await update.message.reply_text("Banned keywords:\n" + "\n".join(keywords))
    else:
        await update.message.reply_text("No keywords added yet.")


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Your user ID is: {user_id}")


async def handle_messages(update: Update, context: CallbackContext):
    """Let the bot react naturally to group messages"""
    message = update.message.text.lower()
    chat_id = update.message.chat_id
    user_name = update.effective_user.first_name

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


async def start(update: Update, context):
    await update.message.reply_text("Bot is running and monitoring new members.")


async def ban_message(context, update, member, chat_id):
    await context.bot.ban_chat_member(chat_id, member.id)
    await update.message.reply_text(f"Banned {member.full_name} for violating rules.")
    logger.info(f"Banned {member.username} ({member.id}) in group {chat_id}")
    return


def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("add_keyword", add_keyword_cmd))
    app.add_handler(CommandHandler("remove_keyword", remove_keyword_cmd))
    app.add_handler(CommandHandler("clear_keywords", clear_keywords_cmd))
    app.add_handler(CommandHandler("list_keywords", list_keywords_cmd))
    app.add_handler(CommandHandler("whoami", whoami))

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
