from modules.search_results import *
from modules.composer import *

def generate_response(user_input, username):
    results = search(user_input, username)

    final_sources = results["final_sources"]
    composer_input = []
    for source in final_sources:
        composer_input.append("".join(list(source.values())))

    return composer(user_input, "\n".join(composer_input), username)

if __name__ == "__main__":
    user_input = "Has the Paris agreement actually reduced global emissions?"    
    # user_input = "Is Erdogan a dictator?"

    current_query=""
    print("\nRespone from Composer:\n>>>>>")
    print(generate_response(user_input, "Erin123"))