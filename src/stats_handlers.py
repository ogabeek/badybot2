import io
import pandas as pd
import matplotlib.pyplot as plt
from telegram import Update
from telegram.ext import ContextTypes
from db_functions import messages_collection

async def send_activity_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generate and send a pie chart showing the percentage of messages sent by each user.
    """
    chat_id = update.effective_chat.id

    # Aggregate message counts by username.
    pipeline = [
        {"$group": {"_id": "$username", "message_count": {"$sum": 1}}}
    ]
    message_counts = list(messages_collection.aggregate(pipeline))

    if not message_counts:
        await context.bot.send_message(chat_id, "No activity data available.")
        return

    # Convert the aggregated data into a DataFrame.
    df = pd.DataFrame(message_counts)
    df.rename(columns={"_id": "username", "message_count": "Total"}, inplace=True)

    # Plot a pie chart.
    plt.figure(figsize=(8, 6))
    plt.pie(
        df["Total"],
        labels=df["username"],
        autopct='%1.1f%%',
        startangle=90,
        colors=plt.cm.Paired.colors
    )
    plt.title("Percentage of Messages Sent by Each User")

    # Save the plot to an in-memory buffer.
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close()

    # Send the chart as a photo to the chat.
    await context.bot.send_photo(chat_id, photo=buffer)
    buffer.close()
