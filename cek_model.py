import os
from google import genai
from groq import Groq
from dotenv import load_dotenv

# Memuat variabel dari file .env
load_dotenv(dotenv_path="api_key.env")

# Masukkan API Key Anda di sini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY").strip()

print("="*50)
print("🔍 MENGECEK MODEL GEMINI YANG TERSEDIA:")
print("="*50)
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    # List model gemini
    for model in gemini_client.models.list():
        print(f"  - {model.name}")
except Exception as e:
    print(f"  ❌ Gagal cek Gemini: {e}")

print("\n" + "="*50)
print("🔍 MENGECEK MODEL GROQ YANG TERSEDIA:")
print("="*50)
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    models = groq_client.models.list()
    for model in models.data:
        print(f"  - {model.id}")
except Exception as e:
    print(f"  ❌ Gagal cek Groq: {e}")
print("="*50)