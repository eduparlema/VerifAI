import requests
from flask import Flask, request, jsonify, Response
from llmproxy import generate
import os
from modules import *
from main import generate_response

app = Flask(__name__)

RC_token = os.environ.get("RC_token")
RC_userId = os.environ.get("RC_userId")

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

    response = generate_response(message, user)

    return jsonify({"text": response})
 
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    app.run()


"""Bot Topics:
 🗽 United States
Immigration Policies and Debates
(e.g., U.S.-Mexico border policies, DACA, asylum rules)

Election Integrity and Voting Laws
(e.g., mail-in voting security, voter ID laws, allegations of election fraud)

🌎 International
Climate Change Agreements and Policies
(e.g., Paris Agreement commitments, disputes over climate financing among countries)

International Conflicts and Humanitarian Crises
(e.g., Russia-Ukraine war facts vs. propaganda, Gaza conflict narratives)

🇧🇷 Country-Specific (Examples)
Political Corruption in Latin America
(e.g., Brazil’s "Operation Car Wash," recent election controversies in countries like Bolivia, Peru)

Authoritarianism and Democratic Backsliding
(e.g., election fairness debates in Hungary, Turkey, or Venezuela)

"""