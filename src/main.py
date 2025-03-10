import os
import logging
from datetime import datetime, timedelta, timezone
import random
import json
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

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/telegram_bot_bd')
db = client['telegram_bot_db']
messages_collection = db['messages']
memory_collection = db['memory']
chat_info_collection = db['chat_info']

# ============================
# 2. Helper Functions
# ============================

# Function for memory management
def get_memory(chat_id):
    memory_doc = memory_collection.find_one({'chat_id': chat_id})
    if memory_doc:
        return memory_doc.get('memory', '')
    else:
        return ''

def update_memory(chat_id, new_text):
    current_memory = get_memory(chat_id)
    combined_text = f"{current_memory} {new_text}"
    words = combined_text.split()
    limited_memory = ' '.join(words[-50:])
    memory_collection.update_one(
        {'chat_id': chat_id},
        {'$set': {'memory': limited_memory}},
        upsert=True
    )

# Helper function to extract status change
def extract_status_change(chat_member_update: ChatMemberUpdated):
    old_status = chat_member_update.old_chat_member.status
    new_status = chat_member_update.new_chat_member.status
    if old_status == new_status:
        return None
    was_member = old_status in ['member', 'administrator', 'creator']
    is_member = new_status in ['member', 'administrator', 'creator']
    return was_member, is_member


# Function to store messages and handle random interactions
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return
    
    user = message.from_user
    chat = message.chat

    # Store the message in the database
    messages_collection.insert_one({
        'message_id': message.message_id,
        'chat_id': chat.id,
        'user_id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'text': message.text,
        'timestamp': message.date
    })

    # Random interaction
    if random.randint(1, 10) == 1:
        try:
            prompt = f"Write a humorous comment or joke about the following message:\n\n{message.text}"
            response = openai.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.9,
            )
            reply = response.choices[0].message.content.strip()
            await message.reply_text(reply)
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")

# Function for /profile command
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Please provide a username. Usage: /profile @username")
        return

    name = context.args[0]
    chat_id = update.effective_chat.id

    if name.startswith('@'):
        # Search by username
        username = name[1:]
        display_name = f"@{username}"
        messages = messages_collection.find({
            '$or': [
                {'username': username},
                {'text': {'$regex': f'@{username}'}}
            ],
            'chat_id': chat_id
        }).sort('timestamp', -1).limit(100)
    else:
        # Search by full_name
        username = name 
        display_name = name
        messages = messages_collection.find({
            '$or': [
                {'full_name': {'$regex': name, '$options': 'i'}},
                {'text': {'$regex': name, '$options': 'i'}}
            ],
            'chat_id': chat_id
        }).sort('timestamp', -1).limit(100)

    messages_text = '\n'.join([msg.get('text', '') for msg in messages])

    if not messages_text.strip():
        await update.message.reply_text("The user not found.")
        return

    try:
        prompt = f"Based on the following messages, summarize who {display_name} is and what is known about them:\n\n{messages_text}"
        response = openai.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7,
        )
        summary = response.choices[0].message.content.strip()
        await update.message.reply_text(summary)
    except openai.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text("I'm sorry, but I'm currently unable to process that request.")

# Function for /stats command
async def statistics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    total_messages = messages_collection.count_documents({'chat_id': chat_id})
    user_messages = messages_collection.aggregate([
        {'$match': {'chat_id': chat_id}},
        {'$group': {
            '_id': '$user_id',
            'count': {'$sum': 1},
            'username': {'$first': '$username'},
            'full_name': {'$first': '$full_name'}
        }},
        {'$sort': {'count': -1}}
    ])
    
    stats_text = f"📊 *Chat Statistics:*\n\nTotal messages: {total_messages}\n\n*User Activity:*\n"
    for user in user_messages:
        username = user.get('username')
        full_name = user.get('full_name', 'Unknown')
        count = user['count']
        if username:
            user_display = f"@{username}"
        else:
            user_display = full_name
        stats_text += f"{user_display}: {count} messages\n"

    await update.message.reply_text(stats_text, parse_mode='Markdown')

# Function for /daily_summary command
async def daily_summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Europe timezone (UTC+1)
    now = datetime.now(timezone.utc) + timedelta(hours=1)

    today_start = datetime(now.year, now.month, now.day)
    today_end = today_start + timedelta(days=1)

    messages = messages_collection.find({
        'chat_id': chat_id,
        'timestamp': {'$gte': today_start, '$lt': today_end}
    }).sort('timestamp', -1).limit(100)

    messages_text = '\n'.join([msg.get('text', '') for msg in messages])

    if not messages_text:
        await update.message.reply_text("I don't have enough info yet.")
        return

    try:
        prompt = f"Provide a bullet point summary of the following messages from today:\n\n{messages_text}"
        response = openai.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7,
        )
        summary = response.choices[0].message.content.strip()
        await update.message.reply_text(summary)
    except openai.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text("I'm sorry, but I'm currently unable to process that request.")

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

# Function for /remember command
async def remember_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory_text = ' '.join(context.args)
    if not memory_text:
        await update.message.reply_text("Please provide text to remember. Usage: /remember Your text here.")
        return
    chat_id = update.effective_chat.id
    update_memory(chat_id, memory_text)
    await update.message.reply_text("📝 Noted. I've added that to my memory.")

# Function for /ask command
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = ' '.join(context.args)
    if not user_prompt:
        await update.message.reply_text("Please provide a prompt after the command.")
        return

    chat_id = update.effective_chat.id
    memory = get_memory(chat_id)
    prompt = f"Memory: {memory}\n\nQuestion: {user_prompt}"

    try:
        response = openai.chat.completions.create(
            model='gpt-3.5-turbo',
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
            max_tokens=150,
            temperature=0.7,
        )
        answer = response.choices[0].message.content.strip()
        await update.message.reply_text(answer)
    except openai.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text("I'm sorry, but I'm currently unable to process that request.")

# Command handler for /topic
async def topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Fetch recent messages
    chat_id = update.effective_chat.id
    recent_msgs_cursor = messages_collection.find({'chat_id': chat_id}).sort('timestamp', -1).limit(100)
    messages = [msg.get('text', '') for msg in reversed(list(recent_msgs_cursor)) if msg.get('text')]
    context_text = '\n'.join(messages)

    if not context_text:
        await update.message.reply_text("I don't have enough info yet.")
        return
    
    # Generate topics using AI
    prompt = "Identify the main topics discussed in the following conversation."
    topics = generate_response(prompt, context_text)

    await update.message.reply_text(f"Main topics:\n{topics}")


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
            model='gpt-3.5-turbo',
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
    await query.edit_message_text("Enjoy!")

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
    text = "Thank you for using this bot, it's totally free for you, but it consumes resources. If you want to support it, please visit this link: [Support Link]"
    await context.bot.send_message(chat_id=chat_id, text=text)

# Function to send message after a month
async def send_month_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    text = "It's been a month! Thank you for using this bot. If you'd like to support its development, please visit this link: [Support Link]"
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
    
    
# in a week and then in a month since adding bot to the group, the bot has to trigger message "thank you for using this bot, it's totally free for you, but it concumes resourses. and if you want to support it for a while this link - > 
# stats should be awailable not only by @user_name but also with the name in chat. 
# there is a problem that it remembers messages from other chats. it shouldn't be that. For each group whether the bot connected it must be independed from others. I think the solution here is that all the functions must collect and respond regarding the groups id.
# "remember", stats, summary, topic statements are also must be separated by




# Import history from JSON file
# def import_history_from_json(json_file_path):
#     with open(json_file_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)

#     messages = data.get('messages', [])
#     for message in messages:
#         if 'text' not in message or message['type'] != 'message':
#             continue

#         text_content = message['text']
#         # Handle cases where 'text' can be a list
#         if isinstance(text_content, list):
#             text_content = ''.join(
#                 part['text'] if isinstance(part, dict) else part
#                 for part in text_content
#             )

#         # Parse timestamp
#         date_str = message['date']
#         timestamp = int(datetime.datetime.fromisoformat(date_str).timestamp())

#         # Create message document
#         msg_doc = {
#             'message_id': message['id'],
#             'chat_id': message.get('chat_id', None),
#             'user_id': message.get('from_id', None),
#             'username': message.get('from', None),
#             'text': text_content,
#             'timestamp': timestamp,
#         }

#         # Insert or update the message in the database
#         messages_collection.update_one(
#             {'message_id': msg_doc['message_id']},
#             {'$set': msg_doc},
#             upsert=True
#         )
    
