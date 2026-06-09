import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("NO API KEY")
    exit()

genai.configure(api_key=api_key)

try:
    # Test model name
    model_name = 'gemini-1.5-pro'
    print(f"Testing model: {model_name}...")
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("Say 'Gemini is online'")
    print(f"RESPONSE: {response.text}")
except Exception as e:
    print(f"FAILED: {e}")
