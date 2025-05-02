import requests
from flask import Flask, request, jsonify, Response
from llmproxy import generate
import os
from modules import *
from main import generate_response
from pymongo import MongoClient

import os
from pymongo import MongoClient

app = Flask(__name__)

MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["chatbot_db"]
messages = db["messages"]  # Collection to store messages


RC_token = os.environ.get("RC_token")
RC_userId = os.environ.get("RC_userId")
RC_API = os.environ.get("RC_API")
ROCKETCHAT_AUTH = {
    "X-Auth-Token": RC_token,
    "X-User-Id": RC_userId,
}

# conversation_history = {}

@app.route('/', methods=['POST'])
def hello_world():
   return jsonify({"text":'Hello from Koyeb - you reached the main page!'})

@app.route('/query', methods=['POST'])
def main():

    data = request.get_json() 

    # Extract relevant information
    user = data.get("user_name", "Unknown")
    message = data.get("text", "")
    room_id = data.get("channel_id")
    print(data)

   # Add user message to DB
    messages.update_one(
        {"username": user},
        {"$push": {"messages": message}},
        upsert=True
    )

    # Retrieve full message history
    user_data = messages.find_one({"username": user}, {"_id": 0})
    user_messages = user_data.get("messages", [])  # ✅ different variable name
    print(f"✅ Messages for user '{user}':{user_messages}")

    # # Initialize conversation if needed
    # if conversation_history.get(user) is None:
    #     conversation_history[user] = []

    response, language_analysis = generate_response(user_messages, message, room_id, user)

    # conversation_history[user].append(message)


    # print(f"\n\n Response: {response}")

    if language_analysis:
        attachement = [
                {
                    "actions": [
                        {
                            "type": "button",
                            "text": "Press here to analyze the language",
                            "msg": "Analyzing the language...",
                            "msg_in_chat_window": True
                        },
                    ]
                }
            ]
        send_direct_message(response, room_id,  attachement)
    else: 
        send_direct_message(response, room_id)


    return jsonify({"text": response})
 
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    app.run()

def send_direct_message(message: str, room_id: str, attachments = None) -> None:
    payload = {
        "roomId": room_id,
        "text": message
    }
    if attachments:
        payload["attachments"] = attachments

    response = requests.post(RC_API, headers=ROCKETCHAT_AUTH, json=payload)

    # Optional: handle errors
    if response.status_code != 200:
        print(f"Failed to send message: {response.status_code} - {response.text}")

    return