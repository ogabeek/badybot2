import os
import certifi
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()

uri = os.getenv("URI")
client = MongoClient(URI, tlsCAFile=certifi.where())
db = client['telegram_bot_db']

client = MongoClient(
    uri,
    server_api=ServerApi("1"),
    tlsCAFile=certifi.where()
)

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)