from modules.search_results import *

def main(user_input, current_query):
    

    search_journey = []
    current_query = user_input
    thoughts = []
    steps_taken = 0
    max_steps = 5
    collected_results = []

    while steps_taken < max_steps:
        steps_taken += 1

        # 2. Perform search
        results = perform_search(user_input, current_query, "test_user")
        print(f"results: {results}")

        # 3. Evaluate results
        relevance = evaluate_relevance(results, user_input)
        print(f"relevance: {relevance}")
        diversity = evaluate_diversity(collected_results + results, user_input)
        print(f"diversity: {diversity}")
        # 4. Record the step
        search_journey.append({
            "query": current_query,
            "action": "search",
            "relevance": relevance,
            "diversity_so_far": diversity,
            "num_results": len(results),
            "results": results
        })

        collected_results.extend(results)

        # 5. Reason about what to do next
        if relevance > RELEVANCE_THRESHOLD and diversity > DIVERSITY_THRESHOLD:
            final_decision_reasoning = f"Confident answer obtained after {steps_taken} step(s)."
            break
        else:
            next_action = decide_next_action(collected_results, user_input)
            thoughts.append(next_action)
            print(f"NEXT ACTION: {next_action}")


if __name__ == "__main__":
    user_input = "Was there any credible evidence of widespread voter fraud in the 2020 U.S. presidential election?"
    current_query="voter fraud in the 2020 U.S. presidential election"

    main(user_input, current_query)

    