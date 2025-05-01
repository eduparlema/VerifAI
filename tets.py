from transformers import pipeline

pipeline = pipeline("text-generation", model="meta-llama/Llama-2-7b-hf", device="cuda")
print(pipeline("The secret to baking a good cake is ", max_length=50))
