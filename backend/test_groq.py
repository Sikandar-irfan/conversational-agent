import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

print("API key loaded:", api_key is not None)
print("API key prefix:", api_key[:10] if api_key else None)

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)

print("\n=== AVAILABLE MODELS ===")

models = client.models.list()

for model in models.data:
    print(model.id)

print("\n=== TESTING LLAMA 3.3 ===")

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {
            "role": "user",
            "content": "Say hello"
        }
    ]
)

print(response.choices[0].message.content)