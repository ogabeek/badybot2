from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackQueryHandler,
    ChatMemberHandler
)
from ai_functions_lib import (
    start_command,
    button_callback,
    chat_member_update,
    unknown_command   
)
from command_handlers import (
    profile_command,
    statistics_command,
    daily_summary_command,
    ask_command,
    remember_command,
    help_command,
    topic_command,
    message_handler
)
from db_functions import BOT_TOKEN, send_activity_chart



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
    application.add_handler(CommandHandler("activity", send_activity_chart))  # sends pie chart

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
    
    


    
