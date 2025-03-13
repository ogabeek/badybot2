import os
import logging
from dotenv import load_dotenv
import openai
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from telegram import ChatMemberUpdated, Update

import io
import matplotlib.pyplot as plt
import pandas as pd
from telegram.ext import CallbackContext




# ============================
# 1. Setup and Configuration
# ============================

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Set up OpenAI API key and Telegram bot token
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("The OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable.")

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("The Telegram bot token is not set. Please set the BOT_TOKEN environment variable.")


URI = os.getenv('URI')
if not URI:
    raise ValueError("The Database token is not set. Please set the URI environment variable.")


# Create a new client and connect to the server
client = MongoClient(URI, server_api=ServerApi('1'))


# Connect to MongoDB
# client = MongoClient('mongodb://localhost:27017/telegram_bot_bd')
db = client['telegram_bot_db']
messages_collection = db['messages']
memory_collection = db['memory']
chat_info_collection = db['chat_info']

# Helper function to extract status change
def extract_status_change(chat_member_update: ChatMemberUpdated):
    old_status = chat_member_update.old_chat_member.status
    new_status = chat_member_update.new_chat_member.status
    if old_status == new_status:
        return None
    was_member = old_status in ['member', 'administrator', 'creator']
    is_member = new_status in ['member', 'administrator', 'creator']
    return was_member, is_member


async def send_activity_chart(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Fetch message counts per user from MongoDB
    pipeline = [
        {"$group": {"_id": "$username", "message_count": {"$sum": 1}}}
    ]
    message_counts = list(messages_collection.aggregate(pipeline))

    if not message_counts:
        await context.bot.send_message(chat_id, "No activity data available.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(message_counts)
    df.rename(columns={"_id": "username", "message_count": "Total"}, inplace=True)

    # Plot pie chart
    plt.figure(figsize=(8, 6))
    plt.pie(df["Total"], labels=df["username"], autopct='%1.1f%%', startangle=90, colors=plt.cm.Paired.colors)
    plt.title("Percentage of Messages Sent by Each User")

    # Save image to an in-memory buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close()

    # Send the image directly to Telegram chat
    await context.bot.send_photo(chat_id, photo=buffer)
    buffer.close()
