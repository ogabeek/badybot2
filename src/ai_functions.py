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






































