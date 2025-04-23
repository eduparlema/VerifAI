from llmproxy import generate
from utils import *
from dotenv import load_dotenv
import praw
from prompt import *

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
    if response["response"] != "__FACT_CHECKABLE__":
        send_direct_message(response["response"], room_id)
    return response["response"]

def fact_check_tools(user_input: str, room_id: str, user_name:str):
    print("[INFO] fact_check_tools module activated!")
    url = extract_url(user_input)
    if url:
        print(f"[INFO] Detected URL: {url}")
        url_content = fetch_full_content(url)
        print(f"\n[INFO] URL data: \n{url_content}")
        user_input += f"\n Url Content: {url_content}"
    keywords = extract_keywords(user_input)
    print(f"[INFO] Keywords: {keywords}")
    fact_check_data = query_fact_check_api(keywords)

    # Check if we get something from Fact Checking API
    if fact_check_data and fact_check_data.get('claims'):
        context = prepare_fact_check_context(fact_check_data["claims"])
        verdict = generate_verdict(user_input, context)
        if verdict == "__NO_FACT_CHECK_API__":
            return "__NO_FACT_CHECK_API__"
        send_direct_message(verdict, room_id)
        attachements = [
                {
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
        send_direct_message("Want me to look this up online for you? 🌐🔍", room_id, attachments=attachements)
        return verdict
    else:
        return "__NO_FACT_CHECK_API__"

# def all_search(user_input: str, room_id: str, user_name:str):
#     print("[INFO] all_search module activated!")
#     response_general = general_search(user_input, room_id, user_name)
#     print(f"Response from general search: \n{response_general}")
    
#     response_local = local_search(user_input, room_id, user_name)

#     response = all_search_verdict(response_local, response_local, "")
#     print(f"[INFO]\n\n all_search_veredict: \n\n{response}")
#     # Respond to the user
#     send_direct_message(response_local, room_id)
#     return response

def local_search(input: str, room_id: str, user_name: str):
    print("[INFO] local_search module activated!")
    return unified_search_pipeline(
        input, room_id, user_name,
        search_fn=local_google_search,
        summarizer_fn=generate_summary,
        message_prefix="✅ Got some results from Google — taking a closer look at your claim now! 🔍"

    )

def general_search(input: str, room_id: str, user_name: str, all_search: bool=False):
    print("[INFO] general_search module activated!")
    response = unified_search_pipeline(
        input, room_id, user_name,
        search_fn=google_search,
        summarizer_fn=generate_summary,
        message_prefix="✅ Got some results from Google — taking a closer look at your claim now! 🔍"
    )
    if not all_search:
        send_direct_message(response["response"], room_id)
    return response

def social_search(user_input: str, room_id: str, user_name:str, limit_posts: int=3, limit_comments: int=20, all_search: bool=False):
    print("[INFO] social_search module activated!")
    reddit_ulrs = google_search_reddit(user_input)
    print(f"[INFO] These are the reddit urls: {reddit_ulrs}")
    summaries = get_reddit_comment_summaries_from_urls(reddit_ulrs[:limit_posts], limit_comments)
    print(f"[INFO] This are the summaries: {summaries}")

    response = generate(
        model="4o-mini",
        system=SOCIAL_SEARCH_PROMPT,
        query=f"Here is the content \n {summaries}",
        temperature=0.2,
        lastk=3,
        session_id=SESSION,
        rag_usage=False
    )
    if not all_search:
        send_direct_message(response["response"], room_id)
    print(f"[INFO] Social response: {response["response"]}")
    return response["response"]

def should_crowdsource(claim, search_summary):
    SHOULD_CROWDSOURCE_PROMPT = f"""
        You are part of a fact-checking assistant pipeline. You will be given a
        claim / statement / question submitted by a user. We attempted to verify
        the claim using fact-checking tools and google search. You will be provided
        with these results.

        Your task is to decide whether this claim should be sent to human users
        (a crowdsourcing module) to gather public opinion.

        Only respond with one of the following options:
        - "YES" → if the claim is ambiguous, opinion-based, socially controversial,
        or lacks authoritative evidence.
        - "NO" → if the claim is clearly factual and has already been resolved
        with high confidence.

        Do NOT explain your answer — STRICTLY only respond with "YES" or "NO".
        """
    response = generate(
        model="4o-mini",
        system=SHOULD_CROWDSOURCE_PROMPT,
        query=f"User input: {claim}, Fact-checkin results: {search_summary}",
        temperature=0.1,
        lastk=1,
        session_id="crowdsoursing_1",
        rag_usage=False
    )
    return True if response["response"] == "YES" else False

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
        session_id="search_planner_v2",
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
        results["General"] = general_search(user_input, room_id, user_name, all_search=True)
    if "local" in strategy:
        results["Local"] = local_search(user_input, room_id, user_name)
   
    # Filter empty responses
    non_empty = {k: v for k, v in results.items() if v and len(v.strip()) > 0}

    if not non_empty:
        fallback = "❌ Sorry, I couldn't find relevant information to verify this claim."
        # send_direct_message(fallback, room_id)
        return fallback

    combined = "\n\n".join([f"🔹 {k}:\n{v}" for k, v in non_empty.items()])
    final_response = f"✅ Here's a summary combining results from {', '.join(non_empty.keys())} sources:\n\n{combined}"

    print(f"[INFO] Final response in all_search: {final_response}")
    
    response = generate(
        model="4o-mini",
        system=ALL_SEARCH_PROMPT,
        query=final_response,
        temperature=0.4,
        lastk=3,
        session_id=SESSION,
        rag_usage=False
    )

    followup_questions = get_relevant_questions(response["response"])

    attachments = [
        {
            "text": f"❓ *{question}*",
            "actions": [
                {
                    "type": "button",
                    "text": "Answer this",
                    "msg": question,
                    "msg_in_chat_window": True
                }
            ]
        }
        for i, question in enumerate(followup_questions)
    ]

    send_direct_message(response["response"], room_id)

    message1 = """ Based on the information I found, here are some follow-up 
    questions you might want to consider: """
    
    send_direct_message(message1, room_id, attachments=attachments)

    extra_attachments = [
        {
                "actions": [
                    {
                        "type": "button",
                        "text": "Ask Reddit",
                        "msg": "Ask Reddit",
                        "msg_in_chat_window": True
                    }
                ]
            }
    ]
    message = "🙋‍♀️ Want to ask the community? \n See what people are saying on Reddit! 👥💬"
    if should_crowdsource(user_input, final_response):
        extra_attachments.append(
            {
                "actions": [
                    {
                        "type": "button",
                        "text": "Crowdsourcing",
                        "msg": "Crowdsourcing",
                        "msg_in_chat_window": True
                    }
                ]
            }
        )
        message += "  or get input from others in the chat! 🗣️"
    send_direct_message(message, room_id, extra_attachments)           
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
        lastk=5,
        session_id=SESSION, # This must share same session with main agent
        rag_usage=False
    )

    reply = response["response"].strip()
    if reply != "__NEED_WEB_SEARCH__":
        send_direct_message(reply, room_id)
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