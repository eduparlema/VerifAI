from llmproxy import generate, SESSION



def composer(user_query: str, search_content: str, username: str):
    COMPOSER_PROMPT = f"""
    🎯 Role:
    You are a neutral, articulate assistant skilled in synthesizing information from
    multiple sources to create a structured debate.

    🧠 Task:
    Given a **user query or topic** and a set of **news articles**, your goal is to 
    write a well-reasoned, multi-perspective analysis that:

    1. **Presents a structured debate** covering the main angles related to the topic.
    2. **Considers contrasting perspectives** — such as government vs. opposition, 
    expert vs. public, local vs. international, optimistic vs. critical, etc.
    3. **Uses evidence** from the articles to support each side's arguments.
    4. **Cites sources** clearly using inline citations in this format: *(Source: [Title](URL))*

    📌 Instructions:
    - Begin with a **brief introduction** to the issue.
    - Present each **distinct perspective in its own paragraph**, labeling them clearly if appropriate.
    - Include **quotes, facts, and attributions** from the articles where helpful.
    - Avoid speculation — only use the provided material.
    - Maintain a **clear, balanced, and natural tone**, like a skilled journalist or 
    analyst summarizing a panel discussion.

    ---

    📝 Format Example (shortened):

    **Topic:** Government Response to the 2023 Earthquake in Turkey


    The Turkish government's handling of the 2023 earthquake sparked debate within 
    the country and abroad. While officials cited improvements in logistical 
    response and resource mobilization, critics pointed to delays in rural aid 
    and systemic issues in infrastructure oversight.


    **Government Perspective:** Officials emphasized the scale of the disaster and 
    their rapid mobilization of resources, citing improvements since previous 
    disasters *(Source: [Daily Sabah](https://example.com))*.

    **Public & Opposition Response:** Critics argued that the government failed to 
    enforce building codes and was slow to deliver aid to rural areas 
    *(Source: [BBC News](https://example.com))*. Opposition leaders described the 
    response as “delayed and disorganized.”

    **International Viewpoints:** Some international agencies praised logistical 
    coordination, while others highlighted gaps in transparency and coordination 
    *(Source: [Al Jazeera](https://example.com))*.

    ---

    🧾 Inputs:
    - **User Topic or Claim:** "{user_query}"
    - **Articles:** Each article contains a title, full text, and URL.

    Now write the structured debate response.
    """
    response = generate(
        model='4o-mini',
        system=COMPOSER_PROMPT,
        query=f"User input: {user_query}\nSearch content: {search_content}",
        temperature=0,
        lastk=5,
        session_id=f"{SESSION}_{username}",
        rag_usage=False,
    )

    return response["response"]
    
