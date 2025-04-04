# FACT_CHECK_API_TOOL = "AIzaSyBs2Tg-Xf0f_bRNRtUSGvFkRNZePd_y680"
import json
import requests

with open('config.json', 'r') as file:
    config = json.load(file)


FACT_CHECK_API = config["googleFactCheckApiKey"]
#query = "climate change"
article = """
FACT FOCUS: Trump falsely claims babies can be seen to change ‘radically’ after vaccination

In an excerpt of a recent conversation between former President Donald Trump and independent presidential candidate Robert F. Kennedy Jr. posted online, Trump suggested vaccines given to children to protect them from disease are harmful. He also exaggerated the number of vaccines given to children and he falsely claimed they lead to sudden, visible changes. Neither campaign has responded to requests for comment.

TRUMP: “A vaccination that is like 38 different vaccines and it looks like it’s meant for a horse, not a, you know, 10-pound or 20-pound baby” and “then you see the baby all of a sudden starting to change radically. I’ve seen it too many times. And then you hear that it doesn’t have an impact, right?”

THE FACTS: There are no 38-disease shots. Babies or toddlers may get four or five vaccinations during a check-up to protect them against dangerous and deadly diseases. The American Academy of Pediatricians is adamant that a handful of vaccines does not overwhelm a healthy tot’s immune system. After all, babies’ immune systems are strong enough to handle the huge number of everyday germs they encounter.

Childhood vaccines train youngsters’ bodies to recognize and fight off viruses and bacteria they haven’t yet been exposed to -- diseases that tend to be especially dangerous at young ages. They’re approved for use only after rigorous testing for safety and effectiveness.

Then they get yet more scrutiny as each year, the Centers for Disease Control and Prevention and the pediatrics group review the childhood immunization schedule – which shots to give at which age.


Full protection generally requires more than one dose and delaying a shot can leave a child at risk of getting sick before they’re back on track.

Vaccines prevent an estimated 3.5 million to 5 million deaths every year, according to the World Health Organization, nearly eliminating many once-common diseases in regions where vaccines are easily accessible.

Common combination vaccines fight a few diseases in one jab – measles, mumps and rubella, the MMR shot, or diphtheria, tetanus and pertussis or whooping cough, called DTaP. Multiple vaccinations are given together only if that, too, has been proven safe, whether it’s separate shots in one visit or the three-in-one combo.
"""

query = ""

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