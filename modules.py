from llmproxy import generate
from utils import *
from dotenv import load_dotenv
import praw
from prompt import *

load_dotenv()

RC_API = os.environ.get("RC_API")
CLIENT_ID = os.environ.get("praw_client_id")
CLIENT_SECRET = os.environ.get("praw_client_secret")
USER_AGENT = "script:misinfo-bot:v1.0"

reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT
)

def intent_detection(user_input: str, room_id: str, user_name: str):
    print("[INFO] intent_detection_activated module activated!")
    response = generate(
        model="4o-mini",
        system=INTENT_DETECTION_PROMPT,
        query=user_input,
        temperature=0.5,
        lastk=1,
        session_id=SESSION,
        rag_usage=False
    )
    send_direct_message(response["response"], room_id)
    return response["response"]

def fact_check_tools(user_input: str, room_id: str, user_name:str):
    print("[INFO] fact_check_tools module activated!")
    keywords = extract_keywords(user_input)
    fact_check_data = query_fact_check_api(keywords)

    # Check if we get something from Fact Checking API
    if fact_check_data and fact_check_data.get('claims'):
        context = prepare_fact_check_context(fact_check_data["claims"])
        verdict = generate_verdict(user_input, context)
        # Send verdict + buttons
        requests.post(RC_API, headers=ROCKETCHAT_AUTH, json={
            "roomId": room_id,
            "text": verdict,
            "attachments": [
                {
                    "text": "Would you like me to search to web for you?",
                    "actions": [
                        {
                            "type": "button",
                            "text": "Search the web",
                            "msg": "Search the web",
                            "msg_in_chat_window": True
                        },
                    ]
                }
            ]
        })
        return verdict
    else:
        return "__NO_FACT_CHECK_API__"

def all_search(user_input: str, room_id: str, user_name:str):
    print("[INFO] all_search module activated!")
    response_general = general_search(user_input, room_id, user_name)
    print(f"Response from general search: \n{response_general}")
    
    response_local = local_search(user_input, room_id, user_name)

    response = all_search_verdict(response_local, response_local, "")
    print(f"[INFO]\n\n all_search_veredict: \n\n{response}")
    # Respond to the user
    send_direct_message(response_local, room_id)
    return response

def local_search(input: str, room_id: str, user_name: str):
    print("[INFO] local_search module activated!")
    return unified_search_pipeline(
        input, room_id, user_name,
        search_fn=local_google_search,
        summarizer_fn=generate_fact_based_response_custom,
        message_prefix="✅ Got some results from Google — taking a closer look at your claim now! 🔍"

    )

def general_search(input: str, room_id: str, user_name: str):
    print("[INFO] general_search module activated!")
    return unified_search_pipeline(
        input, room_id, user_name,
        search_fn=google_search,
        summarizer_fn=generate_fact_based_response,
        message_prefix="✅ Got some results from Google — taking a closer look at your claim now! 🔍"
    )

def social_search(input: str, room_id: str, user_name:str, limit_posts: int=3, limit_comments: int=20):
    print("[INFO] social_search module activated!")
    summaries = []
    posts = reddit.subreddit("all").search(input, sort='relevance', limit=limit_posts)

    for post in posts:
        post.comments.replace_more(limit=0)
        comments = [comment.body for comment in post.comments[:limit_comments]]
        summaries.append({
            "title": post.title,
            "url": post.shortlink,
            "comments": comments
        })
        print([post.shortlink])

    system_prompt = SOCIAL_SEARCH_PROMPT
    
    response = generate(
        model="4o-mini",
        system=system_prompt,
        query=f"Here is the content \n {comments}",
        temperature=0.2,
        lastk=3,
        session_id=SESSION,
        rag_usage=False
    )
    # send_direct_message(response["response"], room_id)
    return response["response"]


if __name__ == "__main__":
    # Example usage
    # user_input = "Trump replaced Pride Month with Veterans Month"

    # print("[INFO] User input:", user_input)
    # response = general_search(user_input)
    # print(response)
    # Example usage
    user_input = "Turkey's earthquake response"
    print("[INFO] User input:", user_input)
    # response = local_search(user_input, "sss", "sasa")
    response = social_search(user_input, "sss", "aaa")
    print(response)
