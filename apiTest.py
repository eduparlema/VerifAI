# FACT_CHECK_API_TOOL = "AIzaSyBs2Tg-Xf0f_bRNRtUSGvFkRNZePd_y680"
import json
import requests

with open('config.json', 'r') as file:
    config = json.load(file)


FACT_CHECK_API = config["googleFactCheckApiKey"]
query = "climate change"

url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

# Define parameters
params = {
    'query': query,
    'key': FACT_CHECK_API,
    'pageSize': 5,
    'languageCode' : 'en'
}

response = requests.get(url, params=params)

# Check status and print results
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
else:
    print(f"Error: {response.status_code}")
    print(response.text)