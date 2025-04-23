import requests
from flask import Flask, request, jsonify, Response
from llmproxy import generate
import os
from mainAgent import main_agent
from modules import *
from utils import *

app = Flask(__name__)

RC_token = os.environ.get("RC_token")
RC_userId = os.environ.get("RC_userId")

special_responses = ["__FACT_CHECKABLE__", "__NO_FACT_CHECK_API__", "__NEED_WEB_SEARCH__", "__FOLLOW_UP__", "__SOCIAL_SEARCH__"]

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
    if message == "Search the web":
        message = "__NO_FACT_CHECK_API__"
    if message.startswith("Question"):
        message = "__FOLLOW_UP__"
    if message == "Ask Reddit":
        message = "__SOCIAL_SEARCH__"

    response = message

    while response in special_responses or response == message:
        print(f"Reponse from agent: {response}")
        module = main_agent(response, user)
        print(f"[INFO] Agent calling: {module}")
        module = add_params_to_module(module, room_id, user)
        print(f"[INFO] Edited module: {module}")
        response = eval(module)
        print(f"\n\nresponse from module {module}: \n\n{response}")
        if response == "__NEED_WEB_SEARCH__":
            send_direct_message("🌐 Gathering more info from the web... one moment please!", room_id)
        elif response == "__FACT_CHECKABLE__":
            send_direct_message("🔎 Looking up your query in Google’s Fact Check Tools... hang on a moment!", room_id)
        elif response == "__NO_FACT_CHECK_API__":
            send_direct_message("😕 Couldn't find a fact-check for this via Google... 🔍 Starting a broader search to gather relevant info — please hold on! ⏳", room_id)
        
    return jsonify({"success": True})
 
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    app.run()