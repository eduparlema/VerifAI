import requests
import os
from flask import Flask, request, jsonify
from llmproxy import generate
from main import generate_response, intent_detection

app = Flask(__name__)

# Read proxy config from environment
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
    room_id = data.get("channel_id")  # needed to send messages
    print(data)

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})
    
    intent = intent_detection(message)

    if intent == "__FACT_CHECKABLE__":
        # Post initial message to initiate a thread
        init_msg = requests.post(ROCKETCHAT_API, headers=ROCKETCHAT_AUTH, json={
            "roomId": room_id,
            "text": "🔎 Fact-checking your claim... please wait.",
        })

        init_msg_data = init_msg.json()
        print(init_msg_data)
        thread_id = init_msg_data.get("message", {}).get("_id")

        if not thread_id:
            return jsonify({"text": "Something went wrong."})
        #Get the fact-check response
        response_text = generate_response(message)


        # Send verdict + buttons
        requests.post(ROCKETCHAT_API, headers=ROCKETCHAT_AUTH, json={
            "roomId": room_id,
            "text": response_text,
            "tmid": thread_id,
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
        if message == "verify_again":
            send_threaded_message(room_id, thread_id, "We will verify again!")
            return '', 200

        if message == "crowdsource":
            send_threaded_message(room_id, thread_id, "Crowdsourcing!")
            return '', 200

        #Send actual response in the thread
        # requests.post(ROCKETCHAT_API, headers=ROCKETCHAT_AUTH, json={
        #     "roomId": room_id,
        #     "text": response_text,
        #     "tmid": thread_id
        # })
    else:
        return jsonify({"text": intent})

    # return jsonify({"text": response})
    

def send_threaded_message(room_id, tmid, text):
    requests.post(ROCKETCHAT_API, headers=ROCKETCHAT_AUTH, json={
        "roomId": room_id,
        "text": text,
        "tmid": tmid
    })

@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    app.run()