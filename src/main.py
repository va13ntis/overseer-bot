import logging
import os
import time
from string import Template

import requests
from telegram import Update
from telegram.ext import MessageHandler, filters, ApplicationBuilder, CallbackContext

POLL_INTERVAL = float(os.getenv("BOT_POLL_INTERVAL", 10.0))
BOT_TOKEN = os.getenv("BOT_TOKEN")
BAN_KEYWORDS = []
PUBLIC_PROFILE_TEMPLATE = Template("https://t.me/$username")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_keywords():
    with open("keywords.txt", mode="r", encoding="utf-8") as keywords_file:
        for keyword in keywords_file:
            BAN_KEYWORDS.append(keyword.rstrip("\r\n"))

    logger.info(f"Ban keywords: {BAN_KEYWORDS}")


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
                return

        # Fallback: check public profile
        if not is_allowed_public_profile(member.username):
            await ban_message(context, update, member, chat_id)
            return

async def start(update: Update, context):
    await update.message.reply_text("Bot is running and monitoring new members.")


async def ban_message(context, update, member, chat_id):
    await context.bot.ban_chat_member(chat_id, member.id)
    await update.message.reply_text(f"Banned {member.full_name} for violating rules.")
    logger.info(f"Banned {member.username} ({member.id}) in group {chat_id}")
    return


def is_allowed_public_profile(username):
    is_allowed = True

    try:
        response = requests.get(PUBLIC_PROFILE_TEMPLATE.substitute(username=username))

        if response.status_code == 200 and response.text and is_ban_word(response.text):
            is_allowed = False
    except Exception as e:
        logger.error(e)
        is_allowed = False

    return is_allowed


def is_ban_word(content):
    return any(substring.casefold() in content.casefold() for substring in BAN_KEYWORDS)


def main():
    get_keywords()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Ban unwanted users when they join
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))

    logger.info("Bot started...")

    while True:
        try:
            app.run_polling(poll_interval=POLL_INTERVAL)
        except Exception as e:
            print(f"Bot crashed: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
