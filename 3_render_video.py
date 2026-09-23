import os, json, time, requests, random, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import *
from moviepy.audio.AudioClip import concatenate_audioclips

def live_print(msg): print(msg, flush=True)

with open("client_config.json", "r", encoding="utf-8") as f: config = json.load(f)
CLIENT_NAME, LOGO_FILE = config["client_name"], config.get("logo_file", "logo.png")
THEME, TIMER_SEC = config["theme_colors"], config["timer_seconds"]
TARGET_SECONDS = config.get("target_video_minutes", 10) * 60

GNANI_API_KEY = os.getenv("GNANI_API_KEY")
FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
BOT_TOKEN, CHAT_ID = os.getenv("BOT_TOKEN"), os.getenv("CHAT_ID")
HINDI_FONT, BGM_FILE = "NirmalaB.ttf", "bgm.mp3"

for folder in ["temp_chunks", "output", "sfx", "loops", "temp_audio"]: os.makedirs(folder, exist_ok=True)

def download_freesound(query, filename):
    out_path = f"sfx/{filename}"
    if os.path.exists(out_path): return out_path
    if not FREESOUND_API_KEY: return None
    try:
        res = requests.get(f"https://freesound.org/apiv2/search/text/?query={query}&token={FREESOUND_API_KEY}&fields=id,name,previews").json()
        if res.get('results'):
            with open(out_path, "wb") as f: f.write(requests.get(res['results'][0]['previews']['preview-hq-mp3']).content)
            return out_path
    except: pass
    return None

# 🟢 FIX: Har sawal (idx) ke liye alag video download hoga
def download_pixabay_video(bg_keyword, idx):
    out_path = f"loops/bg_{idx}.mp4"
    if os.path.exists(out_path): return out_path
    if not PIXABAY_API_KEY: return None
    
    live_print(f"🎥 Pixabay: Searching unique background for Q{idx} ('{bg_keyword}')...")
    try:
        res = requests.get(f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={bg_keyword}&video_type=animation&per_page=3&safesearch=true").json()
        
        # Agar specific keyword nahi mila, toh fallback 'abstract' search karega
        if int(res.get('totalHits', 0)) == 0:
            res = requests.get(f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q=abstract+loop&video_type=animation&per_page=10&safesearch=true").json()
            
        if int(res.get('totalHits', 0)) > 0:
            # Random top result lega taaki variety rahe
            vid_item = random.choice(res['hits'][:3])
            with open(out_path, "wb") as f: f.write(requests.get(vid_item['videos']['medium']['url']).content)
            return out_path
    except: pass
    return None

def generate_voice(text, filename):
    filepath = f"temp_audio/{filename}"
    if os.path.exists(filepath): return filepath
    data = {"text": text, "voice": "Deepak", "model": "timbre-v2.5", "language": "hi-IN", "speed": 0.95, "audio_config": {"sample_rate": 44100, "encoding": "linear_pcm", "container": "wav"}}
    for _ in range(3):
        try:
            resp = requests.post("https://api.vachana.ai/api/v1/tts/inference", headers={"Content-Type": "application/json", "X-API-Key-ID": GNANI_API_KEY}, json=data, timeout=30)
            if resp.status_code == 200:
                with open(filepath, "wb") as f: f.write(resp.content)
                return filepath
        except: time.sleep(2)
    return None

def create_pill_option(letter, text, filename, is_correct=False):
    try: font = ImageFont.truetype(HINDI_FONT, 65)
    except: font = ImageFont.load_default()
    box_w, box_h = 800, 120
    img = Image.new('RGBA', (box_w, box_h), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    bg_color = (0, 200, 50, 255) if is_correct else tuple(THEME["option_bg"])
    text_color = (255, 255, 255) if is_correct else (0, 0, 0)
    border_color = tuple(THEME["option_border"])
    
    draw.rounded_rectangle([(0, 0), (box_w-2, box_h-2)], radius=60, fill=bg_color, outline=border_color, width=4)
    circle_color = (255,255,255) if is_correct else border_color
    draw.ellipse([(15, 15), (105, 105)], fill=circle_color)
    
    lw = draw.textbbox((0,0), letter, font=font)[2] - draw.textbbox((0,0), letter, font=font)[0]
    draw.text((60 - lw/2, 20), letter, font=font, fill=(0,150,0) if is_correct else (255,255,255))
    draw.text((140, 20), text, font=font, fill=text_color)
    img.save(f"temp_chunks/{filename}")
    return ImageClip(f"temp_chunks/{filename}")

def create_image_with_border(img_path):
    if not os.path.exists(img_path): return ColorClip((600, 600), (50,50,50))
    pil_img = Image.open(img_path).convert("RGBA").resize((700, 550), Image.Resampling.LANCZOS)
    border_img = Image.new('RGBA', (740, 590), tuple(THEME["option_border"]))
    border_img.paste(pil_img, (20, 20))
    temp_path = f"temp_chunks/bordered_temp.png"
    border_img.save(temp_path)
    return ImageClip(temp_path)

def create_question_box(text, filename, q_num):
    try: font = ImageFont.truetype(HINDI_FONT, 75)
    except: font = ImageFont.load_default()
    lines = textwrap.wrap(f"Q{q_num}: {text}", width=40)
    line_h = 90
    box_w, box_h = 1600, (len(lines) * line_h) + 60
    img = Image.new('RGBA', (box_w, box_h), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(0, 0), (box_w, box_h)], radius=30, fill=tuple(THEME["question_bg"]))
    y_text = 30
    for line in lines:
        lw = draw.textbbox((0,0), line, font=font)[2] - draw.textbbox((0,0), line, font=font)[0]
        draw.text(((box_w - lw) / 2, y_text), line, font=font, fill=tuple(THEME["question_text"]))
        y_text += line_h
    img.save(f"temp_chunks/{filename}")
    return ImageClip(f"temp_chunks/{filename}")

# 🟢 FIX: Dynamic BG gets unique keyword and idx
def get_dynamic_bg(bg_keyword, duration, idx):
    loop_file = download_pixabay_video(bg_keyword, idx)
    if loop_file and os.path.exists(loop_file):
        bg = VideoFileClip(loop_file).loop(duration=duration).resize((1920, 1080))
        overlay = ColorClip(size=(1920, 1080), color=(10, 10, 30)).set_opacity(0.85).set_duration(duration)
        return CompositeVideoClip([bg, overlay])
    return ColorClip(size=(1920, 1080), color=(15,20,35)).set_duration(duration)

def create_modern_progress_bar(duration):
    def make_frame(t):
        img = np.zeros((30, 800, 3), dtype=np.uint8)
        progress = int((t / duration) * 800)
        img[:, :progress] = THEME["progress_bar"][:3]
        return img
    return VideoClip(make_frame, duration=duration)

def create_corner_watermark(duration):
    visuals = []
    if os.path.exists(LOGO_FILE):
        logo = ImageClip(LOGO_FILE).resize(height=80).set_position((1450, 950)).set_opacity(0.7).set_duration(duration)
        visuals.append(logo)
    try: font = ImageFont.truetype(HINDI_FONT, 50)
    except: font = ImageFont.load_default()
    img = Image.new('RGBA', (400, 80), (0,0,0,0))
    ImageDraw.Draw(img).text((10, 10), CLIENT_NAME, font=font, fill=(255,255,255,180))
    img.save("temp_chunks/wm.png")
    visuals.append(ImageClip("temp_chunks/wm.png").set_position((1550, 960)).set_duration(duration))
    return visuals

def main():
    if not os.path.exists("questions.json"): return
    with open("questions.json", "r", encoding="utf-8") as f: data = json.load(f)["questions"]
    
    trans_sfx = download_freesound(config.get("transition_sfx", "soft whoosh transition"), "trans.mp3")
    timer_sfx = download_freesound(config.get("timer_sfx", "modern synth ticking"), "timer.mp3")
    
    chunk_files = []
    total_time = 0.0
    
    live_print("🚀 Rendering Unique Question Videos...")
    for i, q in enumerate(data):
        if total_time >= TARGET_SECONDS:
            live_print(f"⏱️ Target length reached! Stopping at question {i}")
            break
            
        idx = q['id']
        live_print(f"🔄 Rendering Question {idx}...")
        
        q_aud = AudioFileClip(generate_voice(f"प्रश्न {idx}, {q['q']}... A, {q['a']}... B, {q['b']}... C, {q['c']}", f"q_{idx}.wav")).volumex(2.0)
        a_aud = AudioFileClip(generate_voice(f"सही जवाब है, {q['ans']}.", f"a_{idx}.wav")).volumex(2.0)
        
        t_timer_start, t_ans_start = q_aud.duration + 0.5, q_aud.duration + 0.5 + TIMER_SEC
        total_dur = t_ans_start + a_aud.duration + 1.0 
        
        audio_layers = [q_aud.set_start(0), a_aud.set_start(t_ans_start)]
        if os.path.exists(BGM_FILE):
            from moviepy.audio.fx.audio_loop import audio_loop
            bgm = audio_loop(AudioFileClip(BGM_FILE), duration=total_dur) if AudioFileClip(BGM_FILE).duration < total_dur else AudioFileClip(BGM_FILE).subclip(0, total_dur)
            p1, p2, p3 = bgm.subclip(0, t_timer_start).volumex(0.1), bgm.subclip(t_timer_start, t_ans_start).volumex(0.8), bgm.subclip(t_ans_start, total_dur).volumex(0.1)
            audio_layers.insert(0, concatenate_audioclips([p1, p2, p3]))
            
        if timer_sfx and os.path.exists(timer_sfx): audio_layers.append(AudioFileClip(timer_sfx).set_start(t_timer_start).set_duration(TIMER_SEC))
        if trans_sfx and os.path.exists(trans_sfx): audio_layers.append(AudioFileClip(trans_sfx).set_start(total_dur - 0.5).set_duration(0.5).volumex(1.5))
        
        final_audio = CompositeAudioClip(audio_layers)
        
        # 🟢 UNIQUE BACKGROUND FOR EACH QUESTION
        bg_keyword = q.get('bg_keyword', 'abstract')
        bg = get_dynamic_bg(bg_keyword, total_dur, idx)
        
        img_clip = create_image_with_border(f"scene_images/scene_{idx}.jpg").set_position((150, 320)).set_duration(total_dur)
        q_box = create_question_box(q['q'], f"q_{idx}.png", i+1).set_position(('center', 80)).set_duration(total_dur)
        
        opt_x = 1000
        opt_a = create_pill_option("A", q['a'], f"oa_{idx}.png").set_position((opt_x, 350)).set_duration(total_dur)
        opt_b = create_pill_option("B", q['b'], f"ob_{idx}.png").set_position((opt_x, 500)).set_duration(total_dur)
        opt_c = create_pill_option("C", q['c'], f"oc_{idx}.png").set_position((opt_x, 650)).set_duration(total_dur)
        prog_bar = create_modern_progress_bar(TIMER_SEC).set_position((opt_x, 820)).set_start(t_timer_start).set_duration(TIMER_SEC)
        
        ans_txt = q['a'] if q['ans']=='A' else q['b'] if q['ans']=='B' else q['c']
        ans_y = 350 if q['ans']=='A' else 500 if q['ans']=='B' else 650
        ans_clip = create_pill_option(q['ans'], ans_txt, f"ans_{idx}.png", is_correct=True).set_position((opt_x, ans_y)).set_start(t_ans_start).set_duration(total_dur - t_ans_start)
        watermark = create_corner_watermark(total_dur)
        
        video = CompositeVideoClip([bg, q_box, img_clip, opt_a, opt_b, opt_c, prog_bar, ans_clip] + watermark).set_audio(final_audio)
        
        c_path = f"temp_chunks/c_{idx}.mp4"
        video.write_videofile(c_path, fps=24, codec="libx264", audio_codec="aac", preset="fast", bitrate="8000k", logger=None)
        
        q_aud.close(); a_aud.close(); video.close()
        chunk_files.append(c_path)
        total_time += total_dur

    live_print("🔄 Merging all chunks smoothly...")
    with open("temp_chunks/files.txt", "w") as f:
        for c in chunk_files: f.write(f"file '{os.path.abspath(c)}'\n")
    os.system("ffmpeg -f concat -safe 0 -i temp_chunks/files.txt -c copy output/FINAL_VIDEO.mp4 -y")
    live_print("🎉 Final Premium Video Rendered Successfully!")

if __name__ == "__main__": main()
