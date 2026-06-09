import os
import google.generativeai as genai
from dotenv import load_dotenv
import json

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("NO API KEY")
    exit()

genai.configure(api_key=api_key)

try:
    model_name = 'gemini-3.1-pro-preview'
    print(f"Testing model: {model_name}...")
    model = genai.GenerativeModel(model_name)
    
    charts_json = json.dumps([{"title": "Test Chart", "data": [10, 20, 30]}])
    
    prompt = f"""
    You are 'Quantum', the enterprise AI strategic analyst. 
    I have a chart with the following data: {charts_json}
    
    Your task: Analyze this specific chart and provide a 4-5 sentence deep-pulse strategic insight.
    Return ONLY a JSON object where the key is the title and the value is the analysis.
    """
    
    response = model.generate_content(prompt)
    print(f"RAW RESPONSE: {response.text}")
except Exception as e:
    print(f"FAILED: {e}")
