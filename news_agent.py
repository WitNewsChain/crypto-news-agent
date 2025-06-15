import os
import json
import time
import feedparser
from datetime import datetime
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials

# إعداد مفاتيح البيئة
openai_api_key = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")

# إعداد OpenAI Client (بدون proxies)
client = OpenAI(api_key=openai_api_key)

# إعداد Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scope)
sheet = gspread.authorize(creds).open_by_key(GOOGLE_SHEET_ID).sheet1

# تحميل الأخبار التي تم نشرها مسبقًا
if os.path.exists("processed_articles.json"):
    with open("processed_articles.json", "r") as f:
        processed_articles = json.load(f)
else:
    processed_articles = []

# مصادر أخبار الكريبتو (Top 5)
FEEDS = [
    "https://decrypt.co/feed",
    "https://cointelegraph.com/rss",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://news.bitcoin.com/feed/"
]

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
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You're a helpful assistant that summarizes crypto news into professional tweets."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=150
    )
    return response.choices[0].message.content.strip()

new_entries = []

for feed_url in FEEDS:
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        title = entry.title
        link = entry.link

        if link in processed_articles:
            continue

        # فلترة الأخبار غير المهمة
        keywords = ["bitcoin", "ethereum", "crypto", "SEC", "blockchain", "investment", "trading"]
        if not any(kw.lower() in title.lower() for kw in keywords):
            continue

        prompt = build_tweet_prompt(title)
        tweet_text = summarize_with_gpt(prompt)

        # بناء التغريدة
        tweet = f"{tweet_text}\n{link}"

        # حفظ في Google Sheets
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, title, link, tweet])

        # تحديث القائمة
        processed_articles.append(link)
        new_entries.append(link)

        # فاصل زمني بسيط بين التغريدات
        time.sleep(5)

# حفظ المقالات المعالجة
with open("processed_articles.json", "w") as f:
    json.dump(processed_articles, f, ensure_ascii=False, indent=2)

print(f"{len(new_entries)} new tweets added to Google Sheets.")
