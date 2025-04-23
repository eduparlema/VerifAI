from urllib.parse import urlparse
import os
import requests
from readability import Document
from bs4 import BeautifulSoup
from llmproxy import generate
from dotenv import load_dotenv
import re
from prompt import *
from typing import Optional, List, Dict


RC_API = os.environ.get("RC_API")
RC_token = os.environ.get("RC_token")
RC_userId = os.environ.get("RC_userId")

ROCKETCHAT_AUTH = {
    "X-Auth-Token": RC_token,
    "X-User-Id": RC_userId,
}

reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT
)

load_dotenv()

GOOGLE_API_KEY=os.environ.get("googleSearchApiKey")
SEARCH_ENGINE_ID=os.environ.get("searchEngineId")
FACT_CHECK_API=os.environ.get("googleFactCheckApiKey")
FACT_CHECK_URL=os.environ.get("factCheckApiUrl")

print(GOOGLE_API_KEY)
print(SEARCH_ENGINE_ID)

SESSION = "VerifAI_Session_28"

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
            domain = urlparse(url).netloc.replace("www.", "")
            google_results.append({
                        "url": url,
                        "title": title,
                        "source": domain,
                    })
            
        return google_results

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    return []

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
        session_id="search_param_suggester",
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
            domain = urlparse(url).netloc.replace("www.", "")
            google_results.append({
                "url": url,
                "title": title,
                "source": domain,
            })

        return google_results

    except Exception as e:
        print(f"❌ Failed to execute localized search: {e}")
        return []

def format_source(user_input, url, title, article_text):
    """
    Formats the claim and article text into a structured input for the LLM.
    """
    return {
        "Topic": user_input,
        "URL": url,
        "Title": title,
        "Content": article_text
    }

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
    
def summarize_source(user_input: str, source: dict) -> str:
    """
    Generate fact-focused summaries for a list of articles relevant to a given claim.
    """
    title = source.get("Title", "unknown")
    text = source.get("Content", "")
    url = source.get("URL", "unknown")

    query = f"""
    Here is the topic or claim: {user_input}.
    Here is the article name: {title}.
    Here is the article text: {text}
    """

    try:
        response = generate(
            model='4o-mini',
            system=GENERATE_VERDICT_PROMPT,
            query=query,
            temperature=0.2,
            lastk=3,
            session_id=SESSION,
            rag_usage=False
        )

        article_summary = response.get("response", "")

        if article_summary == "":
            return "ERROR"
        
        summary = {
        "title": title,
        "url": url,
        "summary": article_summary
        }

    except Exception as e:
        print(f"Error summarizing article '{title}': {e}")
        return "ERROR"
    
    return summary


def generate_fact_based_response(user_input: str, summaries: list) -> str:
    """
    Generate a fact-based answer to a user's question or claim by synthesizing
    information from article summaries, using citations with URLs.
    """

    formatted_summaries = "\n\n".join([
        f"- Title: {item['title']}\n  URL: {item['url']}\n Summary: {item['summary']}"
        for item in summaries
    ])

    query = f"""User Input: {user_input}

    Summaries:
    {formatted_summaries}
    """

    response = generate(
        model="4o-mini",
        system=SUMMARIZE_ALL_SOURCES_PROMPT,
        query=query,
        temperature=0.4,
        lastk=3,
        session_id=SESSION,
        rag_usage=False
    )

    return response["response"]

def extract_keywords(user_input: str):

    response = generate(
        model="4o-mini",
        system=EXTRACT_KEYWORDS_PROMPT,
        query=user_input,
        temperature=0.1,
        lastk=3,
        session_id="keyword_session_0",
        rag_usage=False
    )

    return response["response"]

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
                            Claim: {claim_text}
                            Claimant: {claimant}
                            Reviewer: {reviewer}
                            Review Date: {review_date}
                            Rating: {rating}
                            Source: {review_url}
                            Extracted Article Content:
                            {article_text}
                            """
            evidence.append(content_block)
    return "\n\n--\n\n".join(evidence)

def generate_verdict(user_claim: str, evidence: str):

    response = generate(
    model="4o-mini",
    system=GENERATE_VERDICT_PROMPT,
    query=f"""User Claim: {user_claim}
            Fact-Check Evidence:
            {evidence}
            """,
    temperature=0.4,
    lastk=3,
    session_id=SESSION,
    rag_usage=False
    )
    return response["response"]

def send_direct_message(message: str, room_id: str, attachments: Optional[List[Dict]] = None) -> None:
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

def add_params_to_module(module_str, *extra_params):
    """
    Adds extra parameters to a function call string before evaluation.

    Args:
        module_str (str): Original function call string, e.g., "fact_check_tools('Trump')"
        *extra_params: Additional parameters to add, e.g., 'param2', 'param3'

    Returns:
        str: Modified function call string with all parameters
    """
    match = re.match(r"(\w+)\((.*)\)", module_str.strip())
    if not match:
        raise ValueError("Invalid function call string")

    func_name, existing_param = match.groups()

    # Ensure existing_param isn't empty and remove trailing commas/spaces
    all_params = [existing_param.strip()] if existing_param.strip() else []

    # Add extra parameters, stringify if not already strings
    for param in extra_params:
        if isinstance(param, str) and not param.strip().startswith(("'", '"')):
            param = f"'{param}'"
        all_params.append(str(param))

    new_call = f"{func_name}({', '.join(all_params)})"
    return new_call



def generate_fact_based_response_custom(user_input: str, summaries: list) -> str:
    """
    Generate a fact-based answer to a user's question or claim by synthesizing
    information from article summaries, using citations with URLs.
    """

    formatted_summaries = "\n\n".join([
        f"- Title: {item['title']}\n  URL: {item['url']}\n Summary: {item['summary']}"
        for item in summaries
    ])

    query = f"""User Input: {user_input}

    Summaries:
    {formatted_summaries}
    """

    response = generate(
        model="4o-mini",
        system=SUMMARIZE_ALL_SOURCES_PROMPT,
        query=query,
        temperature=0.4,
        lastk=3,
        session_id=SESSION,
        rag_usage=False
    )

    return response["response"]

def all_search_verdict(general_response, local_response, social_media_response):
    system_prompt = f"""
    You are a fact-checking assistant. You have just received search results from three domains: general web, local news, and social media.

    Your task is to:
    - Summarize key points from each domain separately.
    - Highlight any agreements or contradictions.
    - Include source links explicitly.
    - Provide a concise verdict at the end if possible.
    - Always cite your sources.
    """
    response = generate(
        model='4o-mini',
        system=system_prompt,
        query=f"""
                🧠 General Web Search Results:
                    {general_response}

                    📰 Local News Results:
                    {local_response}

                    💬 Social Media Results:
                    {social_media_response}
               """,
        temperature=0.2,
        lastk=3,
        session_id=SESSION,
        rag_usage=False
    )
    return response['response']

def unified_search_pipeline(
    query: str,
    room_id: str,
    user_name: str,
    search_fn,
    summarizer_fn,
    message_prefix: str = ""
) -> str:
    print(f"[INFO] unified_search_pipeline using {search_fn.__name__}")
    search_results = search_fn(query)
    if not search_results:
        print("[ERROR] No results found.")
        return []

    TOTAL_RESULTS = min(3, len(search_results))
    all_summaries = []
    idx = 0

    while len(all_summaries) < TOTAL_RESULTS:
        result = search_results[idx]
        url, title = result["url"], result["title"]
        content = fetch_main_article(url)

        if content == "ERROR":
            idx += 1
            continue

        formatted = format_source(query, url, title, content)
        summary = summarize_source(query, formatted)

        if summary == "ERROR":
            idx += 1
            continue

        all_summaries.append(summary)
        idx += 1

    #if message_prefix:
        #send_direct_message(message_prefix, room_id)

    print("[INFO] Response generated successfully!")
    return summarizer_fn(query, all_summaries)

def get_relevant_questions(content: str):
    GET_RELEVANT_QUESTIONS_PROMPT = """
    You are a helpful assistant for an AI Agent that helps user detect
    missinformation. You should generaterelevant follow-up questions based
    on some content. You will be given a summary combining results from possibly
    a general google search, a local search, and a social media search. Your goal
    is to anticipate what a curious user might want to know next.

    Generate 2 or 3 thoughtful follow-up questions that are directly related to
    the main topic.

    Strictly respond ONLY with a Python list of the questions you come up with,
    like ["[question1]", "questions2"].
    """
    response = generate(
        model="4o-mini",
        system=GET_RELEVANT_QUESTIONS_PROMPT,
        query=f"Here is the content {content}",
        temperature=0.3,
        lastk=1,
        session_id="get_relevan_questions_0",
        rag_usage=False,
    )
    questions = eval(response["response"].strip())  # Safe only if you trust the output
    assert isinstance(questions, list)
    print(f"[INFO] Generated questions: {questions}")
    return questions

def extract_url(text: str) -> str:
    match = re.search(r'https?://[^\s]+', text)
    if not match:
        match = re.search(r'http?://[^\s]+', text)
    return match.group(0) if match else None

def extract_post_id(url: str) -> str:
    """Extracts Reddit post ID from full reddit.com URL"""
    pattern = r"reddit\.com/r/[^/]+/comments/([a-z0-9]+)/"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError(f"Could not extract post ID from URL: {url}")

def get_reddit_comment_summaries_from_urls(urls: list[str], limit_comments: int = 20):
    """Takes a list of Reddit post URLs and returns comment summaries."""
    summaries = []

    for url in urls:
        try:
            post_id = extract_post_id(url)
            submission = reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)

            comments = [comment.body for comment in submission.comments[:limit_comments]]
            summaries.append({
                "title": submission.title,
                "url": submission.shortlink,
                "comments": comments
            })
        except Exception as e:
            print(f"[ERROR] Failed to process {url}: {e}")

    return summaries

def google_search_reddit(query: str, num_results: int = 10) -> list:
    """
    Performs a Google Custom Search API query and returns the top 'num_results' links.
    """
    cleaned_query = query.replace('"', '') 
                    
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": SEARCH_ENGINE_ID_REDDIT,
        "q": cleaned_query,
        "num": num_results
    }

    try:
        response = requests.get(search_url, params=params, timeout=10)

        response.raise_for_status()
        data = response.json()

        results = data.get("items", [])

        google_results_urls = []
        
        for item in results:
            url = item.get("link")
            google_results_urls.append(url)
            
        return google_results_urls

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    return []