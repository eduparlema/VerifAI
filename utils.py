from urllib.parse import urlparse
import os
import requests
from readability import Document
from bs4 import BeautifulSoup
from llmproxy import generate
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY=os.environ.get("1googleSearchApiKey")
SEARCH_ENGINE_ID=os.environ.get("2searchEngineId")

SESSION = "VerifAI_Session_4"

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

def format_source(user_input, url, domain, title, article_text):
    """
    Formats the claim and article text into a structured input for the LLM.
    """
    return {
        "Topic": user_input,
        "URL": url,
        "Domain": domain,
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
    
def summarize_article(user_input: str, sources: list) -> str:
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

    summaries = []

    num_sources = 0
    article_index = 0

    while num_sources < 5:

        source = sources[article_index]

        print("Source", source)
    
        title = source.get("Title", "unknown")
        text = source.get("Content", "")
        url = source.get("URL", "unknown")
        domain = source.get("domain", "unknown")

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
                print(f"[ERROR] No summary generated for {title}.")
                article_index += 1
                continue


            summaries.append({
                "title": title,
                "url": url,
                "domain": domain,
                "summary": article_summary
            })


            num_sources += 1
            article_index += 1
     

        except Exception as e:
            print(f"Error summarizing article '{title}': {e}")
            continue

    return summaries

def generate_fact_based_response(user_input: str, summaries: list) -> str:
    """
    Generate a fact-based answer to a user's question or claim by synthesizing
    information from article summaries, using citations with URLs.
    """

    system_prompt = """
    You are a fact-checking and reasoning assistant.

    🎯 Goal:
    Given a user question or claim and multiple article summaries, your task is to generate a fact-based, well-reasoned response using only the provided information.

    📌 Instructions:
    1. If the input is a **general question**, provide an informative and structured explanation using facts from the summaries.
    2. If it’s a **claim**, decide whether the claim is supported, refuted, or partially supported.
    3. Use facts from the summaries — **do not speculate** or add external knowledge.
    4. Use inline citations with both the article **title** and a **clickable link** in this format:
    *(Source: [Title](URL))*
    5. Keep your tone factual, clear, and neutral.

    📦 Output Format:
    - Start with a clear verdict (e.g., "The claim is partially supported based on current reporting...").
    - Assume that you found the sources on the topic and created the summaries. 
    - Support the reasoning with specific details and quotes from the summaries.
    - Include **citations with titles and URLs** for each source you reference.
    Example Citation:
    (Source: ["Erdogan's Power Consolidation"](https://example.com/article1))

    If there is no relevant information in the summaries, respond with a polite 
    message such as: "I couldn't find any relevant information to support or 
    refute the claim. Please check back later or try a different query. 
    These were some of the sources I looked at: [Title](URL). If you have a 
    source that you want me to check, please provide the URL. If you have any 
    other questions, feel free to ask."

    """

    formatted_summaries = "\n\n".join([
        f"- Title: {item['title']}\n  URL: {item['url']}\n  Domain: {item['domain']}\n  Summary: {item['summary']}"
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