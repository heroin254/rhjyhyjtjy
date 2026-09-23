import os, json, asyncio, re, sys
from playwright.async_api import async_playwright

SAVE_FOLDER = "scene_images"
os.makedirs(SAVE_FOLDER, exist_ok=True)
def live_print(msg): print(msg, flush=True)

async def generate_image(scene_id, prompt, sem):
    # 🟢 SEMAPHORE: Ek baar mein sirf 4 images download hongi taaki server crash na ho
    async with sem:
        out_path = f"{SAVE_FOLDER}/scene_{scene_id}.jpg"
        if os.path.exists(out_path): 
            live_print(f"⏩ [{scene_id}] Image already exists. Skipping.")
            return True
        
        prompt = re.sub(r'--ar\s+\d+:\d+', '', prompt)[:450]
        live_print(f"🚀 Started downloading image for [{scene_id}]...")
        
        async with async_playwright() as p:
            for attempt in range(1, 6):
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                try:
                    await page.goto("https://www.bing.com/images/create", timeout=60000)
                    await asyncio.sleep(2)
                    await page.locator("textarea, input[placeholder*='Describe']").first.fill(prompt)
                    await page.locator("button:has-text('Generate'), button:has-text('Create')").first.click()
                    try: await page.locator("text='We are generating'").wait_for(state="detached", timeout=90000)
                    except: pass
                    dl_btn = page.locator("button[title='Download']:not([disabled]), a:has-text('Download')").first
                    await dl_btn.wait_for(state="visible", timeout=60000)
                    await asyncio.sleep(4)
                    async with page.expect_download() as dl_info: await dl_btn.click()
                    await (await dl_info.value).save_as(out_path)
                    await browser.close()
                    live_print(f"✅ [{scene_id}] HD Image Downloaded Successfully!")
                    return True
                except: 
                    await browser.close()
                    await asyncio.sleep(3)
        live_print(f"❌ [{scene_id}] Failed to download after 5 attempts.")
        return False

async def main():
    try:
        with open("questions.json", "r", encoding="utf-8") as f: data = json.load(f)
        with open("client_config.json", "r") as f: config = json.load(f)
    except: 
        live_print("❌ JSON files not found!")
        sys.exit(1)
    
    questions = data.get("questions", [])
    total = len(questions)
    live_print(f"🚀 Found {total} questions. Starting bulk image generation...")
    
    # 🟢 4 parallel workers limit to save RAM
    sem = asyncio.Semaphore(4) 
    tasks = []
    
    # Add thumbnail task if requested
    if config.get("generate_thumbnail"): 
        thumb_prompt = data.get("seo", {}).get("thumbnail_prompt", "Epic cinematic 4k shot")
        tasks.append(generate_image("thumb", thumb_prompt, sem))
        
    # Add all 35+ questions automatically
    for q in questions:
        tasks.append(generate_image(q["id"], q.get("img_prompt", "cinematic shot"), sem))
        
    # Run all tasks together
    await asyncio.gather(*tasks)
    live_print("🎉 ALL IMAGES DOWNLOADED!")

if __name__ == "__main__": asyncio.run(main())
