from urllib.parse import urlparse
import os
import requests
from readability import Document
from bs4 import BeautifulSoup
from llmproxy import generate
from dotenv import load_dotenv
import re


RC_API = os.environ.get("RC_API")
RC_token = os.environ.get("RC_token")
RC_userId = os.environ.get("RC_userId")

ROCKETCHAT_AUTH = {
    "X-Auth-Token": RC_token,
    "X-User-Id": RC_userId,
}

load_dotenv()

GOOGLE_API_KEY=os.environ.get("googleSearchApiKey")
SEARCH_ENGINE_ID=os.environ.get("searchEngineId")
FACT_CHECK_API=os.environ.get("googleFactCheckApiKey")
FACT_CHECK_URL=os.environ.get("factCheckApiUrl")

print(GOOGLE_API_KEY)
print(SEARCH_ENGINE_ID)

SESSION = "VerifAI_Session_13"

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

def custom_google_search(query: str, num_results: int = 10) -> list:
    pass


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
    system_prompt = """
        You are a fact-focused news summarizer.

        🎯 Goal:
        Summarize a news article with a specific focus on the parts that are **most relevant to the user's topic or claim**. Your summary should be informative, clear, and focused — capturing important facts, context, and supporting details without unnecessary generalizations.

        📝 Input:
        You will receive:
        - A topic or claim from the user.
        - A news article, including its title and full text.

        ✅ DO:
        - Write a **detailed but concise** summary of the article, focusing only on content that relates to the user's topic or claim.
        - Include important **facts, data points, events, or explanations** that help the user understand the article’s relevance to the claim.
        - If there are any **quotes** relevant to the topic or claim, include them with the **speaker’s name** (e.g., "John Smith said, '...'").
        - Use the article’s original phrasing when appropriate to maintain fidelity.
        - Be accurate, objective, and free of speculation.

        ❌ DON'T:
        - Do NOT summarize unrelated parts of the article.
        - Do NOT judge or speculate on whether the claim is true or false.
        - Do NOT make inferences or assumptions beyond what's in the text.
        - Do NOT include commentary or interpretation.

        📦 Output Format:
        This article is about <topic>. It provides the following information relevant to the user's claim or curiosity: <summary with key facts and any relevant quotes>.
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
            system=system_prompt,
            query=query,
            temperature=0.2,
            lastk=10,
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

    system_prompt = """
        You are a fact-checking assistant helping users verify claims or learn more about current events. Assume that *you* conducted the research by reading multiple relevant news articles.

        🎯 Goal:
        Respond to the user's input — whether it's a claim or a general question — by using only the article summaries provided. 

        🧠 Instructions:
        1. If the input is a **claim**, decide whether it is:
        - Likely true
        - Likely not true
        - Partially true or misleading
        - Unverifiable with the current sources
        Begin your response clearly, e.g., "The claim that [...] is likely not true."

        2. If the input is a **general question**, explain the topic using the facts from the summaries.

        3. Use a natural, human tone. For example:
        - "I looked at several sources including [Title](URL), and here's what I found..."
        - "Based on these reports, it seems that..."

        4. Include **citations** using this format:
        *(Source: [Title](URL))*

        5. DO:
        - Be clear, concise, and neutral.
        - Use quotes or key facts from summaries when relevant.
        - Limit output to 3999 characters.

        6. DO NOT:
        - Introduce external knowledge or opinions.
        - Speculate beyond what's in the summaries.

        📦 Output Template:
        - Start with a verdict: "The claim that [...] is likely not true." (or true/partially true)
        - Follow up with reasoning: "I looked at the following sources..."
        - Explain key details or quotes that support the reasoning.
        - Include clickable citations.
        - End by offering to help further if needed.
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
        system=system_prompt,
        query=query,
        temperature=0.4,
        lastk=3,
        session_id=SESSION,
        rag_usage=False
    )

    return response["response"]

def extract_keywords(user_input: str):
    system_prompt = """
        You are a search assistant for a fact-checking system.

        Your task is to generate a concise, high-quality search query based on a claim,
        article, or user statement. The goal is to capture the core idea so it can be
        searched using the Google Fact Check Tools API.

        Guidelines:
        - Extract only the **essential keywords**: people, organizations, places, events, and topics.
        - **Do not** include generic terms like "claim", "news article", "report", "statement", or "rumor".
            Also, unless stated somewhere in the user input, do not include dates on the
            keywords.
        - Focus on the real-world entities or actions being mentioned (e.g., policies, laws, bans, replacements).
        - Use neutral, objective language — avoid emotionally charged or speculative terms.
        - Keep it short and search-friendly: ideally **5-10 words**.
        - Output **only the final search query**, without quotes, prefixes, or explanations.
    """

    response = generate(
        model="4o-mini",
        system=system_prompt,
        query=user_input,
        temperature=0.2,
        lastk=3,
        session_id="keyword_session",
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
    system_prompt = """
    You are a smart and friendly fact-checking assistant who helps users understand
    whether claims they've seen are true, false, biased, misleading, exagerated, etc.
    You are an objective judge, do NOT give any opinions and always refer to relevant
    content when providing claims.

    You are given:
    - A claim submitted by the user
    - Fact-check metadata (e.g. rating, review date, source)
    - Full article content scraped from reliable sources

    🎯 Your job:
    1. Determine if the claim is **True**, **False**,**Misleading**, etc based on the evidence.
    2. Respond with a clear, short, and **engaging** verdict in a friendly tone — like you're explaining something to a friend over coffee.
    3. Use **emojis** to add warmth and help users scan the message quickly.
    4. Pull in **useful details** or **direct quotes** from the source article to explain why the verdict is what it is.
    5. Let the user know if the information is **recent or outdated**.
    6. End with a list of **citations** for transparency.
    """


    response = generate(
    model="4o-mini",
    system=system_prompt,
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

def send_direct_message(message: str, room_id):
    # Post initial message to initiate a thread
    requests.post(RC_API, headers=ROCKETCHAT_AUTH, json={
        "roomId": room_id,
        "text": message,
    })

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
