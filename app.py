import requests
from flask import Flask, request, jsonify
from llmproxy import generate
import os

app = Flask(__name__)

RC_token = os.environ.get("RC_token")
RC_userId = os.environ.get("RC_userId")
RC_API = os.environ.get("RC_API")

ROCKETCHAT_AUTH = {
    "X-Auth-Token": RC_token,
    "X-User-Id": RC_userId,
}

ROCKETCHAT_API = RC_API

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

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})

    print(f"Message from {user} : {message}")

    # Generate a response using LLMProxy
    response = generate(
        model='4o-mini',
        system='answer my question and add keywords',
        query= message,
        temperature=0.0,
        lastk=0,
        session_id='GenericSession'
    )

    response_text = response['response']
    # Send verdict + buttons
    requests.post(ROCKETCHAT_API, headers=ROCKETCHAT_AUTH, json={
        "roomId": room_id,
        "text": response_text,
        "attachments": [
            {
                "text": "What would you like to do next?",
                "actions": [
                    {
                        "type": "button",
                        "text": "🔍 Verify Again",
                        "msg": "verify_again",
                        "msg_in_chat_window": True
                    },
                    {
                        "type": "button",
                        "text": "🧠 Crowdsource",
                        "msg": "crowdsource",
                        "msg_in_chat_window": True
                    }
                ]
            }
        ]
    })
    
    # Send response back
    print(response_text)

    return jsonify({"text": response_text})
    
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    app.run()