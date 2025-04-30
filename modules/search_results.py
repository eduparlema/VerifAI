import json
import os
import re
import requests
from readability import Document
from bs4 import BeautifulSoup
from llmproxy import generate, SESSION
from dotenv import load_dotenv
from urllib.parse import urlparse
from typing import Dict
import ast

load_dotenv()

GOOGLE_API_KEY = os.environ.get("googleSearchApiKey")
SEARCH_ENGINE_ID = os.environ.get("searchEngineId")
FACT_CHECK_API=os.environ.get("googleFactCheckApiKey")
FACT_CHECK_URL=os.environ.get("factCheckApiUrl")

RELEVANCE_THRESHOLD = 0.5
NUM_RELEVAN_RESULTS_THRESHOLD = 5
DIVERSITY_THRESHOLD = 0.7

def search(user_input: str, username: str) -> str:
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
    }
    """

    # 1. Initialization
    search_journey = []
    current_query = user_input
    steps_taken = 0
    max_steps = 5
    collected_results = []

    while steps_taken < max_steps:
        steps_taken += 1
        print(f"[search] Step {steps_taken}")

        # Choose params to perform google search
        chosen_params = choose_search_params(collected_results, current_query, user_input, username)
        print(f"chosen parameters: {chosen_params}")

        # 2. Perform search
        results = perform_search(user_input, username, chosen_params)
        # 3. Evaluate results
        relevant_results = evaluate_relevance(results, user_input, username)
        diversity = evaluate_diversity(collected_results + results, user_input, username)
        print(f"Diversity score so far: {diversity}")

        # 4. Record the step
        search_journey.append({
            "query": current_query,
            "diversity_so_far": diversity,
            "num of relevant sources": len(collected_results),
            "num_results": len(results),
        })

        collected_results.extend(relevant_results)
        print(f"TOTAL RELEVANT: {len(collected_results)}")

        # 5. Reason about what to do next
        if len(collected_results) > NUM_RELEVAN_RESULTS_THRESHOLD and diversity > DIVERSITY_THRESHOLD:
            break

    # 6. Finalize
    final_output = {
        "final_sources": collected_results,
        "search_journey": search_journey,
    }

    print(f"Search journey: {search_journey}")
    print(collected_results)

    return final_output

# ============================== #
#   Perform Search               #
# ============================== #

def perform_search(original_input: str, username: str, chose_params: Dict = None, num_results: int =3) -> list:
    """
    Perform a Google Custom Search and return a list of search results.
    
    Each result includes:
    - url
    - title
    - date (if available)
    - content (scraped text from the page)
    """
    IGNORE = [
        "-filetype:pdf", "-filetype:ppt", "-filetype:doc", "-site:twitter.com", 
        "-site:facebook.com", "-site:instagram.com", "-site:pinterest.com ",
        "-site:tiktok.com", "-site:reddit.com", "-site:linkedin.com"
    ]

    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "num": num_results,
        "excludeTerms": "filetype:pdf"
    }
    
    params.update(chose_params)

    old_q = params["q"]
    ignore_sites = " ".join(IGNORE)
    params["q"] = f"{old_q} {ignore_sites}"

    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        items = response.json().get("items", [])

    except Exception as e:
        # print(f"❌ Search error: {e}")
        return []

    results = []

    for item in items:
        url = item.get("link")
        title = item.get("title")
        print(f'I found a url: {url}')
        snippet = item.get("snippet", "")
        date = extract_date(item, snippet)
        scraped_text = scrape_webpage(url)
        
        if scraped_text == "ERROR":
            continue  # skip bad scrapes

        # # Summarize the article text based on the user's input
        # summary = summarize_content(original_input, scraped_text, username)


        results.append({
            "url": url,
            "title": title,
            "date": date,
            "content": scraped_text
            # "summary": summary
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
        # print(f"⚠️ Fetch error ({url}): {e}")
        return "ERROR"

    try:
        doc = Document(html)
        article_html = doc.summary()
        soup = BeautifulSoup(article_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())  # Clean up excessive whitespace
    except Exception as e:
        # print(f"⚠️ Parsing error ({url}): {e}")
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
        - Keep the summary concise (maximum 3-5 sentences).
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

# ____________________ #
# choose_search_params #
# ____________________ #

def choose_search_params(collected_results: list, current_query:str, user_input:str, username:str):
    CHOOSE_PARAMS_PROMPT = """
    You are a smart and precise search parameter selection agent. You support a
    fact-checking AI system by crafting optimal Google Custom Search queries to
    retrieve the most relevant, trustworthy, and diverse results.

    You will be given the user's query and after the first time, previous results
    you received so that you can update the params accordingly.

    Your task is to analyze the user's input and choose the best search parameters to improve:
    - Relevance
    - Recency (if time-sensitive)
    - Regional context
    - Language fit
    - Result diversity

    If no previous result is provided, just focus on the user's query when 
    choosing the parameters.

    To do this, you may:
    - **Paraphrase** the original query to improve clarity or searchability
    - **Reframe** the query to broaden, narrow, or adjust its perspective
    - **Localize** the query by detecting relevant country or region context
    - **Translate** the query when it's clearly in or about a non-English context
    - **Restrict by date** if the topic is recent, ongoing, or time-sensitive

    ---

    ### You must return a Python dictionary with the following keys:

    **Required:**
    - `"q"` (string): The search query. You may paraphrase, reword, or shift perspective to improve search quality.

    **Optional:**
    - `"lr"` (string): Language restriction (`lang_en`, `lang_es`, etc.). Use if the query suggests a preferred language.
    - `"cr"` (string): Country restriction (`countryUS`, `countryBO`, etc.). Use if the query clearly refers to a specific country.
    - `"dateRestrict"` (string): Restrict by recency. Use only for time-sensitive queries. Accepted values:
        - `"d5"` = past 5 days
        - `"w2"` = past 2 weeks
        - `"m3"` = past 3 months
        - `"y1"` = past year
    - `"filter"` (int): Always set to `1` (removes duplicate results).

    ---

    ### Important:
    Avoid repeating or reusing queries that resulted in the same sources.
    Try to alter the angle, language, country, or time window to access different
    sets of results. It is important to play with the angle and the language structure
    to avoid getting the same after performing a google search.

    ### Output Instructions:
    - Return **ONLY ONE** well-formed Python dictionary (no comments, markdown, or formatting).
    - Do not use the **num** parameter.
    - Do **not** include any explanations.
    - If no optional parameters are needed, omit them.
    - Avoid using the same parameters like queries in subsequent calls which you may find 
    in the past conversations.

    ---

    ### ✅ Examples:

    **Example Input:**  
    "Was the Turkish government's response to the 2023 earthquake effective?"

    **Example Outputs:**  
    ```python
    Example 1:
    {
    "q": "Public opinion turkey government earthquake response 2023",
    "cr": "countryTR",
    "lr": "lang_tr",
    "filter": 1,
    }
    Example 2:
    {
    "q": "Turkey earthquake 2023 preparedness early warning measures",
    "cr": "countryTR",
    "lr": "lang_en",
    "dateRestrict": "y1",
    "filter": 1,
    }
    Example 3:
    {
    "q": "Opposition criticism turkey government earthquake handling",
    "cr": "countryUS",
    "lr": "lang_en",
    "filter": 1,
    }
    Example 4:
    {
    "q": "International reaction turkey earthquake emergency response",
    "cr": "countryUS",
    "lr": "lang_en",
    "filter": 1,
    }
    Example 5:
    {
    "q": "government aid affected regions turkey earthquake 2023",
    "cr": "countryTR",
    "lr": "lang_tr",
    "dateRestrict": "m6",
    "filter": 1,
    }
    """

    # Summarize collected results clearly
    summarized = ""
    for idx, res in enumerate(collected_results, start=1):
        summarized += f"""Source {idx}
            Article Title: {res.get('title', 'Unknown Title')}
            Content: {res.get('content', 'No summary available')}
            """
        
    
    # User prompt: Specific task input
    user_prompt = f"""
        User's original input:
        {user_input}
        Currenty query:
        {current_query}

        Past search results:
        {summarized}
        """

    # Call LLM
    response = generate(
        model="4o-mini",
        system=CHOOSE_PARAMS_PROMPT,
        query=user_prompt.strip(),
        temperature=0,
        lastk=5,
        session_id=f"{SESSION}_{username}",
        rag_usage=False
    )

    try:
        if isinstance(response, dict) and "response" in response:
            parsed = ast.literal_eval(response["response"].strip())
            if isinstance(parsed, dict):
                return parsed
            else:
                raise ValueError("LLM response is not a dictionary.")
        else:
            return f"ERROR with LLM response {response}"
    except (ValueError, SyntaxError) as e:
        print(f"[ERROR] Failed to parse search parameters: {e}")
        return None  # or raise, depending on your error strategy


# ________________________ #
# Decide Next Action       #
# ________________________ #

def decide_next_action(collected_results:list, user_input:str, username:str) -> str:
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
# __________________ #
# Evaluate functions #
# __________________ #
def evaluate_relevance(results: list, user_input: str, username: str) -> list:
    """
    Checks how closely the search results match the user's original query.
    Returns a list of relevant articles.
    """
    # scores = []
    relevant_results = []
    for result in results:
        title, date, content = result["title"], result["date"], result["content"]
        result_info = f"Title: {title}\n Date: {date}\n Content: {content}"
        score = get_relevance_score(result_info, user_input, username)
        print(f"{title} got score {score}")
        if score > RELEVANCE_THRESHOLD:
            relevant_results.append(result)
        # scores.append(score)
    # return sum(scores) / max(1, len(scores))
    return relevant_results


def get_relevance_score(result: str, user_input: str, username: str) -> float:
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
        - 0.5 = Partially related but incomplete, or outdated when the date is
            important within the user's query.
        - 1 = Highly relevant, directly answers the user's question, and is timely.
        - This should be a continuum, do not only score either with 0, 0.5, or 1.
          Feel free to give values in between like 0.7, 0.8, 0.3, etc.

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
        session_id=f"scoring_session_{username}",
        rag_usage=False
    )
    try:
        if isinstance(response, dict) and "response" in response:
            return float(response["response"].strip())
        else:
            print(f"[get_relevant_score ERROR] Invalid LLM response form {response}")
    except ValueError:
        return 0.0
    
def evaluate_diversity(results: str, user_input: str, username: str) -> str:
    """
    Checks how diverse the opinions and perspectives are accross the results
    """
    combined_text = ""
    for result in results:
        combined_text += f"Title: {result['title']}\nDate: {result['date']}\nContent: {result['content']}\n\n"

    diversity_score = get_diversity_score(combined_text, user_input, username)
    return diversity_score

def get_diversity_score(combined_text: str, user_input: str, username: str) -> float:
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
        session_id=f"diversity_scoring_session_{username}",
        rag_usage=False
    )
    print("[get_diversity_score]")
    try:
        if isinstance(response, dict) and "response" in response:
            return float(response["response"].strip())
        else:
            print(f"[get_diversity_score ERROR] Invalid LLM response form {response}")
    except ValueError:
        # Fall back to low diversity if parsing fails
        return 0.0

# _____________________ #
# Next action functions #
# _____________________ #
def paraphrase_query(current_query: str, username: str) -> str:
    """
    Takes the current_query that is being used for search and provides a paraphrased
    version. It should keep the same meaning, use different wording and possibly
    broaden or tighten the focus a little.
    """

    PARAPHRASE_PROMPT = """
        You are an expert at reformulating search queries to improve information
        retrieval from Google search results.

        Given a current query, your task is to paraphrase it:
        - Keep the original meaning.
        - Change the wording enough to potentially match different documents.
        - You can reword slightly more broadly or narrowly if that would likely help.
        - Make sure it still sounds natural and clear.

        Rules:
        - Only return the new paraphrased query as a sentence.
        - Do NOT add explanations, notes, or formatting — just the new query.
        """
    
    response = generate(
        model="4o-mini",
        system=PARAPHRASE_PROMPT,
        query=f"Current query: {current_query}",
        temperature=0.3,
        lastk=8,
        session_id=f"{SESSION}_{username}",
        rag_usage=False
    )

    return response["response"].strip()

