import requests
import os
import re
from dotenv import load_dotenv
from llmproxy import SESSION, generate
import praw

GOOGLE_API_KEY = os.environ.get("googleSearchApiKey")
GOOGLE_API_KEY_EDU = os.environ.get("googleSearchApiKeyEdu")
SEARCH_ENGINE_ID_REDDIT = os.environ.get("searchEngineIDReddit")
CLIENT_ID = os.environ.get("praw_client_id")
CLIENT_SECRET = os.environ.get("praw_client_secret")
USER_AGENT = "script:misinfo-bot:v1.0"

SOCIAL_SEARCH_PROMPT = """
    You are a smart and friendly assistant who helps users understand how people are reacting to a claim or topic on Reddit.

    You are given:
    - A user-submitted claim or topic
    - A list of Reddit post titles and their most relevant user comments

    
    🎯 Guidelines:  
    1. Identify and explain the main themes, sentiments, and trends across the comments.
        - Are people supportive, skeptical, angry, joking? 
        - Do the comments show disagreement or controversy?
        - Are there shifts in tone (e.g. early support → later backlash)?
    2. For every main theme that you identify, quote 1-2 representative comments
    (user direct quotes or short paraphrases).
    3. Write in a clear, warm, and concise tone, using emojis to improve readability. Keep the answer concise!
    4. End each post section with the **Reddit post link** so users can explore more.

    ✅ DO:
    - Keep the tone friendly and concise
    - Use emojis sparingly to enhance clarity and warmth
    - Keep it visually clean and easy to scan
    - Base your analysis only on the comments provided
    - If appropriate, feel free to include a conclusion section at the end followed
      by links to the discussions.

    ❌ DO NOT:
    - Use headings like "Representative Comments:"
    - Add line breaks between bullet points, paragraphs, or quotes
    - Break the structure shown above
    - Repeat the same idea in multiple themes
    - Inject personal opinions or commentary 
    """


def google_search_reddit(query: str, num_results: int = 10) -> list:
    """
    Performs a Google Custom Search API query and returns the top 'num_results' links.
    """
    cleaned_query = query.replace('"', '') 
                    
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY_EDU,
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


def extract_post_id(url: str) -> str:
    """Extracts Reddit post ID from full reddit.com URL"""
    pattern = r"reddit\.com/r/[^/]+/comments/([a-z0-9]+)/"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError(f"Could not extract post ID from URL: {url}")

def get_reddit_comment_summaries_from_urls(urls: list[str], limit_comments: int):
    """Takes a list of Reddit post URLs and returns comment summaries."""
    summaries = []

    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT
    )
    
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

def get_reddit_search_keywords(user_input: str):
    sys_prompt = """
    🎯 **Role**  
    You are a Reddit search assistant that helps a misinformation analysis system find useful public opinions and reactions from Reddit.

    ---

    🧠 **Your Task**  
    The user will give you a message — it may be:
    - a forwarded WhatsApp post
    - a piece of viral or emotional misinformation
    - a political claim or conspiracy theory
    - or a general question

    Your job is to extract a **concise, well-phrased search query** that can be used to look up relevant Reddit discussions on this topic.

    ---

    ✅ Your search query should:
    - Focus on the **core claim or topic** in the message
    - Be phrased in **natural Reddit language** (not overly formal)
    - Remove filler, hashtags, or non-informative parts
    - Be **neutral and direct** — not emotionally biased or inflammatory
    - Be a good fit for finding posts in Reddit titles or comment threads

    ---

    📌 **Output Format**  
    Return only the search query as a single line of text. No explanation. No punctuation at the end.
    """

    response = generate(
        model='4o-mini',
        system=sys_prompt,
        query=f"User input: {user_input}",
        temperature=0.1,
        lastk=0,
        session_id="reddit_keywords",
        rag_usage=False
    )

    if isinstance(response, dict) and "response" in response:
        return response["response"]
    else:
        print(f"ERROR [social_search] LLM response: {response}")
        return f"ERROR [social_search] LLM response: {response}"


def social_search(user_input: str, room_id: str, user_name:str, limit_posts: int=3, limit_comments: int=20):
    keywords = get_reddit_search_keywords(user_input)
    print(f"Reddit KEYWORDS: {keywords}")
    print("[INFO] social_search module activated!")
    reddit_ulrs = google_search_reddit(keywords)
    print(f"[INFO] These are the reddit urls: {reddit_ulrs}")
    summaries = get_reddit_comment_summaries_from_urls(reddit_ulrs[:limit_posts], limit_comments)
    print(f"[INFO] This are the summaries: {summaries}")

    response = generate(
        model="4o-mini",
        system=SOCIAL_SEARCH_PROMPT,
        query=f"Here is the content \n {summaries}",
        temperature=0.1,
        lastk=3,
        session_id=f"{SESSION}_{user_name}",
        rag_usage=False
    )
    print(f"[INFO] Social response: {response["response"]}")
    return response["response"]