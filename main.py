from flask import Flask, request
import json
import requests
import os
import datetime
import schedule
import time
import threading

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = "Ca2650d60306dfb644f0212aee155098d"
BEDS24_API_KEY = "5w6CQLbQCHs3OfqJYDy3BoI7W"
BEDS24_ACCOUNT_ID = "66lodge"

@app.route("/", methods=["GET"])
def index():
    return "Youtei Webhook Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.json
    print("▼ 受信した内容 ▼")
    print(json.dumps(body, indent=2, ensure_ascii=False))
    # 返信機能は停止（何もしない）
    return "OK", 200

def push_line_group(message):
    headers = {
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "to": GROUP_ID,
        "messages": [{"type": "text", "text": message}]
    }
    res = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=body)
    print("LINE Push:", res.status_code, res.text)

def fetch_beds24_bookings():
    url = "https://api.beds24.com/json/getBookings"
    headers = {"Content-Type": "application/json"}

    today = datetime.date.today()
    start_date = today.strftime("%Y-%m-%d")
    # 2ヶ月（60日）後まで
    end_date = (today + datetime.timedelta(days=60)).strftime("%Y-%m-%d")

    payload = {
        "authentication": {
            "apiKey": BEDS24_API_KEY,
            "accountId": BEDS24_ACCOUNT_ID
        },
        "startDate": start_date,
        "endDate": end_date
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        bookings = resp.json().get("bookings", [])
    except Exception as e:
        print("Beds24 APIエラー:", e)
        bookings = []
    return bookings

def build_cleaning_message():
    bookings = fetch_beds24_bookings()
    if not bookings:
        return "直近のIN & OUT予定はありません。"

    seen = set()
    message_lines = ["直近のIN & OUT をお知らせします。"]
    for b in bookings:
        property_name = b.get("property", "66 Lodge")
        checkin = b.get("startDate", "")
        checkout = b.get("endDate", "")
        if checkin and ("IN", checkin, property_name) not in seen:
            message_lines.append(f"{int(checkin[5:7])}月{int(checkin[8:10])}日　{property_name} チェックイン")
            seen.add(("IN", checkin, property_name))
        if checkout and ("OUT", checkout, property_name) not in seen:
            message_lines.append(f"{int(checkout[5:7])}月{int(checkout[8:10])}日　{property_name} チェックアウト")
            seen.add(("OUT", checkout, property_name))
    return "\n".join(message_lines)

def notify_cleaning_schedule():
    message = build_cleaning_message()
    push_line_group(message)

def run_scheduler():
    # Glitch（UTC）でJST朝8時=UTC23時
    schedule.every().day.at("23:00").do(notify_cleaning_schedule)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host="0.0.0.0", port=3000)
    # テスト送信したい場合は下の1行を有効化
    # notify_cleaning_schedule()
