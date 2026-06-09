import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    try:
        models = genai.list_models()
        print("Available models:")
        for m in models:
            print(f"- {m.name} (Supports: {m.supported_generation_methods})")
    except Exception as e:
        print(f"Error listing models: {e}")
else:
    print("API Key not found.")
