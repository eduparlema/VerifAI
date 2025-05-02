import requests
from flask import Flask, request, jsonify, Response
from llmproxy import generate
import os
from modules import *
from main import generate_response

app = Flask(__name__)

RC_token = os.environ.get("RC_token")
RC_userId = os.environ.get("RC_userId")
RC_API = os.environ.get("RC_API")
ROCKETCHAT_AUTH = {
    "X-Auth-Token": RC_token,
    "X-User-Id": RC_userId,
}

conversation_history = {}

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

    if conversation_history.get(user) is None:
        conversation_history[user] = [message]
    else:
        conversation_history[user].append(message)


    response, language_analysis = generate_response(conversation_history[user], message, room_id, user)

    print(f"\n\n Response: {response}")

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