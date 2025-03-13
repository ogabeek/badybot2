# BadyBot2 - Telegram Bot

You can find the bot [on this link.](https://bady00bot.t.me)

**BadyBot2** is a feature-rich Telegram bot built using Python and the `python-telegram-bot` library. It tracks user activity, sends random responses (jokes and GIFs), generates activity reports in the form of pie charts, and interacts with users in various fun and useful ways.



## Features

- **Track User Activity**: The bot stores messages sent by users and tracks the activity in a MongoDB database.
- **Random Joke Responses**: The bot sends a random AI-generated joke or humorous comment about a user's message (with a 10% chance).
- **Random GIFs/Stickers**: The bot sends a random funny GIF or sticker (with a 50% chance) every N messages.
- **Activity Pie Chart**: The bot generates and sends a pie chart showing the percentage of messages sent by each user in the chat.

## Bot Commands

- `/help` - Show this help message.
- `/stats` - Check out chat activity statistics.
- `/ask <question>` - Ask anything to AI.
- `/summary` - Get today's bullet-point summary.
- `/topic` - Get the main topics from recent discussions.
- `/profile @username or Name` - Get what the group knows about the user.
- `/remember <text>` - Add a short memory to further AI prompts (limited).
- `/activity` or `/show_activity` - Shows the percentage of messages sent by each person in the chat.

## Installation

### Prerequisites

- Python 3.7+
- MongoDB (either locally or use MongoDB Atlas)
- Telegram Bot Token
- OpenAI API Key (for random joke generation)

### Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/badybot2.git
   cd badybot2
   ```
2. **Install dependencies from requirements.txt:**
    ```bash
    pip install -r requirements.txt
    ```
3. **Set environment variables for sensitive credentials (e.g., OpenAI API key, Telegram Bot token, etc.):**

    ```bash
    export TELEGRAM_TOKEN="your-telegram-bot-token"
    export OPENAI_API_KEY="your-openai-api-key"
    ```

4. **Start MongoDB (locally or via MongoDB Atlas).**

### Configuration

- The bot stores messages and activity data in MongoDB. You can configure MongoDB connection settings in src/db_functions.py.
- Sticker and GIF Handling: The bot can send random stickers and GIFs via Telegram's inline search (@gif funny, @sticker).

### File structure
```
badybot2/
├── src/
│   ├── __pycache__/          # Compiled Python files
│   ├── ai_functions_lib.py   # AI-related functions for generating jokes and responses
│   ├── command_handler.py    # Command handling functions for bot commands
│   ├── db_functions.py       # MongoDB interaction functions
│   └── main.py               # Main entry point for starting the bot
├── .env                      # Environment variables for sensitive information
├── .gitignore                # Git ignore file (e.g., for virtual environments and temp files)
├── README.md                 # This file
└── requirements.txt          # Python dependencies
```
## Running the bot 

1. Make sure all the environment variables are set (either in .env or via your terminal).
2. Run the bot using the following command: python src/main.py
3. Your bot will start running and will respond to commands in the Telegram chat.



## Project Agenda

- ✅ 🙋‍♀️ **Add full project description in README.**
- [ ] 🙋 **In a week and then in a month:**  
  The bot should trigger a message:  
  "Thank you for using this bot, it's totally free for you, but it consumes resources. If you'd like to support it, visit [this link](https://ogabeeek.notion.site/Thk-u-135bc0d823c3805381f2f38ac074a2c8?pvs=4)."
- [ ] 🙋 **Statistics Enhancement:**  
  Stats should be available not only by @user_name but also with the chat name.
- ✅ 🙋‍♀️ **For a statistics function add feature of showing it in a pichart.**
- [ ] 🙋 **Fix the part of message_handler function that has a random chance of sending a reaction to the previous message**
- [ ] 🙋 **Message Separation Issue:**  
  The bot currently remembers messages from other chats. Each group should be independent.  
  *Suggestion:* All functions should collect and respond according to each group's unique ID.
- [ ] 🙋 **DataBase:**  
    Integrade database to mongoDB online
- ✅ 🙋‍♀️ **Function Separation:**  
  "Remember," stats, summary, and topic statements should be separated.
- ✅ 🙋‍♀️ **Engagement Function:**  
  Create a function that occasionally engages the chat by adding comments, gifts, or other media.
- ✅ 🙋‍♀️ **Documentation:**   

  Add documentation to the functions.
- [ ] **Additional Custom Functions:**  
  Implement your own additional functions as needed.


<b> Team: </b> 

🙋‍♀️ - this is Nina (Lead)

🙋 - this is Ogabek 

[ ] - not assigned yet

<a href="https://ogabeeek.notion.site/Thk-u-135bc0d823c3805381f2f38ac074a2c8?pvs=4" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;"></a>
