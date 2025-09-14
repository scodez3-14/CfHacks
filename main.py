from flask import Flask, request
import requests
import os
import random

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/"

user_state = {}  # store user progress: chat_id -> {"step": , "rating": }

def send_message(chat_id, text):
    requests.post(URL + "sendMessage", json={"chat_id": chat_id, "text": text})

def get_cf_problems(rating, count):
    url = "https://codeforces.com/api/problemset.problems"
    resp = requests.get(url).json()
    if resp["status"] != "OK":
        return []
    
    problems = [
        p for p in resp["result"]["problems"]
        if "rating" in p and p["rating"] == rating
    ]
    random.shuffle(problems)
    return problems[:count]

@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.get_json()
        if "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"]["text"].strip()

            if chat_id not in user_state:
                user_state[chat_id] = {"step": "ask_rating"}
                send_message(chat_id, "Welcome! Please enter a problem rating (e.g., 800, 1200):")
            
            elif user_state[chat_id]["step"] == "ask_rating":
                if text.isdigit():
                    user_state[chat_id]["rating"] = int(text)
                    user_state[chat_id]["step"] = "ask_count"
                    send_message(chat_id, "Great! Now enter how many questions you want:")
                else:
                    send_message(chat_id, "Please enter a valid number (e.g., 800, 1200).")
            
            elif user_state[chat_id]["step"] == "ask_count":
                if text.isdigit():
                    count = int(text)
                    rating = user_state[chat_id]["rating"]
                    problems = get_cf_problems(rating, count)
                    
                    if not problems:
                        send_message(chat_id, f"Sorry, no problems found for rating {rating}. Try another rating.")
                    else:
                        for p in problems:
                            link = f"https://codeforces.com/problemset/problem/{p['contestId']}/{p['index']}"
                            send_message(chat_id, f"{p['name']} ({rating})\n{link}")
                    
                    # Reset conversation
                    user_state[chat_id] = {"step": "ask_rating"}
                    send_message(chat_id, "Done ✅\n\nYou can enter a new rating to continue.")
                else:
                    send_message(chat_id, "Please enter a valid number of questions.")
        
        return {"ok": True}
    return "Bot is alive!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
