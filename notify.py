"""
notify.py — Telegram Notification System
Sends alerts to a Telegram bot for failures or warnings.
"""

import os
import requests
from utils import logger
from dotenv import load_dotenv

# Ensure .env is loaded so we can read tokens if running locally
load_dotenv()

def send_telegram_alert(message: str):
    """
    Sends an HTML-formatted message to the Telegram bot configured in .env
    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        logger.warning("Telegram secrets not found. Skipping Telegram notification.")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Telegram notification sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")

if __name__ == "__main__":
    # Test script usage
    send_telegram_alert("⚠️ Tests Telegram Notification from notify.py")
