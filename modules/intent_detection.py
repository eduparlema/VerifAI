from llmproxy import generate, SESSION
import os

INTENT_DETECTION_PROMPT = """
🤖 You are a helpful, friendly, and human-like assistant that helps detect and 
analyze misinformation, particularly in forwarded messages, viral social media 
posts, and public claims. You assist an AI fact-checking agent in determining 
the user's intent so that appropriate action can be taken.

Your task is to classify the user's input into one of the following types:

---

🟣 "misinformation_analysis":
Use this category for **any input involving a forwarded message, claim, or 
emotionally charged language** that should be analyzed for truthfulness and 
tone. It includes two subtypes:

  🟢 "fact_check":
  - Use this when the message contains a **claim about politics, health, safety, 
    policies, disasters, etc. that can be verified** using reliable external information.
  - Example: "The UN just declared war on Israel? Is that true?"
  - Example: "My aunt sent a message saying there will be a blackout in 3 days. Is this real?"
  - Example: "I saw a post saying vaccines contain microchips. Can you verify?"

  🟠 "bias_detect":
  - Use this when the input contains **highly emotional, fear-based, or 
    manipulative language** that may spread misinformation — even if it’s not 
    a verifiable claim.
  - Flag messages with exaggerated, conspiratorial, or accusatory tone.
  - Example: “I just got this from my cousin in ICE: Biden already signed a plan 
    to give papers to 20 million illegals and defund the police. MSM won't tell
    you because they’re covering it up. We’re being sold out. Forward this NOW 
    before it’s deleted. Our country is being taken from us while we sleep. God 
    help us.”

  If the message qualifies for both, respond with `"misinformation_analysis"` and **indicate subtype(s)** in your notes.

---

🔵 "follow_up_search":
Use this if the user is continuing a previous conversation or asking for elaboration without introducing new information to verify.
- Example: "Can you explain why people are panicking?"
- Example: "What happened after that law passed?"

---

🟡 "generic_response": Use this for:
- Common knowledge questions (e.g., "Who is the president of Germany?")
- Ambiguous topics needing clarification (e.g., "immigration")
- Greetings, small talk, or casual messages
- Off-topic queries unrelated to political or factual content

📌 Example input and bot behavior:
- Greeting:
  ➤ Input: "Hey how's it going?"
  ➤ Bot:
  🤖 Hey there! I'm your fact-checking assistant. 🗳️
  If you've seen a viral message, headline, or social media post and you're 
  wondering, "Is this actually true?" — I'm here to help you find out! 🔍
  You can send me: 🧾 A message or claim you want verified
  🌐 A link or screenshot
  🗣️ A forwarded WhatsApp text or tweet
  🔎 Go ahead — what would you like me to verify?

-Clarification request: 
  ➤ Input: "immigration"
  ➤ Bot: "Could you clarify what you would like to know about immigration? Are 
you asking about recent laws, statistics, or public reactions?"

- Off-topic input:  
  ➤ Input: "What's the best pizza place in New York?"  
  ➤ Bot: "I'm here to help verify suspicious claims, viral messages, and misinformation — especially those shared online or in forwarded texts. 🍕  
  For restaurant recommendations, a general search engine might be more helpful.  
  But if you’ve seen something circulating that feels off — I’m here to check it for you!"


---

Response Format by Type:
"misinformation_analysis" → Respond strictly with the keyword "fact_check".
"follow_up" → Respond strictly with the keyword "follow_up".
"generic_response" → Provide a full paragraph response.

Strictly follow this format. Do not add explanation unless instructed.
"""

def intent_detection(user_input, room_id, user_name):
    response = generate(
        model='4o-mini',
        system=INTENT_DETECTION_PROMPT,
        query=f"User input: {user_input}",
        temperature=0.3,
        lastk=3,
        session_id=f"{SESSION}-{user_name}",
        rag_usage=False
    )
    return response["response"]

import random

if __name__ == "__main__":
    test1 = """In 2014, they said ‘development’ – now they want to remove Hindu
            temples and legalize terrorism. Ask yourself who benefits when our 
            traditions are erased. Jai Hind 🙏🏼 Pass this on to 10 real patriots. 
            If you care about Bharat, don’t stay silent."""
    test2 = """: El fin del Corona virus con esta prevención alemana. Científicos 
            alemanes anunciaron, después de una serie de estudios, que el virus 
            Corona no solo se reproduce en los pulmones como el virus del SARS 
            en 2002, sino que también se propaga ampliamente en la garganta 
            durante la primera semana de infección. Los científicos sugirieron 
            al canciller alemán y al ministro de Salud que le pidan a la gente 
            que haga una tarea simple varias veces al día, que es hacer gárgaras 
            con una solución semicaliente de Abmonak. Durante mucho tiempo han 
            insistido en la necesidad de hacer esto, y ahora, después de los 
            resultados de los experimentos realizados por biólogos alemanes 
            sobre la multiplicación del virus Corona en la garganta, han 
            enfatizado una vez más la necesidad de hacer gárgaras con una 
            solución tibia de agua y sal. íficos alemanes aseguran al 
            Ministerio de Salud alemán: si todas las personas se aclaran la 
            garganta varias veces al día haciendo gárgaras con una solución 
            semi-caliente de agua salada, el virus se eliminará por completo 
            en toda Alemania en una semana. Los experimentos han demostrado que 
            al hacer gárgaras con una solución de agua y sal, constantemente 
            convertimos nuestra garganta en un ambiente completamente alcalino, 
            y este ambiente es el peor ambiente para el coronavirus, porque con 
            el agua salada, el pH de la boca cambia a alcalino.  pH, y si 
            hacemos gárgaras varias veces al día haciendo gárgaras con solución 
            salina casi caliente, no le estamos dando oportunidad al coronavirus 
            de multiplicarse. Por lo tanto, es necesario que todas las personas 
            hagan gárgaras con una solución salina semi-caliente varias veces 
            al día varias veces al día, especialmente por la mañana y antes de 
            salir de casa y después de regresar a casa, para no permitir que el 
            virus Corona se multiplique.  en el mismo período inicial. Pidamos 
            a todas las personas que apliquen estos importantes y sencillos 
            consejos de salud con compromiso A medida que este artículo se 
            vuelva viral, usted también estará en el círculo de quienes luchan 
            contra la propagación del coronavirus. Enviar a sus seres queridos"""
    # Small set of mixed test cases
    test_cases = [
        ("misinformation_analysis", test1),
        # ("follow_up", "What does that ruling mean for small businesses?"),
        ("generic_response", "Who is the President of Canada?"),
        ("generic_response", "voting rights"),
        ("generic_response", "hey there!"),
        ("misinformation_analysis", test2),
        ("generic_response", "Tell me a good movie to watch tonight")
    ]

    # Randomize order
    random.shuffle(test_cases)

    # Run tests
    for idx, (expected_category, user_input) in enumerate(test_cases, start=1):
        print(f"\n=== Test {idx} | Expected: {expected_category.upper()} ===")
        print(f"Input: {user_input}\n")
        room_id = "test_room"
        user_name = "test_user"
        response = intent_detection(user_input.strip(), room_id, user_name)
        print(f"Response: {response}")