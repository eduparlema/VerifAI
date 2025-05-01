from modules.search_results import *
from modules.composer import *
from modules.intent_detection import *
from modules.language_analysis import *
from llmproxy import retrieve, RAG_SESSION, text_upload
from collections import defaultdict

def generate_response(user_input, room_id, user_name):
    # Detect intention
    intent = intent_detection(user_input, room_id, user_name)
    print("intent", intent)

    # If generic_reponse: directly return
    if intent != "follow_up" and intent != "misinformation_analysis":
        print("in generic response")
        return intent

    # Define variables to keep track of content for the composer
    search_content = []
    lang_analysis = ""
    rag_content = []


    # If misinformation_analysis: Get the queries and proceed to search
    if intent == "misinformation_analysis":
        print("in misinformation_analysis")
        queries = eval(get_queries(user_input, room_id, user_name))
        
        content = []
        for query in queries:
            content = smart_search(query, user_name)
            search_content.extend(content["final_sources"])

        
        # Get language analysis
        lang_analysis = language_analysis(user_input, user_name)

    
    # If follow_up: Skip getting the queries and just proceed to search (if needed)
    elif intent == "follow_up":
        print("in follow up")
        # Check RAG
        rag_context = retrieve(
            query = f"Content: {user_input}",
            session_id=f"{RAG_SESSION}_{user_name}",
            rag_threshold = 0.8,
            rag_k = 3)
        
        rag_enough = rag_decide(user_input, rag_context)
        # If Rag not enough -> search needed.
        if rag_enough == "NO":
            content = search(user_input, user_name)
            search_content.extend(content["final_sources"])
        # If Rag enough -> send to composer
        elif rag_enough == "YES":
            rag_content.extend(rag_context)
        else:
            raise ValueError(f"Unexpected response from LLM: {rag_enough}")
            

    # Get composer_input together
    composer_input = {}
    composer_input["search_content"] = ""
    composer_input["rag_content"] = ""
    composer_input["language_analysis"] = ""

    if search_content:
        search_content_parsed = []
        for source in search_content:
            search_content_parsed.append("".join(list(source.values())))
        composer_input["search_content"] = "\n".join(search_content_parsed)

    if rag_content:
        composer_input["rag_content"] = "\n\n".join(rag_content)

    if lang_analysis:
        composer_input["language_analysis"] = lang_analysis

    return composer(user_input, composer_input, user_name)
    # Pass composer_input to generate response
    

    # results = search(user_input, username)

    # final_sources = results["final_sources"]
    # composer_input = []
    # for source in final_sources:
    #     composer_input.append("".join(list(source.values())))

    # return composer(user_input, "\n".join(composer_input), username)

def rag_decide(user_question: str, rag_context: str):
    RAG_DECIDE_PROMPT = """
    You are a verification agent inside a fact-checking system.

    Your job is to decide whether the given context (retrieved from trusted
    sources) contains enough reliable, relevant, and specific information to
    confidently answer the user's query.

    To return “YES,” the context must meet **all** of the following conditions:
    1. It is clearly related to the user's question — not vaguely or partially.
    2. It provides enough detail or factual content to support a meaningful answer.
    3. It comes from sources that would be considered trustworthy in context
        (e.g. news outlets, institutions, expert blogs, etc.).
    4. The information can be cited or paraphrased directly to support the
        response — not speculation or generalities.

    If any of these conditions are not met, return “NO”.

    Only return:
    - `YES` → if the LLM could confidently respond using this context and cite it
    - `NO` → if the LLM would struggle to respond accurately or credibly using this context alone

    Do not explain your answer. Do not include any formatting or notes.
    """
    response = generate(
        model='4o-mini',
        system=RAG_DECIDE_PROMPT,
        query=f"User question: {user_question}\nRag context: {rag_context}",
        lastk=0,
        session_id="rag_decider_0",
        rag_usage=False
    )

    if isinstance(response, dict) and "response" in response:
        return response["response"]
    else:
        print(f"ERRO [rag_decide] LLM reponse: {response}")
        return f"ERROR LLM Response: {response}"

if __name__ == "__main__":
    user_input = "Has the Paris agreement actually reduced global emissions?"    
    # user_input = "Is Erdogan a dictator?"

    # current_query=""
    # print("\nRespone from Composer:\n>>>>>")
    # print(generate_response(user_input, "Erin123"))
    content = """"You can say whatever you want, but MAS is the only party that
    gave real dignity to our people. Free school breakfast, gas subsidies, help
    for the countryside. Don’t fall for media lies paid by the elites in La Paz.
    Don’t forget what they took from us before Evo. 🇧🇴

    Send this to at least 15 friends before midnight. Bolivia must wake up. Don’t
    break this chain – the truth must be known."""
    # print(generate_response(content, "room123", "Erin123"))
    results = smart_search(user_input, "Erin123")