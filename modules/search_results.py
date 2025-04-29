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
# __________________ #
# Evaluate functions #
# __________________ #
def evaluate_relevance(results: list, user_input: str):
    """
    Checks how closely the search results match the user's original query.
    """
    scores = []
    for result in results:
        title, date, content = result["title"], result["date"], result["content"]
        result_info = f"Title: {title}\n Date: {date}\n Content: {content}"
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

# _____________________ #
# Next action functions #
# _____________________ #
def paraphrase_query(current_query: str) -> str:
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
        session_id=SESSION,
        rag_usage=False
    )

    return response["response"].strip()
    


def localize_query():
    pass

def translate_query():
    pass

def reframe_query():
    pass

# ______________________ #
# Final output functions #
# ______________________ #
def deduplicate_results():
    pass


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