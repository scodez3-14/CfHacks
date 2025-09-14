import os
import sqlite3
import requests
import random
import time
from flask import Flask, request, jsonify

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN environment variable")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

app = Flask(__name__)

# --- SQLite setup ---
DB_PATH = "botdata.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    step TEXT,
                    rating INTEGER,
                    count INTEGER,
                    tag TEXT
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    contestId INTEGER,
                    index TEXT,
                    name TEXT,
                    rating INTEGER,
                    ts DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
    conn.commit()
    conn.close()

def db_get_user(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT chat_id,step,rating,count,tag FROM users WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"chat_id": row[0], "step": row[1], "rating": row[2], "count": row[3], "tag": row[4]}
    return None

def db_upsert_user(chat_id, **kwargs):
    u = db_get_user(chat_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if u is None:
        c.execute("INSERT INTO users (chat_id, step, rating, count, tag) VALUES (?, ?, ?, ?, ?)",
                  (chat_id, kwargs.get("step"), kwargs.get("rating"), kwargs.get("count"), kwargs.get("tag")))
    else:
        fields = []
        vals = []
        for k in ("step","rating","count","tag"):
            if k in kwargs:
                fields.append(f"{k}=?")
                vals.append(kwargs[k])
        if fields:
            vals.append(chat_id)
            c.execute(f"UPDATE users SET {', '.join(fields)} WHERE chat_id=?", vals)
    conn.commit()
    conn.close()

def db_add_history(chat_id, p):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO history (chat_id, contestId, index, name, rating) VALUES (?, ?, ?, ?, ?)",
              (chat_id, p["contestId"], p["index"], p["name"], p.get("rating")))
    conn.commit()
    conn.close()

def db_get_history(chat_id, limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT contestId, index, name, rating, ts FROM history WHERE chat_id=? ORDER BY ts DESC LIMIT ?", (chat_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

# --- Codeforces problem cache ---
CF_CACHE = {"timestamp": 0, "problems": []}
CF_CACHE_TTL = 60 * 60

def fetch_cf_problems(refresh=False):
    now = time.time()
    if CF_CACHE["problems"] and not refresh and now - CF_CACHE["timestamp"] < CF_CACHE_TTL:
        return CF_CACHE["problems"]
    url = "https://codeforces.com/api/problemset.problems"
    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
        return []
    j = resp.json()
    if j.get("status") != "OK":
        return []
    CF_CACHE["problems"] = j["result"]["problems"]
    CF_CACHE["timestamp"] = now
    return CF_CACHE["problems"]

def find_problems_by_rating(rating, count=1):
    problems = fetch_cf_problems()
    filtered = [p for p in problems if p.get("rating") == rating]
    random.shuffle(filtered)
    return filtered[:count]

def find_problems_by_tag_and_rating(tag, rating=None, count=1):
    problems = fetch_cf_problems()
    filtered = []
    for p in problems:
        if "tags" in p and tag.lower() in [t.lower() for t in p["tags"]]:
            if rating is None or p.get("rating") == rating:
                filtered.append(p)
    random.shuffle(filtered)
    return filtered[:count]

def random_problem():
    problems = fetch_cf_problems()
    return random.choice(problems) if problems else None

# --- Telegram helpers ---
def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    if parse_mode:
        data["parse_mode"] = parse_mode
    requests.post(TELEGRAM_API + "sendMessage", json=data, timeout=10)

def answer_callback(callback_id, text=None):
    data = {"callback_query_id": callback_id}
    if text:
        data["text"] = text
    requests.post(TELEGRAM_API + "answerCallbackQuery", json=data, timeout=5)

def mk_inline_keyboard(button_rows):
    return {"inline_keyboard": button_rows}

# --- Bot flows ---
def start_flow(chat_id):
    db_upsert_user(chat_id, step=None, rating=None, count=None, tag=None)
    text = ("👋 Welcome to CF Practice Bot!\n\n"
            "Commands:\n"
            "/rating - choose rating and number of problems\n"
            "/random - random problem\n"
            "/tags - choose by tag\n"
            "/history - last problems you received\n"
            "/help - show this menu")
    send_message(chat_id, text)

def help_flow(chat_id):
    start_flow(chat_id)

def rating_start(chat_id):
    db_upsert_user(chat_id, step="awaiting_rating")
    kb = mk_inline_keyboard([
        [{"text": "Easy 800", "callback_data": "rating_800"},
         {"text": "1200", "callback_data": "rating_1200"},
         {"text": "1600", "callback_data": "rating_1600"}],
        [{"text": "1800+", "callback_data": "rating_1800"}]
    ])
    send_message(chat_id, "Please enter a rating number (e.g., 800, 1200) or choose below:", reply_markup=kb)

def tags_start(chat_id):
    db_upsert_user(chat_id, step="awaiting_tag")
    tags = ["dp","greedy","graphs","math","implementation","strings","binary search"]
    rows = []
    row = []
    for i, t in enumerate(tags):
        row.append({"text": t.title(), "callback_data": f"tag_{t}"})
        if (i+1) % 3 == 0:
            rows.append(row)
            row = []
    if row: rows.append(row)
    kb = mk_inline_keyboard(rows)
    send_message(chat_id, "Choose a tag:", reply_markup=kb)

def send_problems_to_user(chat_id, problems):
    if not problems:
        send_message(chat_id, "No problems found for your filters. Try a different rating/tag.")
        return
    for p in problems:
        url = f"https://codeforces.com/problemset/problem/{p['contestId']}/{p['index']}"
        rating = p.get("rating", "N/A")
        text = f"{p['name']} [{rating}]\n{url}"
        send_message(chat_id, text)
        db_add_history(chat_id, p)
    send_message(chat_id, "✅ Done. Use /rating or /tags again to get more.")

def send_history(chat_id):
    rows = db_get_history(chat_id, limit=10)
    if not rows:
        send_message(chat_id, "No history yet.")
        return
    text = "Your recent problems:\n"
    for r in rows:
        contestId, idx, name, rating, ts = r
        text += f"- {name} [{rating}] — https://codeforces.com/problemset/problem/{contestId}/{idx}\n"
    send_message(chat_id, text)

# --- Webhook ---
@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "Bot is alive"
    data = request.get_json()

    # Handle callback_query (inline keyboard presses)
    if "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data_cb = cb["data"]
        callback_id = cb["id"]

        if data_cb.startswith("rating_"):
            rating = int(data_cb.split("_",1)[1])
            db_upsert_user(chat_id, rating=rating, step="awaiting_count")
            answer_callback(callback_id, f"Rating set to {rating}. Now send number of problems (e.g., 3).")
            send_message(chat_id, f"Rating {rating} saved. Now enter number of problems:")
        elif data_cb.startswith("tag_"):
            tag = data_cb.split("_",1)[1]
            db_upsert_user(chat_id, tag=tag, step="awaiting_tag_count")
            answer_callback(callback_id, f"Tag set to {tag}. Now send number of problems (e.g., 3).")
            send_message(chat_id, f"Tag `{tag}` saved. Now enter number of problems:", parse_mode=None)
        else:
            answer_callback(callback_id, "Unknown action.")
        return jsonify(ok=True)

    # Handle normal messages
    if "message" in data:
        msg = data["message"]
        text = msg.get("text","").strip()
        chat_id = msg["chat"]["id"]

        if db_get_user(chat_id) is None:
            db_upsert_user(chat_id, step=None)

        # Commands
        if text == "/start":
            start_flow(chat_id); return jsonify(ok=True)
        if text == "/help":
            help_flow(chat_id); return jsonify(ok=True)
        if text == "/rating":
            rating_start(chat_id); return jsonify(ok=True)
        if text == "/random":
            p = random_problem()
            if not p:
                send_message(chat_id, "Could not fetch problems from Codeforces right now.")
            else:
                send_problems_to_user(chat_id, [p])
            return jsonify(ok=True)
        if text == "/tags":
            tags_start(chat_id); return jsonify(ok=True)
        if text == "/history":
            send_history(chat_id); return jsonify(ok=True)

        # Handle conversation states
        u = db_get_user(chat_id)
        step = u.get("step")

        if step == "awaiting_rating":
            if text.isdigit():
                rating = int(text)
                db_upsert_user(chat_id, rating=rating, step="awaiting_count")
                send_message(chat_id, f"Rating {rating} saved. Now enter number of problems you want:")
            else:
                send_message(chat_id, "Please send a numeric rating (e.g., 800, 1200).")
            return jsonify(ok=True)

        if step == "awaiting_count":
            if text.isdigit():
                count = max(1, min(10, int(text)))
                rating = u.get("rating")
                problems = find_problems_by_rating(rating, count)
                send_problems_to_user(chat_id, problems)
                db_upsert_user(chat_id, step=None, rating=None, count=None)
            else:
                send_message(chat_id, "Please send a valid number (e.g., 3). Max 10.")
            return jsonify(ok=True)

        if step == "awaiting_tag":
            tag = text.lower()
            db_upsert_user(chat_id, tag=tag, step="awaiting_tag_count")
            send_message(chat_id, f"Tag `{tag}` saved. Now enter number of problems:")
            return jsonify(ok=True)

        if step == "awaiting_tag_count":
            if text.isdigit():
                count = max(1, min(10, int(text)))
                tag = u.get("tag")
                problems = find_problems_by_tag_and_rating(tag, rating=None, count=count)
                send_problems_to_user(chat_id, problems)
                db_upsert_user(chat_id, step=None, tag=None)
            else:
                send_message(chat_id, "Please enter a number of problems (max 10).")
            return jsonify(ok=True)

        # Fallback
        send_message(chat_id, "I didn't understand that. Use /help to see commands.")
        return jsonify(ok=True)

    return jsonify(ok=True)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
