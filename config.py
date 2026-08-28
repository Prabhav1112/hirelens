import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
ENABLE_VOICE = os.getenv("ENABLE_VOICE", "true").lower() == "true"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")

os.makedirs(OUTPUT_DIR, exist_ok=True)
