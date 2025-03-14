import os
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import openai

from telegram import Update
from telegram.ext import ContextTypes

# Load environment variables and configure logger.
load_dotenv()
logger = logging.getLogger(__name__)

# Set up OpenAI API key.
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("The OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable.")

# ---------------------------------------------------------------------
# Helper Functions for OpenAI API Calls
# ---------------------------------------------------------------------
def _generate_completion(messages: list, max_tokens: int = 150, temperature: float = 0.7) -> str:
    """
    Helper function to call OpenAI's ChatCompletion API.
    
    Args:
        messages (list): List of message dictionaries.
        max_tokens (int): Maximum tokens to generate.
        temperature (float): Sampling temperature.
    
    Returns:
        str: The generated text or an error message.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except openai.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return "I'm sorry, but I'm currently unable to process that request."

def generate_response(prompt: str, context_text: str, max_tokens: int = 150, temperature: float = 0.7) -> str:
    """
    Generate an AI response using a prompt and additional context.
    
    Args:
        prompt (str): The user's question or instruction.
        context_text (str): Supplementary context to include.
        max_tokens (int): Maximum tokens in the response.
        temperature (float): Sampling temperature.
    
    Returns:
        str: The AI-generated response.
    """
    system_message = "You are a helpful assistant."
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion:\n{prompt}"}
    ]
    return _generate_completion(messages, max_tokens, temperature)

# ---------------------------------------------------------------------
# AI Command Handlers
# ---------------------------------------------------------------------
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /ask command: Responds to a user's question by incorporating chat memory.
    """
    user_prompt = ' '.join(context.args)
    if not user_prompt:
        await update.message.reply_text("Please provide a prompt after the command.")
        return

    from db_functions import get_memory
    chat_id = update.effective_chat.id
    memory = get_memory(chat_id)
    full_prompt = f"Memory: {memory}\n\nQuestion: {user_prompt}"
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": full_prompt}
    ]
    
    answer = _generate_completion(messages, max_tokens=150, temperature=0.7)
    await update.message.reply_text(answer)

async def remember_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /remember command: Stores provided text into the chat's memory.
    """
    memory_text = ' '.join(context.args)
    if not memory_text:
        await update.message.reply_text("Please provide text to remember. Usage: /remember Your text here.")
        return

    from db_functions import update_memory
    chat_id = update.effective_chat.id
    update_memory(chat_id, memory_text)
    await update.message.reply_text("📝 Noted. I've added that to my memory.")

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /profile command: Summarizes a user's profile based on recent chat messages.
    """
    if len(context.args) != 1:
        await update.message.reply_text("Please provide a username. Usage: /profile @username")
        return

    name = context.args[0]
    chat_id = update.effective_chat.id
    from db_functions import messages_collection

    if name.startswith('@'):
        username = name[1:]
        display_name = f"@{username}"
        query = {
            '$or': [
                {'username': username},
                {'text': {'$regex': f'@{username}'}}
            ],
            'chat_id': chat_id
        }
    else:
        display_name = name
        query = {
            '$or': [
                {'full_name': {'$regex': name, '$options': 'i'}},
                {'text': {'$regex': name, '$options': 'i'}}
            ],
            'chat_id': chat_id
        }

    messages_cursor = messages_collection.find(query).sort('timestamp', -1).limit(100)
    messages_text = '\n'.join([msg.get('text', '') for msg in messages_cursor])
    if not messages_text.strip():
        await update.message.reply_text("User not found.")
        return

    prompt = f"Based on the following messages, summarize who {display_name} is and what is known about them:\n\n{messages_text}"
    messages_list = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
    summary = _generate_completion(messages_list, max_tokens=150, temperature=0.7)
    await update.message.reply_text(summary)

async def topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /topic command: Identifies the main topics discussed in recent chat messages.
    """
    chat_id = update.effective_chat.id
    from db_functions import messages_collection
    recent_msgs_cursor = messages_collection.find({'chat_id': chat_id}).sort('timestamp', -1).limit(100)
    messages_text = '\n'.join([msg.get('text', '') for msg in reversed(list(recent_msgs_cursor)) if msg.get('text')])
    
    if not messages_text:
        await update.message.reply_text("I don't have enough info yet.")
        return

    prompt = "Identify the main topics discussed in the following conversation."
    messages_list = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Context:\n{messages_text}\n\nQuestion:\n{prompt}"}
    ]
    topics = _generate_completion(messages_list, max_tokens=150, temperature=0.7)
    await update.message.reply_text(f"Main topics:\n{topics}")

async def daily_summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /daily_summary command: Provides a bullet-point summary of today's messages.
    """
    chat_id = update.effective_chat.id
    from db_functions import messages_collection
    now = datetime.now(timezone.utc) + timedelta(hours=1)  # Adjust for desired timezone (e.g., Europe UTC+1)
    today_start = datetime(now.year, now.month, now.day)
    today_end = today_start + timedelta(days=1)
    
    messages_cursor = messages_collection.find({
        'chat_id': chat_id,
        'timestamp': {'$gte': today_start, '$lt': today_end}
    }).sort('timestamp', -1).limit(100)
    
    messages_text = '\n'.join([msg.get('text', '') for msg in messages_cursor])
    if not messages_text.strip():
        await update.message.reply_text("I don't have enough info yet.")
        return

    prompt = f"Provide a bullet point summary of the following messages from today:\n\n{messages_text}"
    messages_list = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
    summary = _generate_completion(messages_list, max_tokens=200, temperature=0.7)
    await update.message.reply_text(summary)
