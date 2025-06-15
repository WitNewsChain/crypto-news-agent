import os
import json
import time
import feedparser
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from openai import OpenAI

# إعداد متغيرات البيئة من GitHub Secrets
openai_api_key = os.environ["OPENAI_API_KEY"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_CREDENTIALS_FILE = os.environ["GOOGLE_CREDENTIALS_FILE"]

# إعداد الاتصال بـ OpenAI
client = OpenAI(api_key=openai_api_key)

# إعداد Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scope)
sheet_client = gspread.authorize(creds)
sheet = sheet_client.open_by_key(GOOGLE_SHEET_ID).sheet1

# تحميل المقالات المعالجة مسبقاً
if os.path.exists("processed_articles.json"):
    with open("processed_articles.json", "r") as f:
        processed_articles = json.load(f)
else:
    processed_articles = []

# المصادر (أهم 5 مصادر أخبار كريبتو)
feeds = [
    "https://decrypt.co/feed",
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptoslate.com/feed/",
    "https://bitcoinmagazine.com/.rss/full/"
]

# يساعد على توليد تغريدة احترافية
def summarize_with_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "أنت مساعد ذكي تقوم بتلخيص أهم أخبار الكريبتو على شكل تغريدات احترافية جذابة دون روابط داخل النص."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=180
    )
    return response.choices[0].message.content.strip()

# يحدد هل الخبر مهم فعلاً
def is_important(title):
    importance_prompt = (
        f"هل العنوان التالي يمثل خبرًا مهمًا جدًا في عالم الكريبتو اليوم؟\n\n"
        f"العنوان: {title}\n\n"
        "أجب فقط بـ نعم أو لا."
    )
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": importance_prompt}
        ],
        temperature=0
    )
    answer = response.choices[0].message.content.lower()
    return "نعم" in answer or "yes" in answer

# يجمع التغريدات ويضيفها للجدول
new_entries = []

for feed_url in feeds:
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        title = entry.title
        link = entry.link

        if link in processed_articles:
            continue

        if not is_important(title):
            continue

        prompt = (
            f"""قم بتلخيص العنوان التالي إلى تغريدة احترافية (280 حرفًا كحد أقصى). 
- لا تضع روابط داخل التغريدة.
- اجعلها جذابة، بصيغة بشرية.
- أضف وسومًا مناسبة.

العنوان:
{title}
"""
        )
        tweet = summarize_with_gpt(prompt)
        final_tweet = f"{tweet}\n{link}"

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, title, link, final_tweet])
        print(f"✅ تم نشر: {title}")

        processed_articles.append(link)
        new_entries.append(link)

        # فاصل زمني بين التغريدات
        time.sleep(10)

# حفظ القائمة
with open("processed_articles.json", "w") as f:
    json.dump(processed_articles, f, ensure_ascii=False, indent=2)

print(f"\n✅ أُضيف {len(new_entries)} خبرًا مهمًا إلى Google Sheets.")
