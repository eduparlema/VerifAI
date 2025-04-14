import requests
from flask import Flask, request, jsonify
from llmproxy import generate
import os
from mainAgent import main_agent
from modules import *
from utils import *

app = Flask(__name__)

RC_token = os.environ.get("RC_token")
RC_userId = os.environ.get("RC_userId")

special_responses = ["__FACT_CHECKABLE__", "__NO_FACT_CHECK_API__"]

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
    response = message

    while response in special_responses or response == message:
        print(f"Reponse from agent: {response}")
        module = main_agent(response)
        print(f"[INFO] Agent calling: {module}")
        module = add_params_to_module(module, room_id, user)
        print(f"[INFO] Edited module: {module}")
        response = eval(module)
        print(f"\n\nresponse from module {module}: \n\n{response}")
        if response == "__FACT_CHECKABLE__":
            send_direct_message("🔎 Searching if your claim has been fact-checked... please wait", room_id)
        elif response == "__NO_FACT_CHECK_API__":
            send_direct_message("😕 Your claim hasn't been fact-checked yet... 🔎 Performing a general search to find relevant information — please hang tight! ⏳", room_id)
    
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    app.run()