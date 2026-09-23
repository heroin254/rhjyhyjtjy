import os, json, time, requests, sys
from openai import OpenAI

def live_print(msg): print(msg, flush=True)

try:
    with open("client_config.json", "r", encoding="utf-8") as f: config = json.load(f)
except Exception:
    live_print("❌ ERROR: client_config.json not found!"); sys.exit(1)

CLIENT_NAME = config.get("client_name", "GK Master")
TOPIC = config.get("topic", "General Knowledge")
LANGUAGE = config.get("language", "Hindi")
TARGET_MINUTES = config.get("target_video_minutes", 10)
GENERATE_THUMB = config.get("generate_thumbnail", True)

TOTAL_QUESTIONS = int((TARGET_MINUTES * 60) / 15) + 3

XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")
BOT_TOKEN, CHAT_ID = os.getenv("BOT_TOKEN"), os.getenv("CHAT_ID")
client = OpenAI(api_key=XKIRO_API_KEY, base_url="https://api.xkiro.com/v1", timeout=90.0) if XKIRO_API_KEY else None

def send_telegram(msg):
    live_print(f"📲 Telegram: {msg}")
    if BOT_TOKEN and CHAT_ID:
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        except: pass

def get_strictly_free_models():
    try:
        models = [m.id for m in client.models.list(timeout=15.0).data]
        free_models = [m for m in models if ":free" in m.lower()]
        if free_models: return free_models[:10]
    except: pass
    return ["google/gemini-2.5-pro:free", "meta-llama/llama-3.1-8b-instruct:free", "qwen/qwen-2.5-72b-instruct:free"]

def main():
    live_print(f"🚀 Generating {TOTAL_QUESTIONS} questions for {TARGET_MINUTES} min video in {LANGUAGE}...")
    send_telegram(f"🚀 Step 1: Script & SEO gen started for {CLIENT_NAME} ({TARGET_MINUTES} mins)...")
    
    thumb_instruction = """
    Generate an EXTREMELY CLICKBAITY, hyper-realistic, 4K cinematic thumbnail prompt for Bing Image Creator. 
    IMPORTANT STRICT RULE: Add the exact words "NO TEXT, NO LETTERS, NO WORDS in the image" to the prompt.
    CRITICAL: The thumbnail_prompt MUST be UNDER 400 characters AND IN ENGLISH.
    """ if GENERATE_THUMB else "No thumbnail prompt needed."

    # 🟢 FIX: bg_type ki jagah bg_keyword (Unique for EVERY question)
    prompt = f"""
    You are an expert Quiz Master. Topic: {TOPIC}.
    CRITICAL INSTRUCTION: The entire JSON output (Title, Description, Questions, Options, Answers) MUST BE WRITTEN STRICTLY IN {LANGUAGE}. 
    If {LANGUAGE} is 'Hindi', you MUST use the pure Devanagari script.
    
    Generate exactly {TOTAL_QUESTIONS} fast-paced MCQ questions.
    For EACH question, generate a unique 1-2 word English search term for a background video ('bg_keyword'). Examples: "fire", "water drop", "planet", "brain", "money", "clock".
    {thumb_instruction}
    
    Return ONLY valid JSON format without any markdown or extra text.
    {{
        "seo": {{
            "title": "Viral Clickbait Title in {LANGUAGE}", 
            "description": "Desc in {LANGUAGE}", 
            "tags": ["tag1", "tag2"],
            "thumbnail_prompt": "Cinematic shot of... (keep this in English, max 400 chars)"
        }},
        "questions": [ 
            {{"id": 1, "q": "...", "a": "...", "b": "...", "c": "...", "ans": "A/B/C", "img_prompt": "Cinematic shot... (in English)", "bg_keyword": "water drop"}} 
        ]
    }}
    """
    
    for model in get_strictly_free_models():
        live_print(f"🔄 Trying strictly FREE model: {model}...")
        try:
            resp = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.7, timeout=90.0)
            text = resp.choices[0].message.content.strip()
            if text.startswith("```json"): text = text[7:-3]
            elif text.startswith("```"): text = text[3:-3]
            
            data = json.loads(text.strip())
            if "questions" in data:
                with open("questions.json", "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
                live_print(f"✅ Step 1 Done successfully using model: {model}!")
                send_telegram(f"✅ Script & SEO Ready! Model used: {model}")
                return
        except Exception as e: 
            live_print(f"⚠️ Model {model} Failed: {e}"); time.sleep(2)
    sys.exit(1)

if __name__ == "__main__": main()
