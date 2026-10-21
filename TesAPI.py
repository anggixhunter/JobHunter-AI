import os
from dotenv import load_dotenv
from groq import Groq
from google import genai
from jobspy import scrape_jobs

load_dotenv(dotenv_path="api_key.env")

GEMINI_MODEL = "gemini-3.5-flash-lite"

print("=== CEK STATUS API KEY ===\n")

try:
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=5
    )
    print("Groq API Key : MASIH BERFUNGSI (Aktif)")
except Exception as e:
    print(f"Groq API Key : MATI / ERROR ({e})")

try:
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    gemini_client.models.generate_content(model=GEMINI_MODEL, contents="ping")
    print(f"Gemini API Key: MASIH BERFUNGSI (Aktif, {GEMINI_MODEL})")
except Exception as e:
    print(f"Gemini API Key: MATI / ERROR ({e})")

try:
    df = scrape_jobs(site_name=["indeed"], search_term="test", results_wanted=1, country_indeed="indonesia", verbose=0)
    print(f"jobspy       : BERFUNGSI ({len(df)} baris)")
except Exception as e:
    print(f"jobspy       : ERROR ({e})")

print("\n=== SELESAI ===")
