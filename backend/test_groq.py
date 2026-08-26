import sys
import os
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent.resolve()
load_dotenv(dotenv_path=BASE_DIR / ".env")
load_dotenv(dotenv_path=BASE_DIR.parent / ".env")

api_key = os.getenv("GROQ_API_KEY") or os.getenv("groq_API_KEY")

print("API key loaded:", api_key is not None)
print("API key prefix:", api_key[:10] if api_key else None)

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)

print("\n=== TESTING OPENAI/GPT-OSS-20B ON GROQ ===")

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role": "user",
            "content": "Say hello in Kannada"
        }
    ]
)

print(response.choices[0].message.content)