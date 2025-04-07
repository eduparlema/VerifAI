from llmproxy_local import generate
import json
import requests

SESSION = "GenericSession_3"

with open('config.json', 'r') as file:
    config = json.load(file)

with open('article.txt', 'r') as file:
    article = file.read()

def generate_response(user_input: str):
  response = intent_detection(user_input).strip()

  if response == "__FACT_CHECKABLE__":
      print("✅ Fact-checkable claim detected. Proceeding with the pipeline...")
      
      keywords = extract_keywords(user_input)
      print(f"Keywords: {keywords}")
      fact_check_data = query_fact_check_api(keywords)
      if fact_check_data:
          display_fact_check_results(fact_check_data)
  else:
      print(response)

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
  FACT_CHECK_API = config["googleFactCheckApiKey"]
  URL = config["factCheckApiUrl"]

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
  
def display_fact_check_results(data):
    claims = data.get('claims', [])
    if not claims:
        print("🔍 No fact checks found for this query.")
        return

    for i, claim in enumerate(claims):
        print(f"\n📌 Claim {i + 1}:")
        print(f"   🗣️ Text: {claim.get('text')}")
        print(f"   👤 Claimant: {claim.get('claimant')}")
        print(f"   📅 Claim Date: {claim.get('claimDate')}")

        for review in claim.get('claimReview', []):
            print(f"   ✅ Reviewed by: {review.get('publisher', {}).get('name')}")
            print(f"   📆 Review Date: {review.get('reviewDate')}")
            print(f"   🧠 Rating: {review.get('textualRating')}")
            print(f"   🔗 URL: {review.get('url')}")

def main():
  while True:
      user_input = input("You: ")
      generate_response(user_input)

if __name__ == "__main__":
    main()
