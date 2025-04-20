# def general_search(input: str, room_id: str, user_name:str, num_results: int = 10):
#     TOTAL_RESULTS_DESIRED = 5
#     print("[INFO] general_search module activated!")
#     print(f"[general_search_module] room_id: {room_id}, user: {user_name}")
#     # Perform a Google search
#     search_results = google_search(input, num_results)
#     send_direct_message("✅ Got some results from Google — taking a closer look at your claim now! 🔍", room_id)
#     if not search_results:
#         print("[ERROR] No results found.")
#         return []

#     all_summaries = []
#     total_summary = 0
#     index_search_results = 0
    
#     while total_summary < TOTAL_RESULTS_DESIRED:

#         # Retrieve the next website in all search results.
#         result = search_results[index_search_results]

#         # Extact the url, title, and content of the website.
#         url = result["url"]
#         title = result["title"]
#         content = fetch_main_article(url)

#         # If fetching the content fails, skip this website.
#         if content == "ERROR":
#             index_search_results += 1
#             continue
#         # Else, Format the url, title, and content information properly.
#         else: 
#             formatted_result = format_source(input, url, title, content)
#             summary_result = summarize_source(input, formatted_result)

#             # If summarizing the content fails, skip this website.
#             if summary_result == "ERROR":
#                 index_search_results += 1
#                 continue

#             # Else, add the source to the all_summaries list.
#             else: 
#                 total_summary += 1
#                 index_search_results += 1

#                 all_summaries.append(summary_result)
#     send_direct_message("Generating a response...", room_id)
#     # Generate a response based on all summarized sources.
#     response = generate_fact_based_response(input, all_summaries)
#     if not response:
#         print("[ERROR] No response generated.")
#         return []
    
#     print("[INFO] Response generated successfully!")
#     return response



# def local_search(input: str, room_id: str, user_name:str, num_results: int = 10):
#     TOTAL_RESULTS_DESIRED = 5
    
#     print("[INFO] Local search module activated!")
#     # Perform a Google search
#     search_results = custom_google_search(input, num_results)
#     print(search_results)

#     # send_direct_message("Retrieved results from Google, evaluating the claim!", room_id)
    
#     if not search_results:
#         print("[ERROR] No results found.")
#         return []

#     all_summaries = []
#     total_summary = 0

#     index_search_results = 0

#     TOTAL_RESULTS_DESIRED = min(TOTAL_RESULTS_DESIRED, len(search_results))
    
#     while total_summary < TOTAL_RESULTS_DESIRED:

#         # Retrieve the next website in all search results.
#         result = search_results[index_search_results]

#         # Extact the url, title, and content of the website.
#         url = result["url"]
#         title = result["title"]
#         content = fetch_main_article(url)

#         # If fetching the content fails, skip this website.
#         if content == "ERROR":
#             index_search_results += 1
#             print('weijwije')
#             continue
#         # Else, Format the url, title, and content information properly.
#         else: 
#             formatted_result = format_source(input, url, title, content)
#             summary_result = summarize_source(input, formatted_result)

#             # If summarizing the content fails, skip this website.
#             if summary_result == "ERROR":
#                 index_search_results += 1
#                 continue

#             # Else, add the source to the all_summaries list.
#             else: 
#                 total_summary += 1
#                 index_search_results += 1

#                 all_summaries.append(summary_result)

#     # send_direct_message("Generating a response...", room_id)
 
#     # Generate a response based on all summarized sources.
#     response = generate_fact_based_response_custom(input, all_summaries)

     
#     if not response:
#         print("[ERROR] No response generated.")
#         return []
    
#     print("[INFO] Response generated successfully!")
#     return response