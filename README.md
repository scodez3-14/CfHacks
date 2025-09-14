# CF Practice Bot

A Telegram bot for practicing Codeforces problems interactively via chat. This bot lets users request problems by rating, tag, or randomly, and tracks their history using SQLite.

## Features
- Get Codeforces problems by rating or tag
- Request random problems
- View history of received problems
- Inline keyboard for easy selection
- Stores user state and history in SQLite

## Setup
1. **Clone the repo**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set environment variable**:
   - `BOT_TOKEN`: Your Telegram bot token
   - Optionally, set `PORT` (default: 10000)
4. **Run the bot**:
   ```bash
   python main.py
   ```

## Usage
- Add your bot to Telegram and set the webhook to your server URL
- Supported commands:
  - `/start` or `/help`: Show menu
  - `/rating`: Choose rating and number of problems
  - `/tags`: Choose by tag
  - `/random`: Get a random problem
  - `/history`: Show last received problems

## File Overview
- `main.py`: Main bot logic, webhook handler, database, and Codeforces API integration
- `requirements.txt`: Python dependencies

## Database
- SQLite file: `botdata.db`
- Tables: `users` (user state), `history` (problem history)

## API
- Uses Telegram Bot API and Codeforces API

## Deployment
- Can be run locally or deployed to any server supporting Python and Flask
- Set up HTTPS and Telegram webhook for production use

## License
MIT
