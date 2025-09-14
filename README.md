
# Telegram Codeforces Bot

A simple Telegram bot that asks users for a problem rating and number of questions,
then sends random Codeforces problems matching that rating.

## Features
- Ask user for a Codeforces problem rating (e.g., 800, 1200)
- Ask user for number of questions to receive
- Fetch random problems from Codeforces API
- Send problem name and link directly to the user
- Simple conversation flow with state tracking

## Tech Stack
- Python 3
- Flask (web framework)
- Requests (HTTP requests)
- Render (for web deployment)

## Installation
1. Clone the repository
2. Create virtual environment (optional)
3. Install dependencies:
    pip install flask requests
4. Set your Telegram bot token as environment variable:
    export BOT_TOKEN="your_telegram_bot_token"  # Linux/macOS
    set BOT_TOKEN="your_telegram_bot_token"     # Windows

## Usage
1. Run locally:
    python app.py
2. Set webhook:
    https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_URL>
3. Chat with bot in Telegram:
    - Enter rating (e.g., 1200)
    - Enter number of questions (e.g., 3)
    - Receive random CF problems

## Deployment
- Deploy as Web Service on Render
- Start command: python app.py
- Add BOT_TOKEN as environment variable
