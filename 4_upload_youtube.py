import os, base64, json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_B64 = os.getenv("YOUTUBE_TOKEN_BASE64", "")
VIDEO_FILE = "output/FINAL_VIDEO.mp4"
THUMBNAIL_FILE = "scene_images/scene_thumb.jpg" 

def upload_to_youtube():
    if not TOKEN_B64 or not os.path.exists(VIDEO_FILE):
        print("⚠️ Token or Video missing. Skipping YouTube upload.")
        return

    # SEO Read karna
    try:
        with open("questions.json", "r", encoding="utf-8") as f: data = json.load(f)["seo"]
        title, description, tags = data["title"], data["description"], data["tags"]
    except:
        title, description, tags = "Viral Amazing Facts", "Watch this amazing long-form video!", ["viral", "facts"]

    try:
        creds = Credentials.from_authorized_user_info(json.loads(base64.b64decode(TOKEN_B64).decode('utf-8')))
        youtube = build('youtube', 'v3', credentials=creds)
        
        body = {
            'snippet': {
                'title': title[:100], 
                'description': description + "\n\n#education #viral",
                'tags': tags[:15], 
                'categoryId': '27' 
            },
            'status': {
                # 🟢 YAHAN HAI MAGIC: 'public' karte hi video turant LIVE ho jayega bina kisi schedule ke!
                'privacyStatus': 'public',      
                'selfDeclaredMadeForKids': False, 
                'containsSyntheticMedia':  False   
            }
        }
        
        print(f"🚀 Uploading & Publishing LIVE immediately... Title: {title}")
        media = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True, mimetype='video/mp4')
        request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        response = request.execute()
        
        video_id = response.get('id')
        print(f"🎉 YouTube Upload Complete! Video is now LIVE: https://youtu.be/{video_id}")
        
        # 🟢 THUMBNAIL UPLOAD LOGIC
        with open("client_config.json", "r") as f: config = json.load(f)
        if config.get("generate_thumbnail") and os.path.exists(THUMBNAIL_FILE):
            print("🖼️ Uploading custom 4K Thumbnail to YouTube...")
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(THUMBNAIL_FILE, mimetype='image/jpeg')
                ).execute()
                print("✅ Custom Thumbnail Set Successfully!")
            except Exception as e:
                print(f"⚠️ Thumbnail Upload Failed: {e}")

    except Exception as e:
        print(f"❌ YouTube Upload Failed: {e}")

if __name__ == "__main__":
    upload_to_youtube()
