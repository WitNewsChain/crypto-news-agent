import os
import json
import gspread
from google.oauth2.service_account import Credentials
import openai
from datetime import datetime

# تحميل المفاتيح من GitHub Secrets
openai.api_key = os.environ["OPENAI_API_KEY"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_CREDENTIALS_FILE = "google_credentials.json"

# حفظ محتوى GOOGLE_CREDENTIALS كنص إلى ملف json
with open(GOOGLE_CREDENTIALS_FILE, "w") as f:
    f.write(os.environ["GOOGLE_CREDENTIALS"])

# إعداد Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

# تحميل التغريدات التي نُشرت مسبقًا
if os.path.exists("processed_articles.json"):
    with open("processed_articles.json", "r") as f:
        processed_articles = json.load(f)
else:
    processed_articles = []

rows = sheet.get_all_records()

for row in rows:
    url = row["url"]
    tweet = row["tweet"]
    has_image = row.get("image", "") != ""

    if url in processed_articles:
        continue

    # 🟦 تنسيق التغريدة حسب وجود الصورة
    if not has_image:
        tweet_to_post = f"{tweet}\n{url}"
    else:
        tweet_to_post = tweet  # اللينك سيظهر مع الصورة تلقائيًا

    print(f"نشر التغريدة: {tweet_to_post}")

    # ✳️ هنا يتم النشر الحقيقي باستخدام واجهة تويتر — مبدئيًا مطبوعة فقط
    # send_to_twitter(tweet_to_post, image_url) ← لاحقًا عند توفر النشر

    processed_articles.append(url)

    # حفظ الحالة بعد كل تغريدة منشورة
    with open("processed_articles.json", "w") as f:
        json.dump(processed_articles, f, ensure_ascii=False, indent=2)

    break  # ننشر تغريدة واحدة فقط كل تشغيل
