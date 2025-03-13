from datetime import datetime, timedelta, timezone
import random
from dotenv import load_dotenv
from telegram import Update,  InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated 
from telegram.ext import ContextTypes
import openai
from db_functions import (
    messages_collection,
    memory_collection,
    logger
)
import ai_functions_lib

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
                model='gpt-4o-mini',
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.9,
            )
            reply = response.choices[0].message.content.strip()
            await message.reply_text(reply)
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")


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
            model='gpt-4o-mini',
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
            model='gpt-4o-mini',
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
            model='gpt-4o-mini',
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
    topics = ai_functions_lib.generate_response(prompt, context_text)

    await update.message.reply_text(f"Main topics:\n{topics}")




