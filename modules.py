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
        attachements = [
                {
                    "text": "Would you like me to search the web for you?",
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
        # Send verdict + buttons
        send_direct_message(verdict, room_id, attachments=attachements)
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

def should_crowdsource(claim, fact_check_result, search_summary):
    system_prompt = f"""
        You are part of a fact-checking assistant pipeline. A user has submitted
        the following claim:

        Claim:
        \"\"\"{claim}\"\"\"

        We attempted to verify the claim using fact-checking tools and search:

        Fact Check Result:
        \"\"\"{fact_check_result}\"\"\"

        Search Summary:
        \"\"\"{search_summary}\"\"\"

        Your task is to decide whether this claim should be sent to human users
        (a crowdsourcing module) to gather public opinion.

        Only respond with one of the following options:
        - "YES" → if the claim is ambiguous, opinion-based, socially controversial,
        or lacks authoritative evidence.
        - "NO" → if the claim is clearly factual and has already been resolved
        with high confidence.

        Do NOT explain your answer — only respond with "YES" or "NO".
        """
    # TODO: Implement the rest and integrate with pipeline
    pass

def crowdsourcing(input: str, room_id: str, user_name: str):
    pass

def decide_search_sources(user_input: str) -> list:
    print("[INFO] Deciding search strategy via LLM...")

    response = generate(
        model="4o-mini",
        system=DECIDE_SEARCH_SOURCES_PROMPT,
        query= "Here is the user input: \n" + user_input,
        temperature=0,
        lastk=3,
        session_id="search_planner_v1",
        rag_usage=False
    )
    
    try:
        sources = eval(response["response"].strip())  # Safe only if you trust the output
        assert isinstance(sources, list) and all(s in {"general", "local", "social"} for s in sources)
        print(f"[INFO] Strategy selected: {sources}")
        return sources
    except Exception as e:
        print(f"[WARN] Failed to parse LLM response: {e}")
        return ["general", "local"]  # Fallback


def all_search(user_input: str, room_id: str, user_name: str):
    print("[INFO] all_search module activated!")
    
    strategy = decide_search_sources(user_input)
    results = {}

    if "general" in strategy:
        results["General"] = general_search(user_input, room_id, user_name)
    if "local" in strategy:
        results["Local"] = local_search(user_input, room_id, user_name)
    if "social" in strategy:
        results["Social"] = social_search(user_input, room_id, user_name)

    # Filter empty responses
    non_empty = {k: v for k, v in results.items() if v and len(v.strip()) > 0}

    if not non_empty:
        fallback = "❌ Sorry, I couldn't find relevant information to verify this claim."
        # send_direct_message(fallback, room_id)
        return fallback

    combined = "\n\n".join([f"🔹 {k}:\n{v}" for k, v in non_empty.items()])
    final_response = f"✅ Here's a summary combining results from {', '.join(non_empty.keys())} sources:\n\n{combined}"
    
    response = generate(
        model="4o-mini",
        system=ALL_SEARCH_PROMPT,
        query=final_response,
        temperature=0.4,
        lastk=3,
        session_id="final_summary_synthesis",
        rag_usage=False
    )
 
    # send_direct_message(final_response, room_id)
    return response["response"]

def handle_followup(user_input: str, room_id: str, username: str):
    print("[INFO] handle_followup module activated (via last_k)!")

    FOLLOWUP_FROM_CONTEXT_PROMPT = """
    You are a fact-checking assistant. A user has asked a follow-up question. 
    You must answer **only** using the information in the prior conversation.

    📦 Input:
    - The previous assistant responses may contain summaries from general, local, or social sources.
    - You will also see the user's new question at the end.

    🎯 Goal:
    - Answer the follow-up using only facts mentioned earlier.
    - Be concise and cite the original sources when possible.
    - Do not go back to the web or assume new facts.
    - Use inline citations like *(Source: [Article Title](URL))*

    If the answer is not available in the previous conversation, respond ONLY with:
    `__NEED_WEB_SEARCH__`
    """

    response = generate(
        model="4o-mini",
        system=FOLLOWUP_FROM_CONTEXT_PROMPT,
        query=user_input,
        temperature=0.3,
        lastk=3,
        session_id="followup_from_context",
        rag_usage=False
    )

    reply = response["response"].strip()

    return reply



if __name__ == "__main__":
    # Example usage
    # user_input = "Trump replaced Pride Month with Veterans Month"
    # print("[INFO] User input:", user_input)
    # response = general_search(user_input)
    # print(response)
    # Example usage
    # user_input = "Turkey's earthquake response"
    # print("[INFO] User input:", user_input)
    # response = local_search(user_input, "sss", "sasa")
    # response = social_search(user_input, "sss", "aaa")
    # print(response)
    # print(all_search("Turkey's earthquake response", "room_id", "user_name"))
    print(handle_followup("how many people died in the earthquakle", "room_id", "user_name"))




