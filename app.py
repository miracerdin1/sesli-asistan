import os
import subprocess
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from dotenv import load_dotenv
import pyautogui
import pyperclip
import traceback
import time
import difflib

load_dotenv()

app = Flask(__name__)

# Configure Gemini API
API_KEY = os.getenv("GEMINI_API_KEY")
model = None

if API_KEY:
    genai.configure(api_key=API_KEY)
    # Trying to pick a model, will handle errors during generation
    model_name = 'gemini-2.5-flash'
    try:
        model = genai.GenerativeModel(model_name)
        print(f"SUCCESS: Model {model_name} configured.")
    except Exception as e:
        print(f"ERROR: Failed to configure model {model_name}: {e}")
        model = None
else:
    print("WARNING: GEMINI_API_KEY not found. Using local fallback mode.")


# Helper function to find programs
# Helper function to find programs
def find_application(app_name):
    app_name = app_name.lower()
    
    # Common Start Menu locations
    paths = [
        os.path.join(os.environ['PROGRAMDATA'], r'Microsoft\Windows\Start Menu\Programs'),
        os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs')
    ]
    
    # Cache known apps {name: path}
    known_apps = {}
    
    for path in paths:
        if not os.path.exists(path): continue
        
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".lnk") or file.endswith(".exe"):
                    file_name = file.lower().replace(".lnk", "").replace(".exe", "")
                    keys = [file_name, file_name.replace(" ", "")]
                    for key in keys:
                        # Store full path for this name
                        if key not in known_apps:
                            known_apps[key] = os.path.join(root, file)

    # 1. Exact Match
    if app_name in known_apps:
        return known_apps[app_name]
        
    # 2. Simple Contains
    for name, path in known_apps.items():
        if app_name in name:
            return path
            
    # 3. Fuzzy Match (The "Smart" part)
    # Get closest match with at least 60% similarity
    matches = difflib.get_close_matches(app_name, known_apps.keys(), n=1, cutoff=0.6)
    if matches:
        print(f"Fuzzy match found: '{app_name}' -> '{matches[0]}'")
        return known_apps[matches[0]]
                            
    return None

def local_fallback(text):
    text = text.lower()
    if "nasılsın" in text:
        return "İyiyim, teşekkürler! Sen nasılsın?", None
    elif "merhaba" in text:
        return "Merhaba! Sana nasıl yardımcı olabilirim?", None
    # Dictation fallback
    elif text.startswith("yaz ") or text.startswith("şunu yaz "):
        # Extract text to write
        if text.startswith("yaz "):
            text_to_write = text[4:].strip()
        else:
            text_to_write = text[9:].strip()
        return f"'{text_to_write}' yazılıyor.", f"YAZ:{text_to_write}"
    else:
        return "Bunu tam anlayamadım ama senin için öğrenmeye çalışıyorum.", None




SYSTEM_PROMPT = """
Sen gelişmiş bir bilgisayar asistanısın. Kullanıcının niyetini anla.
Eğer kullanıcı bir program açmak istiyorsa, programın adını net bir şekilde belirle ve şu formatta cevap ver:
[KOMUT:AC:Program Adı] -> Örnek: [KOMUT:AC:Google Chrome], [KOMUT:AC:Adobe Acrobat], [KOMUT:AC:Word]

Özel durumlar:
[KOMUT:CHROME_YENI_SEKME] -> Chrome'da yeni sekme açmak için
[KOMUT:GOOLGE_ARA:arama_terimi] -> Google'da arama yapmak için
[KOMUT:YOUTUBE] -> Youtube'u açmak için
[KOMUT:YAZ:yazılacak_metin] -> Ekrana yazı yazdırmak için (Örnek: [KOMUT:YAZ:Merhaba dünya])

DİKKAT: "Hesap makinesi", "Not defteri" gibi sistem araçları için de [KOMUT:AC:Hesap Makinesi] formatını kullan, ben onları bulurum.

Eğer kullanıcı sohbet ediyorsa normal cevap ver. Cevabın kısa ve öz olsun.
"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
@app.route('/process', methods=['POST'])
def process():
    global model
    data = request.json
    user_input = data.get('text')

    if not user_input:
        return jsonify({'error': 'No input provided'}), 400

    text_response = ""
    command = None
    
    # --- Rule-Based Processing (bypass LLM for speed and quota) ---
    user_input_lower = user_input.lower()
    print(f"🔍 Komut Analiz Ediliyor: '{user_input}'")
    
    # 1. Dictation (YAZ)
    if user_input_lower.startswith("yaz ") or user_input_lower.startswith("şunu yaz ") or user_input_lower.startswith("yaz:"):
        text_to_write = ""
        if user_input_lower.startswith("yaz:"):
             text_to_write = user_input[4:].strip()
        elif user_input_lower.startswith("yaz "):
             text_to_write = user_input[4:].strip()
        else:
             text_to_write = user_input[9:].strip()
        
        if not text_to_write:
            return jsonify({'response': "Ne yazmamı istediğinizi söylemediniz.", 'command': None})
             
        try:
            import time
            time.sleep(0.5) # Wait a bit for focus
            pyperclip.copy(text_to_write)
            pyautogui.hotkey('ctrl', 'v')
            text_response = "Yazıldı."
            command = "WRITE"
            return jsonify({'response': text_response, 'command': command})
        except Exception as e:
            print(f"Write error: {e}")
            with open("error.log", "a") as f:
                f.write(f"Write Error: {e}\n")
                traceback.print_exc(file=f)
            text_response = "Yazma işlemi başarısız oldu."
            return jsonify({'response': text_response, 'command': command})

    # 2. Open App (AC) - Simple variations
    if "aç" in user_input_lower:
        # Simple extraction logic tailored for Turkish "X'i aç", "Y'yi aç"
        potential_app = user_input_lower.replace(" aç", "").replace("'i", "").replace("'ı", "").replace("'u", "").replace("'ü", "").replace("'ni", "").replace("'nı", "").replace("'nu", "").replace("'nü", "").strip()
        
        # Manual mappings for common Turkish names to Exe names
        if "not defter" in potential_app or potential_app == "notepad":
            subprocess.Popen(['notepad.exe'])
            text_response = "Not defteri açılıyor."
            command = "OPEN:NOTEPAD"
            return jsonify({'response': text_response, 'command': command})
            
        if "hesap makine" in potential_app or "kalkülatör" in potential_app:
            subprocess.Popen(['calc.exe'])
            text_response = "Hesap makinesi açılıyor."
            command = "OPEN:CALC"
            return jsonify({'response': text_response, 'command': command})

        if "chrome" in potential_app or "google" in potential_app:
            subprocess.Popen(['start', 'chrome'], shell=True)
            text_response = "Google Chrome açılıyor."
            command = "OPEN:CHROME"
            return jsonify({'response': text_response, 'command': command})
        
        # Try to find app locally if manual mapping failed
        found_path = find_application(potential_app)
        if found_path:
             subprocess.Popen(['start', '', found_path], shell=True)
             text_response = f"{potential_app} başlatılıyor..."
             command = f"OPEN:{potential_app}"
             return jsonify({'response': text_response, 'command': command})

    # --- LLM Processing with Fallback ---
    try:
        print(f"🤖 Yapay Zeka Devrede: '{user_input}'")
        model_name = 'gemini-2.5-flash'
        if not model:
            # Try to initialize if not already done (e.g. if key was added later)
            if API_KEY:
                 genai.configure(api_key=API_KEY)
                 model = genai.GenerativeModel(model_name)

        if model:
            full_prompt = f"{SYSTEM_PROMPT}\n\nKullanıcı: {user_input}\nAsistan:"
            response = model.generate_content(full_prompt)
            text_response = response.text.strip()
            
            import re
            match = re.search(r'\[KOMUT:(.*?)\]', text_response)
            if match:
                command_raw = match.group(1)
                
                if command_raw.startswith("AC:"):
                    app_name = command_raw.split(":", 1)[1].strip()
                    app_path = find_application(app_name)
                    
                    if app_path:
                        subprocess.Popen(['start', '', app_path], shell=True)
                        text_response = f"{app_name} başlatılıyor..."
                        command = f"OPEN:{app_name}"
                    else:
                        text_response = f"Bilgisayarınızda '{app_name}' adında bir program bulamadım."
                        command = "NOT_FOUND"
                            
                elif command_raw.startswith("YAZ:"):
                    text_to_write = command_raw.split(":", 1)[1]
                    try:
                        import time
                        time.sleep(0.5)
                        pyperclip.copy(text_to_write)
                        pyautogui.hotkey('ctrl', 'v')
                        text_response = "Yazıldı."
                        command = "WRITE"
                    except Exception as e:
                        print(f"Write error: {e}")
                        text_response = "Yazma işlemi başarısız oldu."

                elif command_raw == "CHROME_YENI_SEKME":
                    subprocess.Popen(['start', 'chrome', 'newtab'], shell=True)
                    command = "NEW_TAB"
                elif command_raw == "YOUTUBE":
                    subprocess.Popen(['start', 'chrome', 'https://www.youtube.com'], shell=True)
                    command = "YOUTUBE"
                elif command_raw.startswith("GOOGLE_ARA:"):
                    query = command_raw.split(":", 1)[1]
                    subprocess.Popen(['start', 'chrome', f'https://www.google.com/search?q={query}'], shell=True)
                    command = "SEARCH"
                    
        else:
             raise Exception("Model not initialized")

    except Exception as e:
        print(f"LLM Error: {e}")
        # Log detailed traceback
        try:
             with open("error.log", "a") as f:
                 f.write(f"\n--- LLM Error at {time.ctime()} ---\n")
                 f.write(f"User Input: {user_input}\n")
                 f.write(f"Error: {e}\n")
                 traceback.print_exc(file=f)
        except:
             pass 

        # FALLBACK RESPONSE when LLM fails (e.g. Quota Exceeded)
        text_response, cmd = local_fallback(user_input)
        command = cmd
        if not text_response:
             text_response = "Şu an bağlantı yoğunluğu nedeniyle tam cevap veremiyorum, ama 'yaz', 'aç' gibi komutları kullanabilirsiniz."

    except Exception as e:
        print(f"Error: {e}")
        with open("error.log", "w") as f:
            traceback.print_exc(file=f)
        text_response = "Bir hata oluştu."

    return jsonify({'response': text_response, 'command': command})

if __name__ == '__main__':
    app.run(debug=True)
