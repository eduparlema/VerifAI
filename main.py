# FACT_CHECK_API_TOOL = "AIzaSyBs2Tg-Xf0f_bRNRtUSGvFkRNZePd_y680"
import json
from llmproxy import generate
import requests

with open('config.json', 'r') as file:
    config = json.load(file)

with open('article.txt', 'r') as file:
    article = file.read()


FACT_CHECK_API = config["googleFactCheckApiKey"]

system_prompt = """

  You are a search assistant for a fact-checking system.

  Given a news article, opinion piece, or report, generate one or two high-quality search queries that capture the core theme of the article. These queries will be used to retrieve relevant fact-checking resources from trusted databases.

  Guidelines:
  - The query should reflect the article’s main theme or central controversy.
  - Focus on the people, policies, events, or statistics mentioned in the article.
  - Remove any emotionally charged or biased language.
  - Use search-friendly keywords and keep it concise (5–12 words).
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

print(response['response'])


# query = response['response']
query = "trump 2024 election fraud"



# Define parameters
params = {
    'query': query,
    'key': FACT_CHECK_API,
    'pageSize': 5,
    'languageCode' : 'en'
}

URL = config["factCheckApiUrl"]

# Check status and print results
try: 
  response = requests.get(URL, params=params)
  response.raise_for_status()
except requests.exceptions.RequestException as e: 
  print(f"Error: {e}")
  print(response.text)

print(response.status_code)
if response.status_code == 200:
  data = response.json()
  # print('data', data)
  # print(data.get('claims'))
  claims = data.get('claims', [])
  for i, claim in enumerate(claims):
      print(f"\nClaim {i + 1}:")
      print(f"  Text: {claim.get('text')}")
      print(f"  Claimant: {claim.get('claimant')}")
      for review in claim.get('claimReview', []):
          print(f"  Reviewed by: {review.get('publisher', {}).get('name')}")
          print(f"  Rating: {review.get('textualRating')}")
          print(f"  URL: {review.get('url')}")