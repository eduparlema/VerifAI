from llmproxy import generate

system_prompt = """
You are an assistant that detects whether a user message contains a fact-checkable claim.
You must respond with only one word: "yes" or "no".

A fact-checkable claim is a statement about the world that can be verified or debunked using evidence.
Examples include news headlines, political statements, or misinformation.

DO NOT include any explanation or extra text. ONLY reply with "yes" or "no".
"""

# Friendly intro message
friendly_intro = """🤖 Hey there! I’m your conversational fact-checking assistant.
If you’ve seen a claim, news article, or social media post and you’re wondering,
“Is this actually true?” — I’ve got you.

You can send me:
🧾 A statement you want checked
🌐 A link to a news article
🗣️ A quote or screenshot from social media

Want to dig deeper? Ask me why something is false, check other sources, or even see what Reddit users are saying about it. I’ll keep each claim in a separate thread so it’s easy to follow the conversation.

🔍 Go ahead—what claim should we check today?
"""

def is_fact_checkable(user_input: str) -> bool:
    response = generate(
        model="gpt-4",  # or your preferred model
        system=system_prompt,
        query=user_input,
        temperature=0.0
    )

    if isinstance(response, dict) and 'response' in response:
        reply = response['response'].strip().lower()
        return reply == "yes"
    return False

def main():
    user_input = input("You: ")

    if is_fact_checkable(user_input):
        print("✅ Fact-checkable claim detected. Proceeding with the pipeline...")
        # TODO: Continue with Part 3
    else:
        print(friendly_intro)

if __name__ == "__main__":
    main()
