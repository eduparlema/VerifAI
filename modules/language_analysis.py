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
    # Should return yes if there is alarming, emotional, or manipulative language
    # cIf it is just a regular question or statement it should return no
    LANGUAGE_ANALYSIS_PROMPT = """You are a smart and friendly assistant that helps
    people understand the tone and language of messages shared on social media or messaging apps.
    Your task is ONLY to analyze the language, analyzing the actual content and
    its veracity is the responsibility of another agent.
    Many of these messages can be emotional, biased, or manipulative — even if
    they don't seem false at first. 
    Your job is to detemrine if this is the case and return "YES or "NO"
    Here are some examples


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