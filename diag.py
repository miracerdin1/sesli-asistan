from dotenv import load_dotenv
import os
import google.generativeai as genai
import time

print("--- DIAGNOSTIC START ---")
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("FATAL: API KEY NOT FOUND IN ENV")
    exit(1)
print(f"API Key Found: {api_key[:5]}...")

genai.configure(api_key=api_key)
model_name = 'gemini-2.5-flash'

try:
    print(f"Initializing Model: {model_name}")
    model = genai.GenerativeModel(model_name)
    print("Model Initialized")
    
    print("Testing Generation...")
    start_time = time.time()
    response = model.generate_content("Test message")
    end_time = time.time()
    
    print(f"Response Received in {end_time - start_time:.2f}s")
    print(f"Response: {response.text}")
    print("--- DIAGNOSTIC SUCCESS ---")

except Exception as e:
    print(f"--- DIAGNOSTIC FAILURE ---")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
