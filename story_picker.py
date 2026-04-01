"""
story_picker.py — Picks an unused story from the story bank.
Tracks used stories in used_stories.json to avoid repeats.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict
from pathlib import Path

from config import STORY_BANK_PATH, USED_STORIES_PATH
from utils import logger


@dataclass
class SceneData:
    short_narration: str
    long_narration: str
    image_prompt: str


@dataclass
class StoryData:
    id: int
    title: str
    moral: str
    scenes: List[SceneData]
    description: str
    tags: List[str]


def _load_json(path: Path) -> any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def pick_story() -> StoryData:
    """Pick a random unused story from the bank."""
    bank = _load_json(STORY_BANK_PATH)

    # Load or initialize used IDs
    if USED_STORIES_PATH.exists():
        used_ids = set(_load_json(USED_STORIES_PATH))
    else:
        used_ids = set()

    all_ids = {story["id"] for story in bank}
    available_ids = all_ids - used_ids

    # Reset if all stories have been used
    if not available_ids:
        logger.warning("All stories used! Sending OUT OF STOCK alert and resetting used_stories.json...")
        from notify import send_telegram_alert
        send_telegram_alert("⚠️ <b>StoryBank Out of Stock</b>\nAll stories have been used. The system is resetting the memory and repeating old stories!")
        
        used_ids = set()
        available_ids = all_ids
        _save_json(USED_STORIES_PATH, [])

    # Pick the next available story sequentially
    chosen_id = min(available_ids)
    story_dict = next(s for s in bank if s["id"] == chosen_id)

    story = StoryData(
        id=story_dict["id"],
        title=story_dict["title"],
        moral=story_dict["moral"],
        scenes=[SceneData(**sc) for sc in story_dict["scenes"]],
        description=story_dict["description"],
        tags=story_dict["tags"],
    )

    logger.info(f"Picked story #{story.id}: \"{story.title}\"")
    
    # Immediately mark as used so it isn't repeated if the pipeline crashes
    mark_used(story.id)
    
    return story


def mark_used(story_id: int) -> None:
    """Mark a story as used after successful pipeline run."""
    if USED_STORIES_PATH.exists():
        used_ids = _load_json(USED_STORIES_PATH)
    else:
        used_ids = []

    if story_id not in used_ids:
        used_ids.append(story_id)
        _save_json(USED_STORIES_PATH, used_ids)
        logger.info(f"Marked story #{story_id} as used ({len(used_ids)} total used)")
