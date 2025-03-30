from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import logging
import os
import time

BOT_TOKEN = os.getenv("BOT_TOKEN")
BAN_KEYWORDS = []


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_keywords():
    with open("keywords.txt", mode="r", encoding="utf-8") as keywords_file:
        for keyword in keywords_file:
            BAN_KEYWORDS.append(keyword.rstrip("\r\n"))

    logger.info(f"Ban keywords: {BAN_KEYWORDS}")


async def check_new_members(update: Update, context):
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

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, check_new_members))

    logger.info("Bot started...")

    while True:
        try:
            app.run_polling()
        except Exception as e:
            print(f"Bot crashed: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
