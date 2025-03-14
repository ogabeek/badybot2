import os
import certifi
import logging
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from typing import Dict, Any, List

# Set up and export the logger.
logger = logging.getLogger(__name__)

# Load the MongoDB connection URI from environment variables.
URI = os.getenv("URI")
if not URI:
    raise ValueError("The Database token is not set. Please set the URI environment variable.")

# Initialize the MongoDB client with TLS (using certifi) and select the database.
client = MongoClient(
    URI,
    tlsCAFile=certifi.where(),
    server_api=ServerApi("1")
)
db = client["telegram_bot_db"]

# Define collections.
messages_collection = db["messages"]           # Stores all raw messages.
memory_collection = db["memory"]               # For any short-term memory data.
chat_info_collection = db["chat_info"]         # Additional info about chats.
user_profiles_collection = db["user_profiles"] # Aggregated user profiles per chat.

def insert_message(message_data: Dict[str, Any]) -> None:
    """
    Insert a new message document into the messages collection.
    
    Args:
        message_data (Dict[str, Any]): A dictionary containing message details.
                                      Expected keys: message_id, chat_id, user_id,
                                      username, full_name, text, timestamp, etc.
    """
    messages_collection.insert_one(message_data)

def get_memory(chat_id: int) -> str:
    """
    Retrieve the stored memory text for a specific chat.
    
    Args:
        chat_id (int): The chat identifier.
        
    Returns:
        str: The stored memory text, or an empty string if not found.
    """
    memory_doc = memory_collection.find_one({"chat_id": chat_id})
    return memory_doc.get("memory", "") if memory_doc else ""

def update_memory(chat_id: int, new_text: str, max_words: int = 50) -> None:
    """
    Update the chat's memory by appending new text and keeping only the last `max_words` words.
    
    Args:
        chat_id (int): The chat identifier.
        new_text (str): The new text to add.
        max_words (int): Maximum number of words to store. Defaults to 50.
    """
    current_memory = get_memory(chat_id)
    combined_text = f"{current_memory} {new_text}"
    words = combined_text.split()
    limited_memory = " ".join(words[-max_words:])
    
    memory_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"memory": limited_memory}},
        upsert=True
    )

def get_chat_info(chat_id: int) -> Dict[str, Any]:
    """
    Retrieve chat information from the chat_info collection.
    
    Args:
        chat_id (int): The chat identifier.
        
    Returns:
        Dict[str, Any]: A dictionary with chat info or an empty dict if not found.
    """
    return chat_info_collection.find_one({"chat_id": chat_id}) or {}

def update_chat_info(chat_id: int, data: Dict[str, Any]) -> None:
    """
    Update or insert chat information in the chat_info collection.
    
    Args:
        chat_id (int): The chat identifier.
        data (Dict[str, Any]): A dictionary of key-value pairs to update.
    """
    chat_info_collection.update_one(
        {"chat_id": chat_id},
        {"$set": data},
        upsert=True
    )

def get_statistics_text(chat_id: int) -> str:
    """
    Build and return a statistics summary for a given chat using the messages collection.
    
    Args:
        chat_id (int): The chat identifier.
        
    Returns:
        str: A formatted text summary of the chat's statistics, including total messages
             and per-user message counts.
    """
    total_messages = messages_collection.count_documents({"chat_id": chat_id})
    user_messages = messages_collection.aggregate([
        {"$match": {"chat_id": chat_id}},
        {"$group": {
            "_id": "$user_id",
            "count": {"$sum": 1},
            "username": {"$first": "$username"},
            "full_name": {"$first": "$full_name"}
        }},
        {"$sort": {"count": -1}}
    ])
    
    stats_text = f"📊 *Chat Statistics:*\n\nTotal messages: {total_messages}\n\n*User Activity:*\n"
    for user in user_messages:
        username = user.get("username")
        full_name = user.get("full_name", "Unknown")
        count = user["count"]
        user_display = f"@{username}" if username else full_name
        stats_text += f"{user_display}: {count} messages\n"
    
    return stats_text

# --- User Profile Functions ---
# These functions maintain per-chat user profiles, ensuring that the same user
# in different chats have distinct profile documents.

def get_user_profile(chat_id: int, user_id: int) -> Dict[str, Any]:
    """
    Retrieve the user profile for a given user in a specific chat.
    
    Args:
        chat_id (int): The chat identifier.
        user_id (int): The user identifier.
        
    Returns:
        Dict[str, Any]: The user profile document, or an empty dict if not found.
    """
    return user_profiles_collection.find_one({"chat_id": chat_id, "user_id": user_id}) or {}

def update_user_profile(chat_id: int, user_id: int, data: Dict[str, Any]) -> None:
    """
    Update or insert the user profile for a given user in a specific chat.
    
    Args:
        chat_id (int): The chat identifier.
        user_id (int): The user identifier.
        data (Dict[str, Any]): A dictionary of fields to update (e.g., username, full_name,
                               profile_summary, etc.).
    """
    user_profiles_collection.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": data},
        upsert=True
    )

def add_mention_to_user_profile(chat_id: int, user_id: int, mention_text: str) -> None:
    """
    Append a mention text to the user's profile in the user_profiles collection.
    
    Args:
        chat_id (int): The chat identifier.
        user_id (int): The user identifier.
        mention_text (str): The text of the mention (e.g., message snippet where their name is mentioned).
    """
    user_profiles_collection.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$push": {"mentions": mention_text}},
        upsert=True
    )

def get_all_user_messages(chat_id: int, user_id: int) -> List[Dict[str, Any]]:
    """
    Retrieve all messages from a specific user in a specific chat.
    
    Args:
        chat_id (int): The chat identifier.
        user_id (int): The user identifier.
        
    Returns:
        List[Dict[str, Any]]: A list of message documents sorted by timestamp.
    """
    return list(messages_collection.find({"chat_id": chat_id, "user_id": user_id}).sort("timestamp", 1))
