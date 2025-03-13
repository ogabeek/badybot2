from datetime import datetime, timedelta, timezone
from telegram import Update,  InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import openai
from db_functions import chat_info_collection, logger
from command_handlers import extract_status_change


# Generate a response using OpenAI API
def generate_responses(prompt, context):
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




































