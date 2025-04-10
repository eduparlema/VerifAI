import json
from urllib.parse import urlparse
import requests
from newsapi import NewsApiClient
from bs4 import BeautifulSoup
from llmproxy import generate
import os
from readability import Document

SESSION = "GenericSession_31"

GOOGLE_API_KEY=os.environ.get("googleApiKey")
SEARCH_ENGINE_ID=os.environ.get("searchEngineId")  
NEWS_API_KEY=os.environ.get("newsApiKey")
print(f"search: {GOOGLE_API_KEY}")
print(f"search engine id: {SEARCH_ENGINE_ID}")
print(f"newsapi key {NEWS_API_KEY}")

newsapi = NewsApiClient(api_key=NEWS_API_KEY)

def get_newsapi_data(query, num_results=5):
  try:
    # /v2/everything
    all_articles = newsapi.get_everything(q=query,
                        sort_by='relevancy',
                        page=1)
    articles = all_articles['articles']

    newsapi_results = []

    if not all_articles['articles']:
      return []
    
    num_articles = min(num_results, len(articles))

    for article in articles[:num_articles]:
      url = article['url']
      title = article['title']
      source = article['source']['name']
      published_date = article['publishedAt']

      newsapi_results.append({
          "url": url,
          "title": title,
          "source": source,
          "published_date": published_date
      })

    return newsapi_results

  except Exception as e:
    print(f"Error fetching articles: {e}")
    return None

def extract_publish_date(pagemap):
    try:
        metatags = pagemap.get("metatags", [{}])
        for tag in metatags:
            for key in ["article:published_time", "og:published_time", "date"]:
                if key in tag:
                    return tag[key][:10]  # Return YYYY-MM-DD
    except Exception:
        pass
    return "unknown"

def google_search(query: str, num_results: int = 5) -> list:
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
      publish_date = extract_publish_date(item.get("pagemap", {}))
      google_results.append({
                  "url": url,
                  "title": title,
                  "source": domain,
                  "published_date": publish_date
              })
    
    return google_results

  except Exception as e:
    print(f"❌ Unexpected error: {e}")

  return []

def combine_sources(newsapi_results: list, google_results: list) -> list:
  combined_results = []
  for result in newsapi_results:
    combined_results.append(result)
  for result in google_results:
    combined_results.append(result)
  return combined_results


def filter_sources(
    user_claim: str,
    all_results: list,
    num_to_select: int = 5
):
    num_to_select = min(num_to_select, len(all_results))

    system_prompt = f"""
    You will be given:
    - A claim to fact-check.
    - A list of article and website titles.

    Instructions:
    1. Select the top {num_to_select} most relevant titles to investigate the claim.
    2. Use only the **title text** to decide.
    3. Output only the **indexes** (0-based, based on the full combined list: article_titles followed by website_titles), separated by commas.

    Format:
    index1, index2 , ..., indexN

    Do not include anything else.
    """
    all_titles = [item["title"] for item in all_results]   

    evidence_block = "\n".join(
        [f"{i}. {title}" for i, title in enumerate(all_titles)]
    )

    response = generate(
        model="4o-mini",
        system=system_prompt,
        query=f"""Claim: {user_claim}\n\nTitles:\n{evidence_block}""",
        temperature=0.4,
        lastk=3,
        session_id=SESSION,
        rag_usage=False
    )

    verdict = response["response"]
    print("verdict", verdict)
    indicies = [int(x.strip()) for x in verdict.split(",")]

    return indicies

def fetch_main_article(url: str, timeout: int = 10) -> str:
    try:
        response = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        })
        response.raise_for_status()
        html = response.text
    except requests.exceptions.RequestException as e:
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

def summarize_facts(indicies, all_results, user_claim):
    
    print("indicies, ", indicies)
    print("all_results", all_results)
    
    results = [all_results[i] for i in indicies]

    system_prompt = """
    You are a fact-checking assistant.

    Your task is to extract and organize factual information from a news article using a **strict format**, with a specific focus on summarizing content that is **most relevant to the provided claim or fact**.

    The user will provide:
    - A factual **claim** to investigate.
    - A news **article** with structured metadata: URL, title, published date, and full article text.

    🧠 Your goal is to:
    - Prioritize information from the article that is **relevant to evaluating the claim**.
    - Do NOT speculate on whether the claim is true or false — just identify and summarize factual content from the article that relates to it.
    - Do NOT summarize unrelated parts of the article.
    - Do NOT interpret, speculate, or infer.
    - Preserve the article’s original phrasing wherever possible.

    ⚠️ Output Instructions:
    - If any required field is missing, use "unknown".
    - Output **only valid JSON**. No markdown, no extra commentary, no preamble.

    📦 Required Output Format:

    {
      source: "<url provided by the user>",
      title: "<title provided by the user>",
      published_date: "<published date provided by the user>",
      summary: "An efficient but complete summary of the parts of the article relevant to the claim, preserving the original phrasing wherever possible.",
      verbatim_quotes: Import quotes  if exists in the article that are relevant to the claim."   
    }

    Wait for the user to provide input in the following format:

    ---
    Claim: <claim to fact-check>  
    URL: <article URL>  
    Title: <article title>  
    Published Date: <YYYY-MM-DD>  
    Article Text:  
    \"\"\"<full article text>\"\"\"
    ---
    """

    def format_claim_article_input(
    claim: str,
    url: str,
    title: str,
    published_date: str,
    article_text: str
    ) -> str:
        return f"""---
    Claim: {claim}  
    URL: {url}  
    Title: {title}  
    Published Date: {published_date}  
    Article Text:  
    \"\"\"{article_text}\"\"\"  
    ---"""

    summary_list = []

    for source in results:

      try: 

        url = source['url']
        title = source['title']
        published_date = source['published_date']
        main_article = fetch_main_article(url)

        if main_article != "ERROR":
          
          response = generate(
            model="4o-mini",
            system=system_prompt,
            query=format_claim_article_input(user_claim, url, title, published_date, main_article),
            temperature=0.4,
            lastk=3,
            session_id=SESSION,
            rag_usage=False
          )

          summary_list.append(response['response'])

      except Exception as e:
        print(f"Error in generating summary: {e}")
        continue

    return summary_list


def answer_claim(claim: str, summaries: list[str]) -> str:
    
    try: 

      # Combine the summaries into one block with indexing for traceability
      evidence_text = ""
      for i, summary_json in enumerate(summaries):
          summary_json = summary_json.replace("'", "").replace('"', '')
          evidence_text += f"Source {i+1}:\n{summary_json}\n\n"

      # print(evidence_text)

      system_prompt = """
        You are a fact-checking assistant.

        You will be given a factual claim and a list of structured article summaries in JSON format.

        Your task is to synthesize a natural language response that helps the user assess the validity of the claim based only on the summaries.

        ✅ Use only the information contained in the summaries and any verbatim quotes provided.  
        ❌ Do not speculate, invent, or infer from what is not present.  
        🧠 Your response should:
        - Clearly state whether the claim is supported, contradicted, or unclear.
        - Justify your conclusion by referencing relevant details or quotes.
        - Use a calm, objective tone suitable for fact-checking.
        - Cite resources and provide a list of sources at the end.

        Return a single, concise paragraph. Do not include bullet points or restate the data.
        """

      response = generate(
          model="4o-mini",
          system=system_prompt,
          query=f"""Claim: "{claim}"\n\nSummaries:\n\n{evidence_text}""",
          temperature=0.4,
          lastk=3,
          session_id=SESSION,
          rag_usage=False
        )
      
    except Exception as e:
       print(f"Error in generating response: {e}")


    return response['response']

   
def research(query: str):
  google_results = google_search(query)
  print("google search",google_results)
  newsapi_results = get_newsapi_data(query)
  print("news api", newsapi_results)
  all_results = combine_sources(newsapi_results, google_results)
  print("all_results", all_results)
  indicies = filter_sources(query, all_results)
  print("indicies", indicies)
  summaries = summarize_facts(indicies, all_results, query)
  print("summaries", summaries)
  answer = answer_claim(query, summaries)

  return answer


# if __name__ == "__main__":
#   research("World Cup 2026 location Turkey")

