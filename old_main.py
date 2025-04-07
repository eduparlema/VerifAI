# FACT_CHECK_API_TOOL = "AIzaSyBs2Tg-Xf0f_bRNRtUSGvFkRNZePd_y680"
import json
from llmproxy import generate
import requests

with open('config.json', 'r') as file:
    config = json.load(file)

with open('article.txt', 'r') as file:
    article = file.read()

system_prompt = """

  You are a search assistant for a fact-checking system.

  Given a news article, opinion piece, report, or a simple fact/opinion,
  generate one high-quality search query that capture the core theme of the
  content. The keywords you output will be used to query the Google Fact Check
  Tools API.  

  Guidelines:
  - The query should reflect the article's main theme or central controversy.
  - Focus on the people, policies, events, or statistics mentioned in the article.
  - Remove any emotionally charged or biased language.
  - Use search-friendly keywords and keep it concise (5-12 words).
  - Return onlu one sentence.
"""
response = generate(
    model='4o-mini',
    system=system_prompt,
    query=f"Article:{article}",
    temperature=0.2,
    lastk=1,
    session_id="GenericSessionIDs1",
    rag_usage=False
)

print(f"Response from AI: {response['response']}")

FACT_CHECK_API = config["googleFactCheckApiKey"]
URL = config["factCheckApiUrl"]

query = response['response']

# Define parameters
params = {
    'query': query,
    'key': FACT_CHECK_API,
    'pageSize': 5,
    'languageCode' : 'en'
}

# Check status and print results
try: 
  response = requests.get(URL, params=params)
  response.raise_for_status()
except requests.exceptions.RequestException as e: 
  print(f"Error: {e}")
  print(response.text)

if response.status_code == 200:
  data = response.json()
  claims = data.get('claims', [])
  for i, claim in enumerate(claims):
      print(f"\nClaim {i + 1}:")
      print(f"  Text: {claim.get('text')}")
      print(f"  Claimant: {claim.get('claimant')}")
      for review in claim.get('claimReview', []):
          print(f"  Reviewed by: {review.get('publisher', {}).get('name')}")
          print(f"  Rating: {review.get('textualRating')}")
          print(f"  URL: {review.get('url')}")