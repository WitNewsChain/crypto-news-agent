import os
import openai
import requests
import feedparser
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# إعداد المتغيرات من ملف البيئة
from dotenv import load_dotenv
load_dotenv()

# إعداد المفاتيح
openai.api_key = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")

# إعداد Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

# تحميل الأخبار التي تم نشرها مسبقًا
if os.path.exists("processed_articles.json"):
    with open("processed_articles.json", "r") as f:
        processed_articles = json.load(f)
else:
    processed_articles = []

# خلاصة الأخبار
feed_url = "https://decrypt.co/feed"
feed = feedparser.parse(feed_url)

def build_tweet_prompt(title):
    return f"""Write a single tweet (max 280 characters) summarizing the crypto headline below.
- Do NOT include quotes (" ") around the text.
- Do NOT include any links in the tweet body.
- Do include relevant hashtags.
- Write in a clear, engaging human tone.

Headline:
{title}
"""

def summarize_with_gpt(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You're a helpful assistant that summarizes crypto news into professional tweets."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=150
    )
    return response.choices[0].message.content.strip()

# معالجة كل خبر جديد
new_entries = []
for entry in feed.entries:
    title = entry.title
    link = entry.link

    if link in processed_articles:
        continue

    prompt = build_tweet_prompt(title)
    tweet_text = summarize_with_gpt(prompt)

    # تحقق إن كان يحتوي على صورة
    has_image = "media_content" in entry or "image" in entry.get("summary", "")

    # بناء التغريدة النهائية
    if not has_image:
        tweet = f"{tweet_text}\n{link}"
    else:
        tweet = tweet_text

    # إضافة إلى الجدول
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([timestamp, title, link, tweet])

    # حفظ كمعالج
    processed_articles.append(link)
    new_entries.append(link)

# حفظ القائمة المحدثة
with open("processed_articles.json", "w") as f:
    json.dump(processed_articles, f)

print(f"{len(new_entries)} new tweets added to Google Sheets.")
