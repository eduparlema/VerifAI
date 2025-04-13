from llmproxy import generate
from utils import *

def intent_detection(user_input: str):
    print("[INFO] intent_detection_activated module activated!")
    system_prompt = """
        You are a helpful and friendly assistant that helps users fact-check claims,
        headlines, and social media posts.

        Your job is to:
        1. Detect if the user's message contains a fact-checkable claim (something
        that could be verified or debunked using evidence). A url is a
        fact-checkable claim, and a question that contains a claim is also 
        fact-checkable. Only claims that do not contain any claims at all (e.g.,
        hello, how are you?) are not fact-checkable.
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

def fact_check_tools(user_input: str):
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

def all_search(user_input: str):
    print("[INFO] all_search module activated!")
    response = general_search(user_input)
    print(f"Response from general search: \n{response}")
    return response
    
def general_search(input: str, num_results: int = 10):
    print("[INFO] general_search module activated!")

    # Perform a Google search
    search_results = google_search(input, num_results)

    if not search_results:
        print("[ERROR] No results found.")
        return []
    
    formatted_search_results = []
    
    # Fetch and format each article
    for result in search_results:
        url = result["url"]
        title = result["title"]
        domain = result["source"]
        content = fetch_main_article(url)

        print("[INFO] Fetching article content...")
        print(title)
        print(url)
        print(content)

        if content == "ERROR":
            continue

        formatted_result = format_source(input, url, domain, title, content)

        formatted_search_results.append(formatted_result)              

    # Summarize the articles
    summaries = summarize_article(input, formatted_search_results)

    print("Summaries: ", summaries)

    if not summaries:
        print("[ERROR] No summaries found.")
        return []
    
    # Generate a fact-based response
    response = generate_fact_based_response(input, summaries)

    if not response:
        print("[ERROR] No response generated.")
        return []
    
    print("[INFO] Response generated successfully!")
    return response

def local_search(input: str):
    print("[INFO] general_search module activated!")

def social_search(input: str):
    print("[INFO] social_search module activated!")



if __name__ == "__main__":
    # Example usage
    user_input = "Trump replaced Pride Month with Veterans Month"

    print("[INFO] User input:", user_input)
    response = general_search(user_input)
    print(response)

