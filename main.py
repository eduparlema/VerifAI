from modules.search_results import *
from modules.composer import *
from modules.intent_detection import *
from modules.language_analysis import *
from llmproxy import retrieve, RAG_SESSION, text_upload

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
        queries = eval(get_queries(user_input, room_id, user_name))
        
        content = []
        for query in queries:
            content = search(query, user_name)
            search_content.extend(content["final_sources"])

        
        # Get language analysis
        lang_analysis = language_analysis(user_input, user_name)

    
    # If follow_up: Skip getting the queries and just proceed to search (if needed)
    elif intent == "follow_up":
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

    if search_content:
        search_content_parsed = []
        for source in search_content:
            search_content_parsed.append("".join(list(source.values())))
        composer_input["search_content"] = "\n".join(search_content_parsed)

    if rag_content:
        composer_input["rag_content"] = "\n\n".join(rag_content)

    if lang_analysis:
        composer_input["language_analysis"] = lang_analysis


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
    content = """Esto ya no es crisis, es abuso institucionalizado!

El Ministerio de Salud sigue mirando hacia otro lado mientras la profesión médica en Bolivia se convierte en una de las más maltratadas y peor pagadas.

Cada año más de 5.000 médicos generales egresan… ¿para qué?
No hay fuentes de trabajo, no hay planificación, no hay respeto.
Mientras tanto, siguen abriendo universidades como si fueran tiendas de barrio, generando una saturación brutal y condenando a generaciones enteras al desempleo o al subempleo.

Y lo peor:
Los contratos que deberían ser para médicos generales están siendo entregados a especialistas que no tienen dónde ejercer su verdadera función.
¿El resultado?
Especialistas frustrados, médicos generales desplazados, servicios mal organizados y pacientes mal atendidos.

Nos faltan otorrinos, oncólogos, reumatólogos, endocrinólogos, neumólogos, y más.
Pero los cupos de residencia siguen atascados en las mismas cuatro especialidades básicas, como si estuviéramos atrapados en un loop sin sentido: pediatría, medicina interna, ginecología y cirugía general.

¿Quién decide esto?
Hospitales que piensan en lo que les conviene, no en lo que necesita el país.
¿Dónde están el Ministerio, el Colegio Médico, las sociedades científicas?
Callados. Cómplices.

Hoy en Bolivia, cuesta más hacerse las uñas acrílicas que una consulta médica.
Y eso no es casualidad: es el reflejo del desprecio sistemático hacia nuestra labor.
Ya debería existir un ARANCEL MÉDICO NACIONAL obligatorio, para frenar esta denigración, para exigir respeto, y para dignificar esta profesión que lo da todo y recibe migajas.

¡Basta ya!
Exigimos una reestructuración total del sistema de salud,
Una distribución de especialidades basada en las verdaderas necesidades del país,
Y un freno al uso político y económico de nuestra vocación."""

    qs = get_queries(content, "room1", "erin1")
    q1 = eval(qs.strip())[0]
    print(qs)
    print(q1)