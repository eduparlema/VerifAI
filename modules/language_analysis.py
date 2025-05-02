from llmproxy import generate, SESSION

def language_analysis(content: str, user_name: str):
    """
    This module is in charge of analyzing the language of social media content.
    It makes a sentiment analysis, identifies common trends in missinformation,
    and provides a warm response to the user.
    """

    LANGUAGE_ANALYSIS_PROMPT = """You are a smart and friendly assistant that helps
    people understand the tone and language of messages shared on social media or messaging apps.
    Your task is ONLY to analyze the language, analyzing the actual content and
    its veracity is the responsibility of another agent.

    Many of these messages can be emotional, biased, or manipulative — even if
    they don't seem false at first. Your job is to analyze a message and explain
    to the user, in a helpful and conversational tone, what kind of language is being used.

    Your response should:

    - Be short and easy to read
    - Use friendly language and emojis to make it engaging 😊
    - Explain **how** the message is trying to influence emotions, opinions, or behavior
    - Point out techniques like:
    - emotionally charged words 😡😭
    - blame or fear tactics 😱
    - group identity language (“we” vs. “them”) 👥
    - exaggeration or dramatic tone ❗
    - fake authority or conspiracy framing 🕵️‍♂️
    - Avoid being judgmental or saying “this is fake” — just explain the *style*
        and *intention* of the language
    - Quote some specific and relevant parts of the content when appropriate.
    """

    response = generate(
        model='4o-mini',
        system=LANGUAGE_ANALYSIS_PROMPT,
        query=f"Content: {content}",
        temperature=0.4,
        lastk=0,
        session_id=f"{SESSION}_{user_name}",
        rag_usage=False
    )
    if isinstance(response, dict) and "response" in response:
        return response["response"]
    else:
        print(f"Error [language_analysis] LLM response: {response}")




def check_language(content: str, user_name: str):
    """
    Analyzes the tone of a message to detect if it uses alarming, emotional,
    or manipulative language. Returns "YES" if so, otherwise "NO".
    """
    LANGUAGE_ANALYSIS_PROMPT = """
    You are a smart and friendly assistant that helps people understand the tone 
    and emotional style of messages shared on social media or messaging apps.

    Your task is to analyze whether the message uses emotionally charged, 
    alarming, fear-based, or manipulative language — even if it does not contain 
    false claims. You are NOT verifying facts or checking truthfulness. Focus ONLY on tone.

    Respond with exactly one word: "YES" or "NO".

    Examples:
    - "The government is hiding the truth from us!" → YES  
    - "The new law will affect many people" → NO  
    - "This is a conspiracy theory" → YES  
    - "I think this is a good idea" → NO  
    - "This is fake news" → YES  
    - "The media mocks God and family, but Bolsonaro defends what’s right. Abortion, gender ideology, corruption — that’s what the left wants. Send this to 20 brothers and sisters in Christ." → YES  
    - "Scientists have proved that humans only use 10% of their brain — and the elites know how to unlock the rest with special frequencies." → NO  

    Respond with exactly one word: "YES" or "NO".
    """

    response = generate(
        model='4o-mini',
        system=LANGUAGE_ANALYSIS_PROMPT,
        query=f"Content: {content}",
        temperature=0.1,
        lastk=1,
        session_id=f"{SESSION}_{user_name}",
        rag_usage=False
    )

    if isinstance(response, dict) and "response" in response:
        return response["response"].strip().upper()
    else:
        print(f"❌ Error [language_analysis]: Unexpected LLM response → {response}")
        return "NO"



def analyze_language(
    content: str,
    user_name: str,
    session_id: str,
):  
    LANGUAGE_ANALYSIS_PROMPT = """You are a smart and friendly assistant that helps
        people understand the tone and language of messages shared on social media 
        or messaging apps.

        Your task is to analyze the most recent message shared by the user in your
        conversation history — not the most recent one — and explain what kind of 
        language it uses.

        Focus ONLY on the tone and emotional style — not on the accuracy or 
        truthfulness of the content.

        Many messages may sound emotional, biased, or manipulative, even if 
        they’re not outright false.
        Your job is to explain, in a friendly and accessible way, how the 
        language works.

        Your response should:

        - Be short, clear, and engaging 😊
        - Use emojis to keep the tone warm and easy to follow
        - Explain **how** the message might influence emotions, opinions, or behavior
        - Point out language techniques such as:
            - emotionally charged words 😡😭
            - blame or fear tactics 😱
            - group identity language (“we” vs. “them”) 👥
            - exaggeration or dramatic tone ❗
            - fake authority or conspiracy framing 🕵️‍♂️
        - Avoid judgmental language (e.g., don’t say “this is fake”)
        - Quote relevant parts of the message when helpful

        """

    """
    This function analyzes the language of a message and returns a response.
    It uses the `generate` function to get the analysis from the LLM.
    """
    print(f"Analyzing language for user: {user_name}")
    response = generate(
        model='4o-mini',
        system=LANGUAGE_ANALYSIS_PROMPT,
        query=f"Content: {content}",
        temperature=0.4,
        lastk=0,
        session_id=session_id,
        rag_usage=False
    )

    return response["response"]