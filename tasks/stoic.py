# TASK: stoic
# SCHEDULE: every day at 05:00
# ENABLED: false
# DESCRIPTION: Sends a unique Stoic quote to Telegram each morning

import sys
from pathlib import Path
import requests
import random

# Add the project root to the Python path so we can import config
sys.path.append(str(Path(__file__).parent.parent))
import config

# Curated list of Stoic quotes
STOIC_QUOTES = [
    "You have power over your mind - not outside events. Realize this, and you will find strength. - Marcus Aurelius",
    "The happiness of your life depends upon the quality of your thoughts. - Marcus Aurelius",
    "He who is brave is free. - Seneca",
    "We suffer more often in imagination than in reality. - Seneca",
    "First say to yourself what you would be; and then do what you have to do. - Epictetus",
    "There is only one way to happiness and that is to cease worrying about things which are beyond the power of our will. - Epictetus",
    "The key is to keep company only with people who uplift you, whose presence calls forth your best. - Epictetus",
    "If you are distressed by anything external, the pain is not due to the thing itself, but to your estimate of it; and this you have the power to revoke at any moment. - Marcus Aurelius",
    "When you arise in the morning, think of what a precious privilege it is to be alive - to breathe, to think, to enjoy, to love. - Marcus Aurelius",
    "You could leave life right now. Let that determine what you do and say and think. - Marcus Aurelius"
]

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": message    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"Failed to send Telegram message: {e}")
        return False

def run():
    # Get Telegram credentials from config (ensure these are set in .env)
    bot_token = config.TELEGRAM_BOT_TOKEN
    chat_id = config.TELEGRAM_CHAT_ID

    # Select a random unique quote
    quote = random.choice(STOIC_QUOTES)

    # Send the quote
    success = send_telegram_message(bot_token, chat_id,
        f"🧘 Daily Stoic Wisdom 🧘\n\n{quote}")

    if success:
        print(f"Sent Stoic quote: {quote}")
    else:
        print("Failed to send Stoic quote")
