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






# # Functions for memory management
# def get_memory():
#     memory_doc = memory_collection.find_one({'chat_id': 'global_memory'})
#     if memory_doc:
#         return memory_doc.get('memory', '')
#     else:
#         return ''

# def update_memory(new_text):
#     current_memory = get_memory()
#     combined_text = f"{current_memory} {new_text}"
#     words = combined_text.split()
#     limited_memory = ' '.join(words[-50:])
#     memory_collection.update_one(
#         {'chat_id': 'global_memory'},
#         {'$set': {'memory': limited_memory}},
#         upsert=True
#     )





# Generate a response using OpenAI API
def generate_response(prompt, context):
    # Configure the AI with a default prompt for informal English
    system_message = "You are an AI assistant that communicates in informal English language."
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{prompt}"}
    ]
    try:
        response = openai.chat.completions.create(
            model='gpt-4o-mini',
            messages=messages,
            max_tokens=150,
            temperature=0.7,
        )
        answer = response.choices[0].message.content.strip()
        return answer
    except openai.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return "I'm sorry, but I couldn't process your request."


# Function for unknown commands
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(r"Unknown command. ¯\_(ツ)_/¯")

# Command handler for /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📋 *Commands:*
/help - Show this help message
/stats - Check out chat activity statistics
/ask [question] - Ask anything to AI.
/summary - Today's bullet point summary
/topic - Get main topics from recent discussions
/profile [@username or Name] - Get what the group knows about the user 
/remember [[text]] - Add a short memory to further AI prompts(limited).
"""
    # Create a button with coffee emoji
    button = InlineKeyboardButton("☕ - on service", callback_data='coffee')
    keyboard = InlineKeyboardMarkup([[button]])

    await update.message.reply_text(help_text, reply_markup=keyboard, parse_mode='Markdown')


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Text to @ogabeeek to know how this bot works! ")

# Function to handle bot being added to a group
async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return

    was_member, is_member = result

    if not was_member and is_member:
        # Bot was added to the chat
        chat_id = update.effective_chat.id
        now = datetime.utcnow()
        # Store the time when the bot was added
        chat_info_collection.update_one(
            {'chat_id': chat_id},
            {'$set': {'added_on': now}},
            upsert=True
        )
        # Schedule messages
        job_queue = context.job_queue
        job_queue.run_once(send_week_message, when=timedelta(days=7), chat_id=chat_id)
        job_queue.run_once(send_month_message, when=timedelta(days=30), chat_id=chat_id)

# Function to send message after a week
async def send_week_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    text = "Thank you for using this bot, it's totally free for you, but it consumes resources. If you want to support it, please visit this link: [https://t.ly/m4-av]"
    await context.bot.send_message(chat_id=chat_id, text=text)

# Function to send message after a month
async def send_month_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    text = "It's been a month! Thank you for using this bot. If you'd like to support its development, please visit this link: [https://t.ly/m4-av]"
    await context.bot.send_message(chat_id=chat_id, text=text)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("this bot on service", callback_data='enjoy')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=reply_markup)


#  "Catch @ogabeeek for a chat on how this bot works over a cup of coffee! ")

# ============================
# 4. Main Function
# ============================



def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler('profile', profile_command))
    application.add_handler(CommandHandler('stats', statistics_command))
    application.add_handler(CommandHandler('summary', daily_summary_command))  # Alias for /daily_summary
    application.add_handler(CommandHandler('ask', ask_command))
    application.add_handler(CommandHandler('remember', remember_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('topic', topic_command))
    application.add_handler(CommandHandler('start', start_command))  # Add /start command

    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Chat member update handler
    application.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))

    # Unknown command handler
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
    
    


    
