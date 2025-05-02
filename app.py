import requests
from flask import Flask, request, jsonify, Response
from llmproxy import generate
import os
from modules import *
from main import generate_response, send_direct_message
# from pymongo import MongoClient

import os
# from pymongo import MongoClient

app = Flask(__name__)

MONGO_URI = os.environ.get("MONGO_URI")
print(f"Mongo URI: {MONGO_URI}")
# client = MongoClient(MONGO_URI)
# db = client["chatbot_db"]
# messages = db["messages"]  # Collection to store messages
number_emojis = {
    1: "1️⃣ ",
    2: " 2️⃣ ",
    3: " 3️⃣ ",
    4: " 4️⃣ ",
    5: " 5️⃣ ",
    6: " 6️⃣ ",
    7: " 7️⃣ ",
    8: " 8️⃣ ",
    9: " 9️⃣ ",
    10:" 🔟 "
}


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
    # messages.update_one(
    #     {"username": user},
    #     {"$push": {"messages": message}},
    #     upsert=True
    # )

    # Retrieve full message history
    # user_data = messages.find_one({"username": user}, {"_id": 0})
    # user_messages = user_data.get("messages", [])  # ✅ different variable name
    # print(f"✅ Messages for user '{user}':{user_messages}")

    # # Initialize conversation if needed
    # if conversation_history.get(user) is None:
    #     conversation_history[user] = []

    response, language_analysis, intent = generate_response(message, room_id, user)

    # conversation_history[user].append(message)


    # print(f"\n\n Response: {response}")

    if language_analysis:
        langua_analysis_update = "\nIt looks like this message uses some emotionally charged language 😮💬. Would you like me to analyze it and explain how it's written? 🔍😊"
        attachement = [
                {   "actions": [
                        {
                            "type": "button",
                            "text": "Press here to analyze the language",
                            "msg": f"Analyze the language of {message}",
                            "msg_in_chat_window": True
                        },
                    ]
                }
            ]
        send_direct_message(response + language_analysis, room_id, attachement)
    else: 
        send_direct_message(response, room_id)

    followup_questions = get_relevant_questions(message, response, intent)
    if followup_questions:
        # Generate emoji-labeled questions
        question_blocks = []
        for i, question in enumerate(followup_questions, start=1):
            emoji = number_emojis.get(i, f"{i}.")  # fallback to regular numbers if > 10
            question_blocks.append(f"{emoji} *{question}*")

        # Build the message
        question_text = "\n" + "\n".join(question_blocks)

        # Buttons: you can still label them Q1, Q2, etc., or use same emoji
        buttons = [
            {
                "type": "button",
                "text": f"{number_emojis.get(i+1, str(i+1))}",
                "msg": question,
                "msg_in_chat_window": True
            }
            for i, question in enumerate(followup_questions)
        ]

        # Send as a single attachment
        attachment = {
            "actions": buttons
        }

        send_direct_message("Want to keep going? Here's more you can explore 👇\n" + question_text, room_id, attachments=[attachment])


    # followup_questions = get_relevant_questions(message, response, intent)
    # if followup_questions:

    #     attachments = [
    #         {
    #             "text": f"❓ *{question}*",
    #             "actions": [
    #                 {
    #                     "type": "button",
    #                     "text": "Answer this",
    #                     "msg": question,
    #                     "msg_in_chat_window": True
    #                 }
    #             ]
    #         }
    #         for i, question in enumerate(followup_questions)
    #     ]

    #     send_direct_message("Want to keep going? You might find these questions interesting! 👉", room_id, attachments=attachments)

    return jsonify({"success": True})
 
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

def get_relevant_questions(user_query: str, content: str, intent: str):
    GET_RELEVANT_QUESTIONS_PROMPT = """
    You are a helpful assistant for an AI Agent that helps user detect
    missinformation. You should generaterelevant follow-up questions based
    on some content. You will be given a summary combining results from a
    fact-checking search. Your goal is to anticipate what a curious user might want to know next.

    Generate 2 or 3 thoughtful follow-up questions that are directly related to
    the main topic.

    Strictly respond ONLY with a Python list of the questions you come up with,
    like ["question1", "questions2"].
    """
    if intent == "misinformation_analysis":
        response = generate(
            model="4o-mini",
            system=GET_RELEVANT_QUESTIONS_PROMPT,
            query=f"Here is the content {content}\nOriginal query: {user_query}",
            temperature=0.3,
            lastk=1,
            session_id="get_relevan_questions_2",
            rag_usage=False,
        )
        questions = eval(response["response"].strip())  # Safe only if you trust the output
        assert isinstance(questions, list)
        print(f"[INFO] Generated questions: {questions}")
        return questions
    return []

if __name__ == "__main__":
    app.run()
