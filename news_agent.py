import os
import json
import time
import feedparser
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI

# إعداد المفاتيح من البيئة
openai_api_key = os.environ["OPENAI_API_KEY"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_CREDENTIALS_FILE = os.environ["GOOGLE_CREDENTIALS_FILE"]

# إعداد Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scope)
client_gs = gspread.authorize(creds)
sheet = client_gs.open_by_key(GOOGLE_SHEET_ID).sheet1

# تحميل الأخبار التي نُشرت سابقًا
if os.path.exists("processed_articles.json"):
    with open("processed_articles.json", "r") as f:
        processed_articles = json.load(f)
else:
    processed_articles = []

# مصادر RSS المهمة
sources = [
    "https://decrypt.co/feed",
    "https://cointelegraph.com/rss",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptobriefing.com/feed/"
]

# إعداد OpenAI client
client = OpenAI(api_key=openai_api_key)

# بناء طلب التغريدة
def build_tweet_prompt(title):
    return f"""Write a single tweet (max 280 characters) summarizing the crypto headline below.
- Do NOT include links or quotes (" ").
- Use relevant hashtags.
- Keep it clear, accurate, and engaging.

Headline:
{title}
"""

# توليد التغريدة باستخدام GPT
def summarize_with_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes crypto news headlines into concise, engaging tweets."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=150
    )
    return response.choices[0].message.content.strip()

# قراءة وتصفية العناوين المهمة من المصادر
new_entries = []
for url in sources:
    feed = feedparser.parse(url)
    for entry in feed.entries:
        title = entry.title
        link = entry.link

        if link in processed_articles:
            continue

        # استخدم فلترة بسيطة: العناوين التي تحتوي على كلمات رئيسية فقط
        keywords = ["bitcoin", "ethereum", "crypto", "SEC", "regulation", "ETF", "market", "price", "bull", "bear"]
        if not any(keyword.lower() in title.lower() for keyword in keywords):
            continue

        prompt = build_tweet_prompt(title)
        tweet_text = summarize_with_gpt(prompt)

        tweet = f"{tweet_text}\n{link}"

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, title, link, tweet])

        processed_articles.append(link)
        new_entries.append(link)

        print(f"✅ Tweet added: {tweet_text}")
        time.sleep(10)  # فاصل زمني بين كل تغريدة وأخرى لتفادي الحظر

# حفظ الروابط المعالجة
with open("processed_articles.json", "w") as f:
    json.dump(processed_articles, f, ensure_ascii=False, indent=2)

print(f"\n🎯 {len(new_entries)} important crypto headlines posted to Google Sheet.")
