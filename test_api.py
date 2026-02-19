import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("API KEY NOT FOUND")
    exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

try:
    response = model.generate_content("Merhaba, nasılsın?")
    print("RESPONSE:", response.text)
except Exception as e:
    print("ERROR:", e)
