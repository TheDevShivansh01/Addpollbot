import re
import os
import pandas as pd
import nest_asyncio
import asyncio
from telegram import InputFile
from telethon import TelegramClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Your Telegram API credentials (from my.telegram.org)
API_ID = 21993163
API_HASH = '7fce093ad6aaf5508e00a0ce6fdf1d8c'
INVITE_LINK = "https://t.me/+HGAKyuyr50kyMDNl"  # The group/channel to fetch polls from

nest_asyncio.apply()  # To run async inside sync

# Telethon client session name
SESSION_NAME = 'session_name2'

def clean_question(quest):
    return re.sub(r'^\[\d+/\d+\]\s*', '', quest)

def parse_poll(poll_message):
    poll = poll_message.poll  # Extract poll object
    poll_text = str(poll)
    ques_pattern = r"question=TextWithEntities\(text='(.*?)', entities=\[\]\),"
    answer_pattern = r"PollAnswerVoters\(option=b'(\d)', voters=\d+, chosen=(?:True|False), correct=True\)"
    option_pattern = r"text=TextWithEntities\(text='(.*?)', entities=\[\]\), option=b'(\d)'"
    id_pattern = r"poll=Poll\(id=(\d+)"

    ques_match = re.search(ques_pattern, poll_text)
    ans_match = re.search(answer_pattern, poll_text)
    options = re.findall(option_pattern, poll_text)
    poll_id_match = re.search(id_pattern, poll_text)

    poll_id = poll_id_match.group(1) if poll_id_match else None
    question = clean_question(ques_match.group(1)) if ques_match else None
    correct_ans_index = int(ans_match.group(1)) if ans_match else None

    options_dict = {f"option{opt}": text for text, opt in options}
    option0 = options_dict.get("option0", "")
    option1 = options_dict.get("option1", "")
    option2 = options_dict.get("option2", "Both a & b")
    option3 = options_dict.get("option3", "None of the above")

    correct_answer = [option0, option1, option2, option3][correct_ans_index] if correct_ans_index in [0,1,2,3] else None

    if all([poll_id, question, option0, option1, option2, option3, correct_answer]):
        data = {
            "pollid": [poll_id],
            "question": [question],
            "option1": [option0],
            "option2": [option1],
            "option3": [option2],
            "option4": [option3],
            "answer": [correct_answer]
        }
        return pd.DataFrame(data)
    return None

async def send_file_to_group(bot, filename):
    """
    Send a file to the group given by username or invite URL handle.

    Parameters:
    - bot: telegram bot instance
    - group_url: string, e.g. 'https://t.me/studystuff' or just 'studystuff'
    - filename: path to the file to send
    """
    # Extract the username part from URL if full URL is given
    group_url = 'https://t.me/hdjdbbdidbidbhdjdjhsjsjhdhsibddh'

    if group_url.startswith("https://t.me/"):
        username = "@" + group_url.split("https://t.me/")[1].strip("/")
    elif not group_url.startswith("@"):
        username = "@" + group_url.strip("/")
    else:
        username = group_url

    try:
        with open(filename, 'rb') as f:
            await bot.send_document(chat_id=username, document=InputFile(f, filename))
        return f"File {filename} sent successfully to {username}"
    except Exception as e:
        return f"Failed to send file to {username}: {e}"

async def fetch_polls(filename,bot):
    """Fetch polls from the chat and save to the Excel file."""
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        chat = await client.get_entity(INVITE_LINK)
        chat_id = chat.id

        # Load existing data if file exists
        if os.path.exists(filename):
            existing_df = pd.read_excel(filename, dtype={'pollid': str})
        else:
            existing_df = pd.DataFrame()

        # We'll collect new polls here
        new_polls = []

        async for message in client.iter_messages(chat_id):
            if message.poll:
                df_poll = parse_poll(message)
                if df_poll is not None:
                    # Check if pollid already exists
                    poll_id = df_poll['pollid'].iloc[0]
                    if existing_df.empty or poll_id not in existing_df['pollid'].values:
                        new_polls.append(df_poll)

        if new_polls:
            combined = pd.concat(new_polls, ignore_index=True)
            if not existing_df.empty:
                combined = pd.concat([existing_df, combined], ignore_index=True)

            combined.to_excel(filename, index=False)
            send_result = await send_file_to_group(bot, filename)
            return f"Added {len(new_polls)} new polls to {filename}.\n{send_result}"
        else:
            return "No new polls found to add."

# Telegram Bot command handler
async def addpoll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /addpoll command to fetch and save polls."""
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /addpoll filename.xlsx")
        return

    filename = context.args[0]
    if not filename.endswith(".xlsx"):
        await update.message.reply_text("Please provide a valid Excel filename ending with .xlsx")
        return

    await update.message.reply_text(f"Fetching polls and saving to {filename}...\nPlease wait...")

    # Run the async fetch_polls function
    result = await fetch_polls(filename,context.bot)

    await update.message.reply_text(result)

async def main():
    # Create your Telegram Bot with your Bot Token
    # Replace 'YOUR_TELEGRAM_BOT_TOKEN' with your actual bot token from BotFather
    application = ApplicationBuilder().token('7544102526:AAH61kptKH3-2RyXuNpDyX2ohvE1dN3CC4s').build()

    application.add_handler(CommandHandler("addpoll", addpoll_command))

    print("Bot is polling...")
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
