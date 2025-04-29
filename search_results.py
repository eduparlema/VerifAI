import json
import os
import re
import requests
from readability import Document
from bs4 import BeautifulSoup
from llmproxy import generate
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

GOOGLE_API_KEY = os.environ.get("googleSearchApiKey")
SEARCH_ENGINE_ID = os.environ.get("searchEngineId")
FACT_CHECK_API=os.environ.get("googleFactCheckApiKey")
FACT_CHECK_URL=os.environ.get("factCheckApiUrl")
SESSION = os.environ.get("SESSION")

RELEVANCE_THRESHOLD = 0.7
DIVERSITY_THRESHOLD = 0.7

EXTRACT_KEYWORDS_PROMPT = """
    You are a search assistant in a fact-checking system.

    Your task is to extract a **minimal, high-precision keyword query** from a user claim, article, or sentence. This query will be used to search the Google Fact Check Tools API.

    Your objective is to capture only the **most essential search-relevant concepts**:
    - WHO: people, organizations, public figures
    - WHAT: events, policies, decisions, bans, claims
    - WHERE: countries, regions, institutions (only if directly mentioned)
    - HOW (only if essential): mechanism like replacement, censorship, ban

    Guidelines:
    - Extract **only the necessary keywords** — nouns and named entities are preferred.
    - DO NOT include generic terms like: “claim”, “news article”, “report”, “viral”, or “statement”.
    - DO NOT include any dates unless explicitly stated and essential.
    - DO NOT include full sentences, phrases, or questions.
    - Avoid verbs unless they are crucial to the meaning (e.g., "replace", "ban", "censor").
    - Do not include connectors, filler words, or speculation.

    Format:
    - Output a single short search query (5–10 words).
    - No quotes, no bullet points, no extra explanation — just the keyword string.

    Examples:
    Input: “I heard Trump wants to ban TikTok in the U.S.”
    Output: Trump TikTok ban United States

    Input: “Did Pfizer fake COVID vaccine data?”
    Output: Pfizer COVID vaccine

    Input: “Is it true that Bill Gates owns all US farmland?”
    Output: Bill Gates farmland United States

    Input: “Is it true Trump is changing pride month for veterans month?”
    Output: trump pride month veterans month

    ONLY output the search keywords. Nothing else.

"""

LOCAL_GOOGLE_SEARCH_PROMPT = """
    You are a smart assistant supporting a fact-checking system by improving how user queries are searched on Google.

    Your job is to suggest search parameters that will yield the most relevant and regionally appropriate results.

    🧠 Task:
    Based on the user's input, determine if the query should be searched in a specific language or country context.

    If so, provide:
    - A version of the query translated into the appropriate language (if needed).
    (The query should be customized for retrieving better search results, using key words etc)
    - The most relevant **language code** (e.g., 'tr' for Turkish, 'en' for English).
    - The most relevant **country code** (e.g., 'TR' for Turkey, 'US' for United States).
    
    Stick to the following structure:

    📦 Output format (as a JSON dictionary). For example:
    {
    "query": "<query in Turkish>",
    "language": "<tr>",
    "country": "<TR>"
    }
"""

# EXTRACT_KEYWORDS_PROMPT = """
# You are a political fact-checking assistant specialized in identifying canonical
# claims from user input.

# Your task is to carefully read the user's latest message along with the recent 
# conversation history to reconstruct the full fact-checkable claim.


# Important:
# - If the latest user input depends on previous context (e.g., uses pronouns like 
#   "it", "this", or refers vaguely to "the law," "the bill," "the policy," etc.), 
#   you MUST infer the missing subject from the conversation history to make the 
#   extracted claim complete and meaningful.
# - Your goal is to output a complete, clean, and neutral factual statement that 
#   could be used directly for a Google search.

# Here are the rules:
# - ✅ Keep the claim concise (preferably under 20 words).
# - ✅ Remove any emojis, slang, extra speculation ("I heard", "apparently", etc.).
# - ✅ Focus only on the factual content that could realistically be verified or 
#     debunked.
# - ✅ Use clear, neutral language without exaggeration.
# - ✅ Preserve names, dates, numbers, and important qualifiers (e.g., locations, 
#     timeframes).
# - ❌ Do not add new information.
# - ❌ Do not editorialize or judge whether the claim is true or false.

# Your output must be a single line with the canonical claim.

# ---
# Example 1:
# - Input: "I heard Biden wants to ban all gas stoves!! 😱 Is that true?"
# - Output:"Biden plans to ban gas stoves."

# Example 2:
# - Input: "Can you check if immigrants are voting illegally in U.S. elections?"
# - Output: "Immigrants are voting illegally in U.S. elections."

# Example 3 (Ambiguous latest input requiring conversation history):
# - Conversation History:
#     User: "Can you check if the Clean Energy Act passed?"
#     Bot: "The Clean Energy Act was debated last week. Let me find out more."
# - Latest User Input: "Was it put into effect yet?"
# - Output:"The Clean Energy Act has been put into effect."

# ---

# Summary:
# Always reconstruct the full factual statement needed for accurate fact-checking.  
# If the current user input alone is unclear, infer meaning based on recent 
# conversation history.
# """

def search_results(
        user_input: str, 
        room_id: str, 
        user_name: str, 
        num_results: int = 10, 
        follow_up: bool = False
    ):
    # Extract keywords from user input and past context
    search_keywords = extract_keywords(user_input, user_name)

    # Retrieve results from Google Fact Check API
    fact_check_results = fact_check_tools(search_keywords, room_id, user_name)

    # Retreive results from Google Custom Search API
    general_results = unified_search_pipeline(search_keywords, room_id, user_name, 
                                                    google_search, num_results)
    
    # Retrieve results from local Google Custom Search API
    local_results = unified_search_pipeline(search_keywords, room_id, user_name, 
                                                local_google_search, num_results)
    
    # Generate a verdict based on the fact-check results
    
    
    
    print("[INFO] Search keywords:\n")
    print(search_keywords)
    print("\n\n**********\n\n")
    print("[INFO] Fact check results:")
    print(fact_check_results)
    print("\n\n**********\n\n")
    print("[INFO] Google search results:")
    print(general_results)
    print("\n\n**********\n\n")
    print("[INFO] Local Google search results:")
    print(local_results)


    

def extract_keywords(user_input: str, username: str) -> str:
    response = generate(
        model="4o-mini",
        system=EXTRACT_KEYWORDS_PROMPT,
        query=user_input,
        temperature=0.1,
        lastk=5,
        session_id=f"{SESSION}_{username}",
        rag_usage=False
    )
    return response["response"]

def google_search(query: str, num_results: int = 10) -> list:
    """
    Performs a Google Custom Search API query and returns the top 'num_results' links.
    """
    cleaned_query = query.replace('"', '') 
                    
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "q": cleaned_query,
        "num": num_results
    }

    try:
        response = requests.get(search_url, params=params, timeout=10)

        response.raise_for_status()
        data = response.json()

        results = data.get("items", [])

        google_results = []
        
        for item in results:
            url = item.get("link")
            title = item.get("title")
            snippet = item.get("snippet", "")
    
            # Try to extract date from metatags if available
            date = ""
            pagemap = item.get("pagemap", {})
            metatags = pagemap.get("metatags", [{}])
            if metatags and isinstance(metatags, list):
                meta = metatags[0]
                date = meta.get("article:published_time") or meta.get("og:updated_time")

            # If no date from metadata, try to regex from snippet
            if not date:
                date_match = re.search(r'(\b\d{1,2}\s(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4}\b|\b\d{4}-\d{2}-\d{2}\b)', snippet)
                if date_match:
                    date = date_match.group(0)

            google_results.append({
                        "url": url,
                        "title": title,
                        "date": date,
                    })
            
        return google_results

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    return []

def unified_search_pipeline(
    query: str,
    room_id: str,
    user_name: str,
    search_fn,
    total_results: int = 3,
    message_prefix: str = ""
) -> str:
    print(f"[INFO] unified_search_pipeline using {search_fn.__name__}")

    search_results = search_fn(query)
    if not search_results:
        print("[ERROR] No results found.")
        return []

    total_results = min(3, len(search_results))
    all_summaries = []
    idx = 0
    while len(all_summaries) < total_results:
        result = search_results[idx]
        url, title, date = result["url"], result["title"], result.get("date", "")
        content = fetch_main_article(url)

        if content == "ERROR":
            idx += 1
            continue

        formatted = format_source(url, title, date, content)

        all_summaries.append(formatted)
        idx += 1

    #if message_prefix:
        #send_direct_message(message_prefix, room_id)

    summaries = "\n--\n".join(all_summaries)

    print("[INFO] Response generated successfully!")
    return summaries

def local_google_search(user_query: str, num_results: int = 10) -> list:
    """
    Performs a context-aware Google search using parameters suggested by the LLM,
    such as local language and country, without limiting to specific sites.
    """
    response = generate(
        model="4o-mini",
        system=LOCAL_GOOGLE_SEARCH_PROMPT,
        query=user_query,
        temperature=0.2,
        lastk=3,
        session_id="search_param_suggester_0",
        rag_usage=False
    )
    try:
        suggestions = eval(response["response"])
        language = suggestions.get("language", "en")
        country = suggestions.get("country", "US")
        query = suggestions.get("query", user_query).strip()

        params = {
            "key": GOOGLE_API_KEY,
            "cx": SEARCH_ENGINE_ID,
            "q": f'{query} -filetype:pdf -filetype:ppt -filetype:doc -site:twitter.com -site:facebook.com -site:instagram.com -site:pinterest.com -site:tiktok.com',
            "num": num_results,
            "lr": f"lang_{language}",
            "cr": f"country{country}"
        }

        search_url = "https://www.googleapis.com/customsearch/v1"
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get("items", [])

        google_results = []
        for item in results:
            url = item.get("link")
            title = item.get("title")
            snippet = item.get("snippet", "")
    
            # Try to extract date from metatags if available
            date = ""
            pagemap = item.get("pagemap", {})
            metatags = pagemap.get("metatags", [{}])
            if metatags and isinstance(metatags, list):
                meta = metatags[0]
                date = meta.get("article:published_time") or meta.get("og:updated_time")

            # If no date from metadata, try to regex from snippet
            if not date:
                date_match = re.search(r'(\b\d{1,2}\s(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4}\b|\b\d{4}-\d{2}-\d{2}\b)', snippet)
                if date_match:
                    date = date_match.group(0)            
                    
            google_results.append({
                "url": url,
                "title": title,
                "date": date,
            })

        return google_results

    except Exception as e:
        print(f"❌ Failed to execute localized search: {e}")
        return []

def fetch_main_article(url: str, timeout: int = 10) -> str:
    """
    Fetches the main article text from a given URL.
    """
    try:
        response = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        })
        response.raise_for_status()
        html = response.text
    except Exception as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return "ERROR"

    try:
        doc = Document(html)
        article_html = doc.summary()
        soup = BeautifulSoup(article_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())
    except Exception as e:
        print(f"[ERROR] Failed to parse article: {e}")
        return "ERROR"

def format_source(url, title, date, article_text):
    """
    Formats the claim and article text into a structured input for the LLM.
    """
    return f"URL: {url} \n Title: {title} \n Date:{date} \n Content: {article_text}"

def fact_check_tools(keywords: str, room_id: str, user_name:str):
    print("[fact_check_tools] fact_check_tools module activated!")
    fact_check_data = query_fact_check_api(keywords)

    # Check if we get something from Fact Checking API
    if fact_check_data and fact_check_data.get('claims'):
        context = prepare_fact_check_context(fact_check_data["claims"])
        return context
    
    print("[fact_check_tools]No results found on Google Fact check API!")
    return ""

def prepare_fact_check_context(claims):
    evidence = []
    for claim in claims:
        claim_text = claim.get("text", "")
        claimant = claim.get("claimant", "Unknown")
        for review in claim.get("claimReview", []):
            reviewer = review.get("publisher", {}).get("name", "Unknown")
            rating = review.get("textualRating", "")
            review_url = review.get("url", "")
            review_date = review.get("reviewDate", "")
            article_text = fetch_full_content(review_url)
            content_block = f"""
                            Url: {review_url}
                            Title: {claim_text}
                            Date: {review_date}
                            Rating: {rating}
                            Content:
                            {article_text}
                            """
            evidence.append(content_block)
    return "\n--\n".join(evidence)

def query_fact_check_api(keywords: str):

    params = {
        "query": keywords,
        "key": FACT_CHECK_API,
        "pageSize": 5,
        "languageCode": 'en'
    }
    try:
        response = requests.get(FACT_CHECK_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error querying Fact Check API: {e}")
        return None
    
def fetch_full_content(url: str, timeout: int = 10) -> str:
    try:
        headers = {
            "User-Agent": 'Mozilla/5.0',
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        html = response.text
    except Exception as e:
        print(f"[ERROR] Error fetching {url}: {e}")
        return ""

    try:
        doc = Document(html)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "html.parser")
    except Exception as e:
        print("[WARN] Readability failed, falling back to raw content.")
        soup = BeautifulSoup(html, "html.parser")

    for unwanted in soup(["script", "style", "header", "footer", "nav", "aside"]):
        unwanted.extract()

    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())

def generate_verdict(user_claim: str, evidence: str, user_name: str):

    response = generate(
    model="4o-mini",
    system=GENERATE_VERDICT_PROMPT,
    query=f"""User Claim: {user_claim}
            Fact-Check Evidence:
            {evidence}
            """,
    temperature=0.4,
    lastk=3,
    session_id=f"{SESSION}_{user_name}",
    rag_usage=False
    )
    return response["response"]

# if __name__ == "__main__":
#     query = "Was Brexit bad for EU"
#     search_results(query, "123", "erin")



    
    
    
def search(user_input):
    """
    Determine the google search parameters based on user input. This includes:
        - Deciding if the results it got are relevant.
        - Deciding if the results it got are enough to provide the user with a
          detailed answer confidently.
        - Deciding what type of search to perform: add parameters for local search,
          translation, change region, translate language, paraphrase user input.

    This agent should raise relevant flags (bias, a cluster of sources are from
    a given country, local results seem biased/incomplete, etc)
          
    Output should follow the format:
    {
      "title": "Title of the article",
      "summary": "Short LLM-paraphrased summary of the content",
      "source_url": "https://example.com",
      "bias_tag": "center",  // left, right, center, unknown
      "publication_date": "2024-06-20",
      "location": "TR" (If relevant)
    }
    """
    pass

def search(user_input):
    """
    Agentic Search Function:
    - Treats the search process as an evolving plan.
    - After each search, evaluates:
        - Relevance
        - Sufficiency
        - Diversity
    - Decides dynamically whether to:
        - Accept the results
        - Modify the query (paraphrase, localize, translate, reframe)
        - Gather complementary perspectives
    - Terminates when confident results are obtained or no meaningful improvements are possible.
    
    Output:
    {
        "final_sources": list of dicts (title, url, snippet, etc.),
        "search_journey": list of steps taken (each step = action, query, results),
        "final_decision_reasoning": str
    }
    """

    # 1. Initialization
    search_journey = []
    current_query = user_input
    thoughts = []
    steps_taken = 0
    max_steps = 5
    collected_results = []

    while steps_taken < max_steps:
        steps_taken += 1

        # 2. Perform search
        results = perform_search(current_query)

        # 3. Evaluate results
        relevance = evaluate_relevance(results, user_input)
        diversity = evaluate_diversity(collected_results + results)

        # 4. Record the step
        search_journey.append({
            "query": current_query,
            "action": "search",
            "relevance": relevance,
            "diversity_so_far": diversity,
            "num_results": len(results),
            "results": results
        })

        collected_results.extend(results)

        # 5. Reason about what to do next
        if relevance > RELEVANCE_THRESHOLD and diversity > DIVERSITY_THRESHOLD:
            final_decision_reasoning = f"Confident answer obtained after {steps_taken} step(s)."
            break
        else:
            next_action = decide_next_action(collected_results, user_input)
            thoughts.append(next_action)

            if next_action == "paraphrase":
                current_query = paraphrase_query(user_input)
            elif next_action == "localize":
                current_query = localize_query(user_input)
            elif next_action == "translate":
                current_query = translate_query(user_input)
            elif next_action == "reframe":
                current_query = reframe_query(user_input)
            else:
                # No better action left — stop
                final_decision_reasoning = "No further actions likely to improve search. Best effort."
                break

    # 6. Finalize
    final_output = {
        "final_sources": deduplicate_results(collected_results),
        "search_journey": search_journey,
        "final_decision_reasoning": final_decision_reasoning,
        "internal_thoughts": thoughts
    }

    return final_output

# ============================== #
#   Perform Search               #
# ============================== #

def perform_search(original_input: str, query: str, username: str, num_results: int = 5) -> list:
    """
    Perform a Google Custom Search and return a list of search results.
    
    Each result includes:
    - url
    - title
    - date (if available)
    - content (scraped text from the page)
    """

    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "q": query.replace('"', ''),
        "num": num_results
    }

    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        items = response.json().get("items", [])

    except Exception as e:
        print(f"❌ Search error: {e}")
        return []

    results = []

    for item in items:
        url = item.get("link")
        title = item.get("title")
        snippet = item.get("snippet", "")
        date = extract_date(item, snippet)
        scraped_text = scrape_webpage(url)
        
        if scraped_text == "ERROR":
            continue  # skip bad scrapes

        # Summarize the article text based on the user's input
        summary = summarize_content(original_input, scraped_text, username)


        results.append({
            "url": url,
            "title": title,
            "date": date,
            "content": scraped_text,
            "summary": summary
        })

    return results


def extract_date(item: dict, snippet: str) -> str:
    """
    Extract a publication date from search metadata or snippet text.
    """
    meta = (item.get("pagemap", {}).get("metatags") or [{}])[0]
    date = meta.get("article:published_time") or meta.get("og:updated_time")

    if not date:
        match = re.search(r'(\b\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s\d{4}\b|\b\d{4}-\d{2}-\d{2}\b)', snippet)
        date = match.group(0) if match else ""

    return date

def scrape_webpage(url: str, timeout: int = 10) -> str:
    """
    Fetch the main readable text from a webpage using Readability and BeautifulSoup.
    """
    try:
        response = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        })
        response.raise_for_status()
        html = response.text
    except Exception as e:
        print(f"⚠️ Fetch error ({url}): {e}")
        return "ERROR"

    try:
        doc = Document(html)
        article_html = doc.summary()
        soup = BeautifulSoup(article_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())  # Clean up excessive whitespace
    except Exception as e:
        print(f"⚠️ Parsing error ({url}): {e}")
        return "ERROR"
    
def summarize_content(user_input: str, article_text: str, username: str) -> str: 
    """
    Summarize the article focusing only on information related to the user's query.
    """
    system_prompt = """You are a helpful assistant that summarizes articles in a 
    focused way, based on a user query."""

    user_prompt = f"""
        User Query:
        "{user_input}"

        Article Text:
        \"\"\"
        {article_text}
        \"\"\"

        Instructions:
        - Summarize only the parts of the article that are directly relevant to the user query.
        - If there is no relevant information, respond with: "No relevant information found."
        - Keep the summary concise (maximum 3–5 sentences).
        """

    response = generate(
        model="4o-mini",
        system=system_prompt,
        query=user_prompt,
        temperature=0.1,
        lastk=5,
        session_id=f"{SESSION}_{username}",
        rag_usage=False
    )

    return response["response"].strip()


# ________________________ #
# Decide Next Action       #
# ________________________ #

def decide_next_action(collected_results:list , user_input:str, username:str) -> str:
    """
    Decide the next search action based on current search results and the user's input.
    Returns a dictionary like:
    {
        "action": "paraphrase" | "localize" | "translate" | "reframe" | "stop",
        "query": "<new query text>",
        "language": "<language_code if changed>",
        "country": "<country_code if localized>"
    }
    """

    # Summarize collected results clearly
    summarized = ""
    for idx, res in enumerate(collected_results, start=1):
        summarized += f"""Source {idx}
            Article Title: {res.get('title', 'Unknown Title')}
            Summary: {res.get('summary', 'No summary available')}

            """

    # System prompt: Behavior, rules, format
    system_prompt = """
        You are a search strategy assistant helping an AI agent optimize information retrieval.

        Instructions:
        - Analyze the user's query and the current search results.
        - Choose the best next action based on the information.
        - Choose ONLY one action:
            - "paraphrase" → reword the query differently
            - "localize" → add local/regional context to the query
            - "translate" → rewrite the query in a different language
            - "reframe" → shift the perspective (broader, narrower, or alternate angle)
            - "stop" → if the results are sufficient or improving is unlikely

        📦 Output format (as a JSON dictionary). Example:
        {
            "action": "<one of: paraphrase, localize, translate, reframe, stop>",
            "query": "<rephrased or updated query, or same as original if no change>",
            "language": "<2-letter language code if changed, else null>",
            "country": "<2-letter country code if changed, else null>"
        }

        Notes:
        - If no language or country change applies, set them to null.
        - Always produce valid JSON. Do not explain anything outside the JSON.
        """

    # User prompt: Specific task input
    user_prompt = f"""
        User Query:
        "{user_input}"

        Top Search Results:
        {summarized}
        """

    # Call LLM
    response = generate(
        model="4o-mini",
        system=system_prompt.strip(),
        query=user_prompt.strip(),
        temperature=0,
        lastk=5,
        session_id=f"{SESSION}_{username}",
        rag_usage=False
    )

    try:
        action_data = json.loads(response["response"])
    except Exception as e:
        print(f" Failed to parse LLM output: {e}. Defaulting to stop.")
        action_data = {
            "action": "stop",
            "query": user_input,
            "language": None,
            "country": None
        }

    return action_data



# ________________________ #
# Start Evaluate functions #
# ________________________ #
def evaluate_relevance(results: list, user_input: str):
    """
    Checks how closely the search results match the user's original query.
    """
    scores = []
    for result in results:
        result_info = f"Title: {result["title"]}\n Date: {result["date"]}\n Content: {result["content"]}"
        score = get_relevance_score(result_info, user_input)
        scores.append(score)
    return sum(scores) / max(1, len(scores))


def get_relevance_score(result: str, user_input: str) -> float:
    SCORE_PROMPT = SCORE_PROMPT = """
        You are an expert search quality evaluator.

        Your task is to assess how relevant a given search result is to a user's original query.

        When scoring, consider:
        - How directly the result addresses the user's question or topic.
        - How informative and specific the content is.
        - Whether the publication date makes the result outdated for answering the query.

        Scoring Guidelines:
        - Score between 0 and 1.
        - 0 = Completely irrelevant or outdated.
        - 0.5 = Partially related but incomplete, outdated, or off-topic in parts.
        - 1 = Highly relevant, directly answers the user's question, and is timely.

        Output:
        Strictly only return a number between 0 and 1. No explanation, no text,
        no formatting, just the number.
        """

    response = generate(
        model="4o-mini",
        system=SCORE_PROMPT,
        query=f"Result: {result}. User input: {user_input}",
        temperature=0.3,
        lastk=1,
        session_id="scoring_session",
        rag_usage=False
    )
    try:
        return float(response["response"].strip())
    except ValueError:
        return 0.0
    
def evaluate_diversity(results: str, user_input: str) -> str:
    """
    Checks how diverse the opinions and perspectives are accross the results
    """
    combined_text = ""
    for result in results:
        combined_text += f"Title: {result['title']}\nDate: {result['date']}\nContent: {result['content']}\n\n"

    diversity_score = get_diversity_score(combined_text, user_input)
    return diversity_score

def get_diversity_score(combined_text: str, user_input: str) -> float:
    DIVERSITY_PROMPT = """
    You are an expert opinion diversity evaluator.

    Your task is to analyze a set of search results and determine how diverse the opinions and perspectives are.

    Consider:
    - Are there multiple clearly distinct viewpoints?
    - Do the results show disagreement, contrasting interpretations, or different framings?
    - Or do they all agree and present similar narratives?

    Scoring Guidelines:
    - Score between 0 and 1.
    - 0 = All results express the same opinion or very minor variations.
    - 0.5 = Some variation but results are still largely similar.
    - 1 = Strongly contrasting opinions and multiple distinct perspectives.

    Output:
    ONLY return a number between 0 and 1. No explanation, no formatting, just the number.
    """

    response = generate(
        model="4o-mini",
        system=DIVERSITY_PROMPT,
        query=f"User Question: {user_input}\n\nSearch Results:\n{combined_text}",
        temperature=0.3,
        lastk=1,
        session_id="diversity_scoring_session",
        rag_usage=False
    )
    
    try:
        return float(response["response"].strip())
    except ValueError:
        # Fall back to low diversity if parsing fails
        return 0.0

# ______________________ #
# End Evaluate functions #
# ______________________ #

if __name__ == "__main__":

    user_input = "Was there any credible evidence of widespread voter fraud in the 2020 U.S. presidential election?"
    current_query="voter fraud in the 2020 U.S. presidential election"

    search_journey = []
    current_query = user_input
    thoughts = []
    steps_taken = 0
    max_steps = 5
    collected_results = []

    while steps_taken < max_steps:
        steps_taken += 1

        # 2. Perform search
        results = perform_search(user_input, current_query, "test_user")
        print(f"results: {results}")

        # 3. Evaluate results
        relevance = evaluate_relevance(results, user_input)
        print(f"relevance: {relevance}")
        diversity = evaluate_diversity(collected_results + results, user_input)
        print(f"diversity: {diversity}")
        # 4. Record the step
        search_journey.append({
            "query": current_query,
            "action": "search",
            "relevance": relevance,
            "diversity_so_far": diversity,
            "num_results": len(results),
            "results": results
        })

        collected_results.extend(results)

        # 5. Reason about what to do next
        if relevance > RELEVANCE_THRESHOLD and diversity > DIVERSITY_THRESHOLD:
            final_decision_reasoning = f"Confident answer obtained after {steps_taken} step(s)."
            break
        else:
            next_action = decide_next_action(collected_results, user_input)
            thoughts.append(next_action)
            print(f"NEXT ACTION: {next_action}")