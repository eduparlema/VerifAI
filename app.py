import requests
from flask import Flask, request, jsonify
from llmproxy import generate
import os
from mainAgent import main_agent

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

    response = main_agent(message)

    if response == "__FACT_CHECKABLE__":
        module = main_agent(response)
        print(f"[INFO] Agent calling: {module}")
        response = eval(module)
    return jsonify({"text": response})
    
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    app.run()