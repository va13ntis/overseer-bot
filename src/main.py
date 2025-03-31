import logging
import os
import random
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import CommandHandler, MessageHandler, filters, ApplicationBuilder, CallbackContext


BOT_NAME = "@va13ntis_bot"
BOT_TOKEN = os.getenv("BOT_TOKEN")
BAN_KEYWORDS = []


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_keywords():
    with open("keywords.txt", mode="r", encoding="utf-8") as keywords_file:
        for keyword in keywords_file:
            BAN_KEYWORDS.append(keyword.rstrip("\r\n"))

    logger.info(f"Ban keywords: {BAN_KEYWORDS}")


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
    get_keywords()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

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
