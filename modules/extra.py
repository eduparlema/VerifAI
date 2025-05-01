
def smart_search(user_input: str, user_name):
    """
    Agentic Search Function:
    - Treats the search process as an evolving plan.
    - After each search, evaluates:
        - Relevance
        - Sufficiency
        - Diversity
    - Decides dynamically whether to:
        - Accept the results
        - Modify the query (paraphrase, localize, translate, reframe)
        - Gather complementary perspectives
    - Terminates when confident results are obtained or no meaningful improvements are possible.
    
    Output:
    {
        "final_sources": list of dicts (title, url, snippet, etc.),
        "search_journey": list of steps taken (each step = action, query, results),
    }
    """
    max_steps = 2
    collected_results = []
    search_journey = []
    steps_taken = 0
    feedback = dict()
    while steps_taken < max_steps:
        steps_taken += 1
        print(f"[smart_search] step {steps_taken}")

        # Choose params to perform google search
        chosen_params = choose_search_params_smart(feedback, user_input, user_name)
        print(f"Chosen parameters: {chosen_params}")
        
        # Perform search
        results = perform_search(user_input, user_name, chosen_params)
        

        # Evaluate results
        feedback = evaluate_search_results(user_input, chosen_params, results, user_name)
        print(f"Feedback received: {feedback}")
        # Save results
        collected_results.extend(results)
        search_journey.append(chosen_params)
    
    final_output = {
        "final_sources": collected_results,
        "search_journey": search_journey,
    }
    return final_output




    # while steps_taken < max_steps:
    #     steps_taken += 1
    #     print(f"[search] Step {steps_taken}")

    #     # Choose params to perform google search
    # chosen_params = choose_search_params(collected_results, current_query, user_input, user_name)
    #     print(f"chosen parameters: {chosen_params}")

    #     # 2. Perform search
    # results = perform_search(user_input, user_name, chosen_params)
    #     # 3. Evaluate results
    #     num_relevant_results += evaluate_relevance(results, user_input, user_name)
    #     diversity = evaluate_diversity(collected_results + results, user_input, user_name)
    #     print(f"Diversity score so far: {diversity}")

    #     # 4. Record the step
    #     search_journey.append({
    #         "query": current_query,
    #         "diversity_so_far": diversity,
    #         "num of relevant sources": len(collected_results),
    #         "num_results": len(results),
    #     })

    #     collected_results.extend(results)
    #     print(f"TOTAL RELEVANT: {len(collected_results)}")

    #     # 5. Reason about what to do next
    #     if num_relevant_results > NUM_RELEVAN_RESULTS_THRESHOLD and diversity > DIVERSITY_THRESHOLD:
    #         break

    #     sources_string = "\n\n".join(
    #         f"{src.get('title', 'No Title')} ({src.get('date', 'No Date')})\n{src.get('link', 'No URL')}\n{src.get('content', '')}"
    #         for src in collected_results
    #     )

        # text_upload(
        #         text=sources_string,
        #         session_id=user_name,
        #         strategy='fixed'
        #     )