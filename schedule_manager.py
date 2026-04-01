"""
schedule_manager.py — Calculates and tracks scheduled YouTube uploads.
Handles Indian Standard Time (IST) timezone conversions and specific 
weekday/weekend time slots for short and long videos.
"""

import os
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import SCHEDULE_LOG_PATH
from utils import logger

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


def load_schedule() -> dict:
    """Load the JSON schedule tracking file."""
    if os.path.exists(SCHEDULE_LOG_PATH):
        try:
            with open(SCHEDULE_LOG_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schedule log: {e}")
    return {"short": None, "long": None}


def save_schedule(schedule_data: dict):
    """Save latest upload dates to the JSON schedule file."""
    with open(SCHEDULE_LOG_PATH, 'w') as f:
        json.dump(schedule_data, f, indent=4)


def get_next_schedule_time(is_short: bool) -> str:
    """
    Finds the next un-scheduled slot for either a short or long video.
    
    Long video:
      Weekends: 4:00 PM IST
      Weekdays: 11:30 PM IST
      
    Short video:
      Weekdays: 10:00 PM IST
      Weekends: 3:00 AM IST
      
    Returns an ISO 8601 string in UTC format ('YYYY-MM-DDThh:mm:ss.000Z')
    required by the YouTube API.
    """
    schedule_data = load_schedule()
    key = "short" if is_short else "long"
    last_dt_str = schedule_data.get(key)

    now_ist = datetime.now(IST)

    if last_dt_str:
        # Load from last scheduled time string
        if last_dt_str.endswith('Z'):
            last_dt_str = last_dt_str[:-1] + '+00:00'
        last_dt = datetime.fromisoformat(last_dt_str)
        # Advance to next day from the last scheduled date (assuming 1 video per day)
        target_date = last_dt.astimezone(IST).date() + timedelta(days=1)
    else:
        # Start scheduling tomorrow if no previous schedule exists
        target_date = now_ist.date() + timedelta(days=1)

    while True:
        weekday = target_date.weekday()
        is_weekend = weekday >= 5  # 5 = Saturday, 6 = Sunday

        if is_short:
            if is_weekend:
                # 3:00 AM IST
                dt = datetime(target_date.year, target_date.month, target_date.day, 3, 0, tzinfo=IST)
            else:
                # 10:00 PM IST (22:00)
                dt = datetime(target_date.year, target_date.month, target_date.day, 22, 0, tzinfo=IST)
        else:
            if is_weekend:
                # 4:00 PM IST (16:00)
                dt = datetime(target_date.year, target_date.month, target_date.day, 16, 0, tzinfo=IST)
            else:
                # 11:30 PM IST (23:30)
                dt = datetime(target_date.year, target_date.month, target_date.day, 23, 30, tzinfo=IST)
        
        # Ensure the scheduled time is strictly in the future (plus a small buffer)
        if dt > now_ist + timedelta(minutes=5):
            break
            
        target_date += timedelta(days=1)

    # Convert to UTC and append trailing 'Z'
    utc_dt = dt.astimezone(UTC)
    return utc_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')


def update_last_schedule(is_short: bool, dt_str: str):
    """Save the newly scheduled exact timestamp format to JSON."""
    schedule_data = load_schedule()
    key = "short" if is_short else "long"
    schedule_data[key] = dt_str
    save_schedule(schedule_data)
