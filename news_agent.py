import os
import json
import time
import feedparser
import gspread
import openai
from datetime import datetime
from google.oauth2.service_account import Credentials

# إعداد المفاتيح من GitHub Secrets
openai.api_key = os.environ["OPENAI_API_KEY"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_CREDENTIALS_FILE = os.environ["GOOGLE_CREDENTIALS_FILE"]

# إعداد Google Sheets باستخدام Google Service Account
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

# تحميل الأخبار التي تم نشرها مسبقًا (منع التكرار)
if os.path.exists("processed_articles.json"):
    with open("processed_articles.json", "r") as f:
        processed_articles = json.load(f)
else:
    processed_articles = []

# أهم مصادر أخبار الكريبتو (RSS Feeds)
RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://cointelegraph.com/rss",
    "https://bitcoinmagazine.com/.rss",
    "https://cryptoslate.com/feed"
]

# دالة بناء نص الطلب للذكاء الاصطناعي لتوليد تغريدة احترافية
def build_tweet_prompt(title):
    return f"""Write a single tweet (max 280 characters) summarizing the crypto headline below.
- Do NOT include quotes (" ") around the text.
- Do NOT include any links in the tweet body.
- Do include relevant hashtags.
- Write in a clear, engaging human tone.

Headline:
{title}
"""

# دالة استدعاء OpenAI لتلخيص العنوان
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

# قراءة ومعالجة الأخبار من كل مصدر RSS
new_entries = []

for feed_url in RSS_FEEDS:
    feed = feedparser.parse(feed_url)

    for entry in feed.entries:
        title = entry.title
        link = entry.link

        if link in processed_articles:
            continue  # تم معالجته من قبل

        prompt = build_tweet_prompt(title)
        tweet_text = summarize_with_gpt(prompt)

        # التحقق من وجود صورة
        has_image = "media_content" in entry or "image" in entry.get("summary", "").lower()

        # بناء التغريدة النهائية
        if not has_image:
            tweet = f"{tweet_text}\n{link}"
        else:
            tweet = tweet_text  # الصورة ستُرفق بالرابط لاحقًا عبر Make.com

        # إضافة التغريدة إلى Google Sheet
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, title, link, tweet])

        # إضافة إلى قائمة المعالَجين
        processed_articles.append(link)
        new_entries.append(link)

        print(f"✅ Added tweet: {tweet}")
        time.sleep(5)  # انتظار بسيط بين التغريدات

# حفظ الملفات المعالجة
with open("processed_articles.json", "w") as f:
    json.dump(processed_articles, f, indent=2)

print(f"\n✅ Done! {len(new_entries)} new tweet(s) added.")
