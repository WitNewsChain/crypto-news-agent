import os
import json
import time
import feedparser
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from openai import OpenAI

openai_api_key = os.environ["OPENAI_API_KEY"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_CREDENTIALS_FILE = os.environ["GOOGLE_CREDENTIALS_FILE"]

client = OpenAI(api_key=openai_api_key)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scope)
sheet_client = gspread.authorize(creds)
sheet = sheet_client.open_by_key(GOOGLE_SHEET_ID).sheet1

if os.path.exists("processed_articles.json"):
    with open("processed_articles.json", "r") as f:
        processed_articles = json.load(f)
else:
    processed_articles = []

feeds = [
    "https://decrypt.co/feed",
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptoslate.com/feed/",
    "https://bitcoinmagazine.com/.rss/full/"
]

def summarize_with_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "You are a smart assistant summarizing the most important crypto news as professional tweets with no links inside the text."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=180
    )
    return response.choices[0].message.content.strip()

def is_important(title):
    importance_prompt = (
        f"Is the following crypto headline very important today?\n\n"
        f"Headline: {title}\n\n"
        "Answer with only Yes or No."
    )
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": importance_prompt}
        ],
        temperature=0
    )
    answer = response.choices[0].message.content.lower()
    return "yes" in answer

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
            f"Summarize the following crypto headline into a professional tweet (max 280 characters). "
            f"Do not include links in the tweet. Make it engaging and human-like. Add relevant hashtags.\n\n"
            f"Headline:\n{title}"
        )
        tweet = summarize_with_gpt(prompt)
        final_tweet = f"{tweet}\n{link}"

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, title, link, final_tweet])
        print(f"✅ Posted: {title}")

        processed_articles.append(link)
        new_entries.append(link)

        time.sleep(10)

with open("processed_articles.json", "w") as f:
    json.dump(processed_articles, f, ensure_ascii=False, indent=2)

print(f"\n✅ {len(new_entries)} important articles added to Google Sheets.")
