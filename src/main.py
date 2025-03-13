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
    
    


    
