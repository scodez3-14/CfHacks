from flask import Flask, request
import requests
import os

app = Flask(__name__)

# Your bot token (better to set in Render Environment Variables)
TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/"

def send_message(chat_id, text):
    requests.post(URL + "sendMessage", json={"chat_id": chat_id, "text": text})

@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.get_json()
        if "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"]["text"]

            # Simple echo bot
            reply = f"You said: {text}"
            send_message(chat_id, reply)

        return {"ok": True}
    return "Hello, I am alive!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
