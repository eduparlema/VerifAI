from modules.search_results import *
from modules.composer import *
from modules.intent_detection import *
from modules.language_analysis import *
from llmproxy import retrieve, RAG_SESSION, text_upload
from collections import defaultdict

RC_token = os.environ.get("RC_token")
RC_userId = os.environ.get("RC_userId")
RC_API = os.environ.get("RC_API")
ROCKETCHAT_AUTH = {
    "X-Auth-Token": RC_token,
    "X-User-Id": RC_userId,
}

def send_direct_message(message: str, room_id: str, attachments = None) -> None:
    payload = {
        "roomId": room_id,
        "text": message
    }
    if attachments:
        payload["attachments"] = attachments

    response = requests.post(RC_API, headers=ROCKETCHAT_AUTH, json=payload)

    # Optional: handle errors
    if response.status_code != 200:
        print(f"Failed to send message: {response.status_code} - {response.text}")

    return

def generate_response(user_input, room_id, user_name):
    # Detect intention
    intent = intent_detection(user_input, room_id, user_name).strip('"')
    print("intent", intent)

    if intent == "analyze_language":
        print("in analyze_language")
        # Get language analysis
        return language_analysis(user_input, user_name), False, "analyze_language"

    # If generic_reponse: directly return
    if intent != "follow_up_search" and intent != "misinformation_analysis":
        print("in generic response")
        return intent, False, "generic_response"

    # Define variables to keep track of content for the composer
    search_content = []
    rag_content = []

    language_flag = "NO"

    # If misinformation_analysis: Get the queries and proceed to search
    if intent == "misinformation_analysis":
        print("in misinformation_analysis")

        # Analyze the user input
        queries = eval(get_queries(user_input, room_id, user_name))

        # Inform the user about your search
        query_information = inform_user(user_input, queries, user_name)
        send_direct_message(query_information, room_id)
        
        content = []
        for query in queries:
            content = search(query, user_name)
            print('inside the for loop')
            print(content)
            search_content.extend(content["final_sources"])
        print("search content")
        print(search_content)


        # Get language analysis
        # lang_analysis = language_analysis(user_input, user_name)
        language_flag = check_language(user_input, user_name)

    
    # If follow_up_search: Skip getting the queries and just proceed to search (if needed)
    elif intent == "follow_up_search":
        print("in follow up")
        
        # Check RAG
        rag_context = retrieve(
            query = f"Content: {user_input}",
            session_id=f"{RAG_SESSION}_{user_name}",
            rag_threshold = 0.8,
            rag_k = 3)
        
        rag_enough = rag_decide(user_input, rag_context)
        # If Rag not enough -> search needed.
        if rag_enough == "NO":
            content = search(user_input, user_name)
            search_content.extend(content["final_sources"])
        # If Rag enough -> send to composer
        elif rag_enough == "YES":
            rag_content.extend(rag_context)
        else:
            raise ValueError(f"Unexpected response from LLM: {rag_enough}")
            

    # Get composer_input together
    composer_input = {}
    composer_input["search_content"] = ""
    composer_input["rag_content"] = ""

    print("\nPRINTING SOURCES TO SEND COMPOSER!")
    if search_content:
        search_content_parsed = []
        for source in search_content:
            print(f"Source being sent to composer: \n{source}")
            search_content_parsed.append(", ".join(f"{key}='{value}'" for key, value in source.items()))
        composer_input["search_content"] = "\n".join(search_content_parsed)
    print("\n\n")

    if rag_content:
        composer_input["rag_content"] = "\n\n".join(rag_content)


    response = composer(user_input, composer_input, user_name)

    if language_flag == "YES":
        return response, True, intent
    else:
        return response, False, intent
   

def rag_decide(user_question: str, rag_context: str):
    RAG_DECIDE_PROMPT = """
    You are a verification agent inside a fact-checking system.

    Your job is to decide whether the given context (retrieved from trusted
    sources) contains enough reliable, relevant, and specific information to
    confidently answer the user's query.

    To return “YES,” the context must meet **all** of the following conditions:
    1. It is clearly related to the user's question — not vaguely or partially.
    2. It provides enough detail or factual content to support a meaningful answer.
    3. It comes from sources that would be considered trustworthy in context
        (e.g. news outlets, institutions, expert blogs, etc.).
    4. The information can be cited or paraphrased directly to support the
        response — not speculation or generalities.

    If any of these conditions are not met, return “NO”.

    Only return:
    - `YES` → if the LLM could confidently respond using this context and cite it
    - `NO` → if the LLM would struggle to respond accurately or credibly using this context alone

    Do not explain your answer. Do not include any formatting or notes.
    """
    response = generate(
        model='4o-mini',
        system=RAG_DECIDE_PROMPT,
        query=f"User question: {user_question}\nRag context: {rag_context}",
        lastk=0,
        session_id="rag_decider_0",
        rag_usage=False
    )

    if isinstance(response, dict) and "response" in response:
        return response["response"]
    else:
        print(f"ERRO [rag_decide] LLM reponse: {response}")
        return f"ERROR LLM Response: {response}"


if __name__ == "__main__":
    # user_input = "Has the Paris agreement actually reduced global emissions?"    
    # # user_input = "Is Erdogan a dictator?"

    # current_query=""
    # print("\nRespone from Composer:\n>>>>>")
    # print(generate_response(user_input,"room", "Erin123"))
#     content = """"In 2014, they said ‘development’ – now they want to remove Hindu
#     temples and legalize terrorism. Ask yourself who benefits when our traditions are erased. Jai Hind 🙏🏼

# Pass this on to 10 real patriots. If you care about Bharat, don’t stay silent."""
    content = "Is there evidence for corruption in the MAS political party?"
#     composer_response = generate_response(content, "room123", "Erin123")
#     print(f"RESPONSE: {composer_response}")
    # results = smart_search(user_input, "Erin123")
    res = search(content, "Edu123")