from modules.search_results import *
from modules.composer import *

def main(user_input, username):
    results = search(user_input, username)

    final_sources = results["final_sources"]
    composer_input = []
    for source in final_sources:
        composer_input.append("".join(list(source.values())))

    return composer(user_input, "\n".join(composer_input), username)

if __name__ == "__main__":
    # user_input = "Was there an election fraud in Bolivia in 2019?"    
    user_input = "Is Erdogan a dictator?"

    current_query=""

    print(main(user_input, "Erin123"))