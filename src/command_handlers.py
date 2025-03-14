import os
import random
import io
from datetime import datetime, timedelta, timezone
# from db_functions import logger
import logging
import pandas as pd
import matplotlib.pyplot as plt
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated
from telegram.ext import ContextTypes
from dotenv import load_dotenv

# Load environment variables (if not already loaded in main)
load_dotenv()

# Import database helpers and logger from db_functions.py
from db_functions import (
    messages_collection,
    memory_collection,
    chat_info_collection,
    get_statistics_text,
    insert_message,
)
# Set up and export the logger.
logger = logging.getLogger(__name__)


from ai_functions_lib import generate_response

# Number of messages before triggering a random GIF/sticker response.
N = 5

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /start command.
    """
    keyboard = [[InlineKeyboardButton("this bot on service", callback_data="enjoy")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=reply_markup)



async def send_activity_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generate and send a pie chart showing the percentage of messages sent by each user.
    """
    chat_id = update.effective_chat.id

    # Aggregate message counts by username.
    pipeline = [
        {"$group": {"_id": "$username", "message_count": {"$sum": 1}}}
    ]
    message_counts = list(messages_collection.aggregate(pipeline))

    if not message_counts:
        await context.bot.send_message(chat_id, "No activity data available.")
        return

    # Convert the aggregated data into a DataFrame.
    df = pd.DataFrame(message_counts)
    df.rename(columns={"_id": "username", "message_count": "Total"}, inplace=True)

    # Plot a pie chart.
    plt.figure(figsize=(8, 6))
    plt.pie(
        df["Total"],
        labels=df["username"],
        autopct='%1.1f%%',
        startangle=90,
        colors=plt.cm.Paired.colors
    )
    plt.title("Percentage of Messages Sent by Each User")

    # Save the plot to an in-memory buffer.
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close()

    # Send the chart as a photo to the chat.
    await context.bot.send_photo(chat_id, photo=buffer)
    buffer.close()

def get_memory(chat_id: int) -> str:
    """
    Retrieve stored memory text for a chat.
    """
    memory_doc = memory_collection.find_one({'chat_id': chat_id})
    return memory_doc.get('memory', '') if memory_doc else ''

def update_memory(chat_id: int, new_text: str) -> None:
    """
    Update the memory for a chat by appending new text, keeping only the last 50 words.
    """
    current_memory = get_memory(chat_id)
    combined_text = f"{current_memory} {new_text}"
    words = combined_text.split()
    limited_memory = ' '.join(words[-50:])
    memory_collection.update_one(
        {'chat_id': chat_id},
        {'$set': {'memory': limited_memory}},
        upsert=True
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    user = message.from_user
    chat = message.chat

    # Create a document with the message data.
    doc = {
        'message_id': message.message_id,
        'chat_id': chat.id,
        'user_id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'text': message.text,
        'timestamp': message.date
    }

    try:
        insert_message(doc)
    except Exception as e:
        # Log the error to help diagnose issues.
        import logging
        logging.getLogger(__name__).error(f"Error inserting message: {e}")
    
    # Occasionally send a random AI comment (1 in 8 chance).
    if random.randint(1, 8) == 1:
        try:
            prompt = f"Write a humorous short comment about the following message:\n\n{message.text}, feel free to add emojies or be informal and funny. Don't add additional confirmation and quotation marks on this message becouse you are telegram bot"
            ai_comment = generate_response(prompt, "")
            await message.reply_text(ai_comment)
        except Exception as e:
            logger.error(f"Error generating AI comment: {e}")

    # # Update a message counter stored in memory_collection.
    # counter_doc = memory_collection.find_one({"chat_id": chat.id})
    # if counter_doc and "count" in counter_doc:
    #     new_count = counter_doc["count"] + 1
    #     memory_collection.update_one({"chat_id": chat.id}, {"$set": {"count": new_count}})
    # else:
    #     new_count = 1
    #     memory_collection.insert_one({"chat_id": chat.id, "count": new_count})

    # Every N messages, send a random GIF or sticker.
    if random.randint(1, 2) == 1:
        # await send_random_gif_or_sticker(chat.id, context)
        await send_random_sticker(chat.id, context)
        
async def send_random_gif_or_sticker(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """
    Randomly choose to send either a GIF or a sticker.
    """
    if random.choice([True, False]):
        await send_random_gif(chat_id, context)
    else:
        await send_random_sticker(chat_id, context)

async def send_random_gif(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """
    Send a random GIF (placeholder implementation).
    """
    # This is a placeholder—ideally, use an API or inline query to fetch a GIF.
    await context.bot.send_message(chat_id, "@gif funny")

async def send_random_sticker(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """
    Send a random sticker from a predefined list of sticker pack names.
    If a pack cannot be retrieved, try the next one. If none are available,
    send a fallback text message.
    """
    logger = logging.getLogger(__name__)
    # List of candidate sticker pack names.
    # Replace these with actual public sticker pack names or IDs known to work.
    sticker_packs = [
        "Caturday",              # Typically contains cat stickers.
        "simpson",          # For fans of the group BTS.
        # "Doc",
        # "Funny Cats",
        # "Doggos United",
        # "Cartoon Heroes",
        # "Vintage Memes",
        # "Modern Emoticons",
        # "Abstract Stickers",
        # "Funny Faces",
    
    ]
    
    # Copy list so we can remove invalid packs without modifying the original.
    available_packs = sticker_packs.copy()
    
    while available_packs:
        sticker_pack_name = random.choice(available_packs)
        try:
            sticker_set = await context.bot.get_sticker_set(sticker_pack_name)
            if sticker_set and sticker_set.stickers:
                sticker_id = random.choice(sticker_set.stickers).file_id
                await context.bot.send_sticker(chat_id, sticker_id)
                return
            else:
                logger.warning(f"Sticker set {sticker_pack_name} is empty.")
        except Exception as e:
            logger.error(f"Error fetching sticker pack '{sticker_pack_name}': {e}")
        # Remove the problematic pack and try another.
        available_packs.remove(sticker_pack_name)
    
    # If no sticker pack worked, send a fallback message.
    await context.bot.send_message(chat_id, "Sorry, no stickers available right now.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display a help message listing available non-AI commands.
    """
    help_text = """
    📋 *Commands:*
    /help - Show this help message
    /stats - Check out chat activity statistics
    /ask [question] - Ask anything to AI.
    /summary - Today's bullet point summary
    /topic - Get main topics from recent discussions
    /profile [@username or Name] - Get what the group knows about the user 
    /remember [[text]] - Add a short memory to further AI prompts(limited).
    /activity - Shows the percentage of messages sent by each person
    """

    button = InlineKeyboardButton("☕ - on service", callback_data='coffee')
    keyboard = InlineKeyboardMarkup([[button]])
    await update.message.reply_text(help_text, reply_markup=keyboard, parse_mode='Markdown')

async def statistics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Retrieve and display chat statistics.
    """
    chat_id = update.effective_chat.id
    stats_text = get_statistics_text(chat_id)
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Respond to unknown commands.
    """
    await update.message.reply_text("Unknown command. ¯\\_(ツ)_/¯")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle inline button callbacks.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("You are beautidul ✨ !")

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle bot status updates (e.g., when the bot is added to a group).
    """
    from utils import extract_status_change  # Ensure extract_status_change is defined in utils.py

    result = extract_status_change(update.my_chat_member)
    if result is None:
        return

    was_member, is_member = result
    if not was_member and is_member:
        chat_id = update.effective_chat.id
        now = datetime.utcnow()
        chat_info_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"added_on": now}},
            upsert=True
        )
        job_queue = context.job_queue
        job_queue.run_once(send_week_message, when=timedelta(days=7), chat_id=chat_id)
        job_queue.run_once(send_month_message, when=timedelta(days=30), chat_id=chat_id)

async def send_week_message(context: ContextTypes.DEFAULT_TYPE):
    """
    Send a reminder message after one week.
    """
    chat_id = context.job.chat_id
    text = (
        "Thank you for using this bot, it's totally free for you, but it consumes resources. "
        "If you want to support it, please visit this link: [https://t.ly/m4-av]"
    )
    await context.bot.send_message(chat_id=chat_id, text=text)

async def send_month_message(context: ContextTypes.DEFAULT_TYPE):
    """
    Send a reminder message after one month.
    """
    chat_id = context.job.chat_id
    text = (
        "It's been a month! Thank you for using this bot. "
        "If you'd like to support its development, please visit this link: [https://t.ly/m4-av]"
    )
    await context.bot.send_message(chat_id=chat_id, text=text)

