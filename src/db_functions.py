import os
import logging
from datetime import datetime, timedelta, timezone
import random
from dotenv import load_dotenv

from telegram import Update,  InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated 
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
    CallbackQueryHandler,
    ChatMemberHandler
)

import openai
from pymongo import MongoClient
from pymongo.server_api import ServerApi


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

