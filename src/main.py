import os
import logging
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackQueryHandler,
    ChatMemberHandler
)

## Import AI-specific handlers.
from ai_functions_lib import (
    ask_command,
    remember_command,
    profile_command,
    topic_command,
    daily_summary_command,
)

# Import non-AI command handlers.
from command_handlers import (
    start_command,
    button_callback,
    chat_member_update,
    unknown_command,
    statistics_command,
    help_command,
    message_handler
    #send in a month message
    #send in a week message
)

from stats_handlers import send_activity_chart
from utils import extract_status_change  # if needed elsewhere


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("The Telegram bot token is not set. Please set the BOT_TOKEN environment variable.")





def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler('profile', profile_command))  
    application.add_handler(CommandHandler('stats', statistics_command))
    application.add_handler(CommandHandler('summary', daily_summary_command)) 
    application.add_handler(CommandHandler('ask', ask_command))
    application.add_handler(CommandHandler('remember', remember_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('topic', topic_command))
    application.add_handler(CommandHandler('start', start_command))  
    application.add_handler(CommandHandler("activity", send_activity_chart))  # sends pie chart

    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    application.run_polling(timeout=10)


if __name__ == '__main__':
    main()
    
    


    
