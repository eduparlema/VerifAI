import os
from pymongo import MongoClient

# Set your test Mongo URI here or ensure it's in your environment
MONGO_URI = "mongodb+srv://erinsarlak:t27SZqwtIEuJMvrX@memoryaidchatbot.0fbry.mongodb.net/?retryWrites=true&w=majority&appName=MemoryAidChatbot"
# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client["chatbot_db"]
messages_collection = db["messages"]  # Collection

# Test input
user = "test_user"
message = "This is a test message."

# Upsert: Add message to user's list or create new document
messages_collection.update_one(
    {"username": user},
    {"$push": {"messages": message}},
    upsert=True
)

# Retrieve messages for the user
user_data = messages_collection.find_one({"username": user}, {"_id": 0})
user_messages = user_data.get("messages", [])

# Print results
print(f"✅ Messages for user '{user}':")
for i, msg in enumerate(user_messages, 1):
    print(f"{i}. {msg}")
