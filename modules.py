from llmproxy import generate
from utils import *

def intent_detection(user_input: str, room_id: str, user_name: str):
    print("[INFO] intent_detection_activated module activated!")
    system_prompt = """
        You are a helpful and friendly assistant to a fact-checkable AI Agent.
        Your jobs is to interact with the user and determine whether or not its
        intput contains a fact-checkable claim. More specifically:

        1. Detect if the user's message contains fact-checkable
        (something that could be verified or debunked using evidence).
            - A URL is considered to contain fact-checkable information
            - A question like "I heard that x is y, is this true?" Is fact checkablable.
        2. If the message **does** contain a fact-checkable claim, respond with exactly: `__FACT_CHECKABLE__`
        3. If the message **does not** contain a fact-checkable claim, respond with
            a helpful and friendly message that guides the user.
            - Use a warm tone, emojis, and be engaging.
            - Avoid repeating the same message each time.
            - You should sound human and approachable.

        Here is an example of a good response to a user who just said “hi”:
        ---
        🤖 Hey there! I'm your conversational fact-checking assistant.
        If you've seen a claim, news article, or social media post and you're wondering,
        “Is this actually true?” — I've got you.

        You can send me:
        🧾 A statement you want checked  
        🌐 A link to a news article  
        🗣️ A quote or screenshot from social media

        🔍 Go ahead—what claim should we check today?
        ---

        ONLY output either:
        - `__FACT_CHECKABLE__`  
        **OR**
        - a friendly message like the one above, appropriate for the input.
    """
    response = generate(
        model="4o-mini",
        system=system_prompt,
        query=user_input,
        temperature=0.5,
        lastk=1,
        session_id=SESSION,
        rag_usage=False
    )
    return response["response"]

def fact_check_tools(user_input: str, room_id: str, user_name:str):
    print("[INFO] fact_check_tools module activated!")
    keywords = extract_keywords(user_input)
    fact_check_data = query_fact_check_api(keywords)

    # Check if we get something from Fact Checking API
    if fact_check_data and fact_check_data.get('claims'):
        context = prepare_fact_check_context(fact_check_data["claims"])
        verdict = generate_verdict(user_input, context)
        # TODO: ADD BUTTON FUNCTIONALITY HERE!
        return verdict
    else:
        return "__NO_FACT_CHECK_API__"

def all_search(user_input: str, room_id: str, user_name:str):
    print("[INFO] all_search module activated!")
    response = general_search(user_input, room_id, user_name)
    print(f"Response from general search: \n{response}")
    return response
    
def general_search(input: str, room_id: str, user_name:str, num_results: int = 10):
    TOTAL_RESULTS_DESIRED = 5
    print("[INFO] general_search module activated!")
    print(f"[general_search_module] room_id: {room_id}, user: {user_name}")
    # Perform a Google search
    search_results = google_search(input, num_results)
    send_direct_message("Retrieved results from Google, making a decision!", room_id)
    if not search_results:
        print("[ERROR] No results found.")
        return []

    all_summaries = []
    total_summary = 0
    index_search_results = 0
    
    while total_summary < 5:

        # Retrieve the next website in all search results.
        result = search_results[index_search_results]

        # Extact the url, title, and content of the website.
        url = result["url"]
        title = result["title"]
        content = fetch_main_article(url)

        # If fetching the content fails, skip this website.
        if content == "ERROR":
            index_search_results += 1
            continue
        # Else, Format the url, title, and content information properly.
        else: 
            formatted_result = format_source(input, url, title, content)
            send_direct_message("Summarizing sources", room_id)
            summary_result = summarize_source(input, formatted_result)

            # If summarizing the content fails, skip this website.
            if summary_result == "ERROR":
                index_search_results += 1
                continue

            # Else, add the source to the all_summaries list.
            else: 
                total_summary += 1
                index_search_results += 1

                all_summaries.append(summary_result)
    send_direct_message("Generating a response...", room_id)
    # Generate a response based on all summarized sources.
    response = generate_fact_based_response(input, all_summaries)
    if not response:
        print("[ERROR] No response generated.")
        return []
    
    print("[INFO] Response generated successfully!")
    return response

def local_search(input: str, room_id: str, user_name:str):
    print("[INFO] general_search module activated!")

def social_search(input: str, room_id: str, user_name:str):
    print("[INFO] social_search module activated!")

if __name__ == "__main__":
    # Example usage
    user_input = "Trump replaced Pride Month with Veterans Month"

    print("[INFO] User input:", user_input)
    response = general_search(user_input)
    print(response)

