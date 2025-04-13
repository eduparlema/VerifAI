from llmproxy import generate
from utils import *

def no_facts(input: str):
    print("[INFO] no_facts module activated!")

def fact_check_tools(input: str):
    print("[INFO] fact_check_tools module activated!")

def all_search(input: str):
    print("[INFO] all_search module activated!")
    
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

