from llmproxy import generate
import json
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

SESSION = "GenericSession_15"

# Read proxy config from environment
end_point = os.environ.get("endPoint")
api_key = os.environ.get("apiKey")

FACT_CHECK_API = os.environ.get("googleFactCheckApiKey")
URL = os.environ.get("factCheckApiUrl")

with open('article.txt', 'r') as file:
    article = file.read()

def generate_response(user_input: str):
  # response = intent_detection(user_input).strip()

  print("✅ Fact-checkable claim detected. Proceeding with the pipeline...")
  
  keywords = extract_keywords(user_input)
  print(f"Keywords: {keywords}")
  fact_check_data = query_fact_check_api(keywords)
  
  # Check if we get something from Fact Checking API
  if fact_check_data and fact_check_data.get('claims'):
    context = prepare_fact_check_context(fact_check_data['claims'])
    verdict = generate_verdict(user_input, context)
    print("\n Final Verdict: \n")
    #print(verdict)
    return verdict
  else:
    print("No relevant fact checks found")
    #TODO: ERIN's part here
    return "No relevant fact checks found (TODO: ERIN)"

def intent_detection(user_input:str):
  intent_system_prompt = """
  You are a helpful and friendly assistant that helps users fact-check claims, headlines, and social media posts.

  Your job is to:
  1. Detect if the user's message contains a fact-checkable claim (something that could be verified or debunked using evidence).
  2. If the message **does** contain a fact-checkable claim, respond with exactly: `__FACT_CHECKABLE__`
  3. If the message **does not** contain a fact-checkable claim, respond with a helpful and friendly message that guides the user.
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

  Want to dig deeper? Ask me why something is false, check other sources, or even see what Reddit users are saying about it. I’ll keep each claim in a separate thread so it’s easy to follow the conversation.

  🔍 Go ahead—what claim should we check today?
  ---

  ONLY output either:
  - `__FACT_CHECKABLE__`  
  **OR**
  - a friendly message like the one above, appropriate for the input.
  """
  response = generate(
      model="4o-mini",
      system=intent_system_prompt,
      query=user_input,
      temperature=0.7,
      lastk=5,
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
      session_id=SESSION,
      rag_usage=False
  )

  return response["response"]

def query_fact_check_api(keywords: str):

  params = {
    'query': keywords,
    'key': FACT_CHECK_API,
    'pageSize': 5,
    'languageCode': 'en'
  }
  try:
    response = requests.get(URL, params=params)
    response.raise_for_status()
    return response.json()
  except requests.exceptions.RequestException as e:
    print(f"❌ Error querying Fact Check API: {e}")
    return None
  
# def display_fact_check_results(data):
#     claims = data.get('claims', [])
#     print(data)
#     if not claims:
#         print("🔍 No fact checks found for this query.")
#         return

#     for i, claim in enumerate(claims):
#         print(f"\n📌 Claim {i + 1}:")
#         print(f"   🗣️ Text: {claim.get('text')}")
#         print(f"   👤 Claimant: {claim.get('claimant')}")
#         print(f"   📅 Claim Date: {claim.get('claimDate')}")

#         for review in claim.get('claimReview', []):
#             print(f"   ✅ Reviewed by: {review.get('publisher', {}).get('name')}")
#             print(f"   📆 Review Date: {review.get('reviewDate')}")
#             print(f"   🧠 Rating: {review.get('textualRating')}")
#             print(f"   🔗 URL: {review.get('url')}")

def fetch_full_content(url: str, timeout: int = 10) -> str:
  try:
    response = requests.get(url, timeout=timeout, 
                            headers={
                               "User-Agent": 'Mozilla/5.0',
                               "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.google.com"
                               })
    response.raise_for_status()
    html = response.content
  except Exception as e:
    print(f"[ERROR] Error fetching {url}: {e}")
    return ""
  
  soup = BeautifulSoup(html, "html.parser")
  for unwanted in soup(["script", "style", "header", "footer", "nav", "aside"]):
      unwanted.extract()

  text = soup.get_text(separator=" ", strip=True)
  clean_text = " ".join(text.split())
  return clean_text

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
  1. Determine if the claim is **True**, **False**, or **Misleading** based on the evidence.
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
  

def main():
  while True:
    print("\n")
    user_input = input("You: ")
    generate_response(user_input)

if __name__ == "__main__":
    main()
