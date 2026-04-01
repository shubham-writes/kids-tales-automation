"""
voice_generator.py — Dual-Engine voice generator.
Generates TWO audio files per scene (short + long narration) using edge-tts.
Returns per-scene audio paths and word-level subtitle data for both tracks.
"""

import asyncio
import json
from pathlib import Path

import edge_tts

from config import TTS_VOICE, TTS_RATE
from utils import logger
from story_picker import StoryData


async def _generate_tts(text: str, audio_path: Path) -> list[dict]:
    """Run edge-tts for a single text block and capture word boundary events."""
    communicate = edge_tts.Communicate(text, TTS_VOICE, rate=TTS_RATE)

    word_boundaries = []

    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,
                    "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                })

    return word_boundaries


def _fallback_subs(text: str, audio_path: Path) -> list[dict]:
    """Generate synthetic word boundaries if edge-tts returns none."""
    try:
        from moviepy import AudioFileClip
        audio = AudioFileClip(str(audio_path))
        duration = audio.duration
        audio.close()
    except Exception:
        duration = 10.0

    words = text.split()
    total_chars = sum(len(w) for w in words)
    current_time = 0.0
    boundaries = []

    for w in words:
        word_time = (len(w) / max(1, total_chars)) * duration
        boundaries.append({
            "text": w,
            "start": current_time,
            "end": current_time + word_time,
        })
        current_time += word_time

    return boundaries


def generate_voice(story: StoryData, output_dir: Path) -> dict:
    """
    Generate per-scene dual audio files and subtitle data.

    Returns a dict:
    {
        "short": [{"audio": Path, "subs": [...]}, ...],   # one per scene
        "long":  [{"audio": Path, "subs": [...]}, ...],    # one per scene
    }
    """
    result = {"short": [], "long": []}
    total = len(story.scenes)

    logger.info(f"  Generating dual voiceover for {total} scenes...")

    for i, scene in enumerate(story.scenes, start=1):
        # ── Short narration ──────────────────────────────
        short_audio = output_dir / f"scene_{i}_short.mp3"
        short_text = scene.short_narration

        logger.info(f"  Scene {i}/{total} — Short ({len(short_text)} chars)...")
        short_subs = asyncio.run(_generate_tts(short_text, short_audio))

        if not short_subs:
            logger.warning(f"  Scene {i} short: No word boundaries, using fallback.")
            short_subs = _fallback_subs(short_text, short_audio)

        result["short"].append({"audio": short_audio, "subs": short_subs})

        # ── Long narration ───────────────────────────────
        long_audio = output_dir / f"scene_{i}_long.mp3"
        long_text = scene.long_narration

        logger.info(f"  Scene {i}/{total} — Long  ({len(long_text)} chars)...")
        long_subs = asyncio.run(_generate_tts(long_text, long_audio))

        if not long_subs:
            logger.warning(f"  Scene {i} long: No word boundaries, using fallback.")
            long_subs = _fallback_subs(long_text, long_audio)

        result["long"].append({"audio": long_audio, "subs": long_subs})

    # Save combined subtitle data for debugging
    subs_path = output_dir / "subtitles_dual.json"
    subs_export = {
        "short": [{"scene": i+1, "subs": s["subs"]} for i, s in enumerate(result["short"])],
        "long":  [{"scene": i+1, "subs": s["subs"]} for i, s in enumerate(result["long"])],
    }
    with open(subs_path, "w", encoding="utf-8") as f:
        json.dump(subs_export, f, indent=2)

    short_total_kb = sum(s["audio"].stat().st_size for s in result["short"]) // 1024
    long_total_kb = sum(s["audio"].stat().st_size for s in result["long"]) // 1024

    logger.info(f"  Short audio: {short_total_kb} KB total ✓")
    logger.info(f"  Long  audio: {long_total_kb} KB total ✓")
    logger.info(f"  Subtitles saved to {subs_path.name} ✓")

    return result
