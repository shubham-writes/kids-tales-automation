"""
video_assembler.py — Dual-Engine video assembler.
Produces TWO separate videos:
  • final_short.mp4  (9:16, 1080×1920) — YouTube Short
  • final_long.mp4   (16:9, 1920×1080) — Long-Form video
"""

import random
import numpy as np
from pathlib import Path
from PIL import Image

from moviepy import (
    ImageClip, TextClip, CompositeVideoClip,
    AudioFileClip, concatenate_videoclips, VideoClip,
    CompositeAudioClip, concatenate_audioclips,
)
from moviepy.audio.fx import AudioLoop

from config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS,
    VIDEO_CODEC, AUDIO_CODEC,
    ZOOM_START, ZOOM_END,
    FONT_SIZE, FONT_PATH, FONT_COLOR, STROKE_COLOR, STROKE_WIDTH,
    SUBTITLE_Y_POSITION,
    LONG_VIDEO_WIDTH, LONG_VIDEO_HEIGHT,
    LONG_FONT_SIZE, LONG_SUBTITLE_Y_POSITION,
    LONG_ZOOM_START, LONG_ZOOM_END,
    LONG_IMAGE_STRETCH_X,
)
from utils import logger


# ═══════════════════════════════════════════════════════════════════════
#  Shared Helpers
# ═══════════════════════════════════════════════════════════════════════

def _apply_ken_burns(image_path: Path, duration: float,
                     canvas_w: int, canvas_h: int,
                     zoom_start: float, zoom_end: float,
                     contain_mode: bool = False,
                     stretch_x: float = 1.0) -> VideoClip:
    """Create a VideoClip with a slow zoom + random pan effect.

    Args:
        contain_mode: If True, image is contain-fitted onto the canvas with
                      black bars (used for long-form 16:9 videos).
                      If False, image is cover-cropped to fill (shorts).
        stretch_x:    Horizontal stretch factor applied before contain-fit.
                      E.g. 1.25 turns a 1:1 image into 5:4.
    """
    img = Image.open(image_path).convert("RGB")
    img_array = np.array(img)

    direction = random.choice(["center", "left", "right", "up", "down"])

    img_orig_w, img_orig_h = img.size
    img_aspect = img_orig_w / img_orig_h

    if contain_mode:
        # ── Pre-compute contain-fit display dimensions (constant per clip) ──
        stretched_aspect = (img_orig_w * stretch_x) / img_orig_h
        canvas_aspect = canvas_w / canvas_h

        if stretched_aspect > canvas_aspect:
            # Stretched image is wider than canvas → fit to width
            display_w = canvas_w
            display_h = int(canvas_w / stretched_aspect)
        else:
            # Stretched image is taller than canvas → fit to height
            display_h = canvas_h
            display_w = int(canvas_h * stretched_aspect)

        # Black-bar offsets (centering the image area on the canvas)
        pad_x = (canvas_w - display_w) // 2
        pad_y = (canvas_h - display_h) // 2

    def make_frame(t):
        progress = t / duration if duration > 0 else 0
        scale = zoom_start + (zoom_end - zoom_start) * progress

        if not contain_mode:
            # ── Full-cover mode (original behaviour for shorts) ──
            new_w = int(canvas_w * scale)
            new_h = int(canvas_h * scale)

            target_aspect = new_w / new_h
            if img_aspect > target_aspect:
                fit_h = new_h
                fit_w = int(new_h * img_aspect)
            else:
                fit_w = new_w
                fit_h = int(new_w / img_aspect)

            fitted = Image.fromarray(img_array).resize(
                (fit_w, fit_h), Image.Resampling.LANCZOS)

            cx = (fit_w - new_w) // 2
            cy = (fit_h - new_h) // 2
            cropped_fit = fitted.crop((cx, cy, cx + new_w, cy + new_h))
            resized = np.array(cropped_fit)

            x_center = (new_w - canvas_w) / 2
            y_center = (new_h - canvas_h) / 2

            if direction == "left":
                x_offset = int(x_center * (1.0 - progress))
                y_offset = int(y_center)
            elif direction == "right":
                x_offset = int(x_center * (1.0 + progress))
                y_offset = int(y_center)
            elif direction == "up":
                x_offset = int(x_center)
                y_offset = int(y_center * (1.0 - progress))
            elif direction == "down":
                x_offset = int(x_center)
                y_offset = int(y_center * (1.0 + progress))
            else:
                x_offset = int(x_center)
                y_offset = int(y_center)

            x_offset = max(0, min(x_offset, new_w - canvas_w))
            y_offset = max(0, min(y_offset, new_h - canvas_h))

            return resized[y_offset:y_offset + canvas_h, x_offset:x_offset + canvas_w]

        else:
            # ── Contain mode (long-form): zoom/pan the IMAGE, then place ──
            # Zoomed size of the image area
            zoomed_w = int(display_w * scale)
            zoomed_h = int(display_h * scale)

            # Resize original image (with horizontal stretch) to zoomed size
            zoomed_img = Image.fromarray(img_array).resize(
                (zoomed_w, zoomed_h), Image.Resampling.LANCZOS)

            # How much extra we have for panning
            x_extra = zoomed_w - display_w
            y_extra = zoomed_h - display_h

            if direction == "left":
                x_offset = int(x_extra * (1.0 - progress))
                y_offset = x_extra and y_extra // 2 or 0
            elif direction == "right":
                x_offset = int(x_extra * progress)
                y_offset = x_extra and y_extra // 2 or 0
            elif direction == "up":
                x_offset = x_extra // 2 if x_extra else 0
                y_offset = int(y_extra * (1.0 - progress))
            elif direction == "down":
                x_offset = x_extra // 2 if x_extra else 0
                y_offset = int(y_extra * progress)
            else:  # center
                x_offset = x_extra // 2 if x_extra else 0
                y_offset = y_extra // 2 if y_extra else 0

            x_offset = max(0, min(x_offset, x_extra))
            y_offset = max(0, min(y_offset, y_extra))

            # Crop from zoomed image to display area
            cropped = np.array(zoomed_img)[
                y_offset:y_offset + display_h,
                x_offset:x_offset + display_w,
            ]

            # Place on black canvas
            frame = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
            frame[pad_y:pad_y + display_h, pad_x:pad_x + display_w] = cropped
            return frame

    clip = VideoClip(make_frame, duration=duration).with_fps(VIDEO_FPS)
    return clip


def _create_subtitle_clips(subs: list[dict], canvas_w: int,
                           font_size: int, y_position: int) -> list[TextClip]:
    """Create word-grouped subtitle TextClips synced to word boundaries."""
    clips = []
    current_chunk = []
    font_path = FONT_PATH

    for w in subs:
        current_chunk.append(w)

        ends_with_punctuation = w["text"].endswith(('.', ',', '!', '?', ';', ':'))
        is_last_word = (w == subs[-1])

        if len(current_chunk) >= 5 or ends_with_punctuation or is_last_word:
            text = " ".join(word["text"] for word in current_chunk)
            text = text + "\n "  # Prevent Pillow from clipping descenders

            start_time = current_chunk[0]["start"]
            end_time = current_chunk[-1]["end"]
            duration = max(0.1, end_time - start_time)

            try:
                txt_clip = TextClip(
                    text=text,
                    font=font_path,
                    font_size=font_size,
                    color=FONT_COLOR,
                    stroke_color=STROKE_COLOR,
                    stroke_width=STROKE_WIDTH + 1,
                    size=(canvas_w - 120, None),
                    method="caption",
                    text_align="center",
                )
                txt_clip = (
                    txt_clip
                    .with_position(("center", y_position))
                    .with_start(start_time)
                    .with_duration(duration)
                )
                clips.append(txt_clip)
            except Exception as e:
                logger.warning(f"  Subtitle chunk skipped: {e}")

            current_chunk = []

    return clips


def _pick_bgm(story, target_duration: float) -> AudioFileClip | None:
    """Pick and prepare background music based on story tags."""
    bgm_dir = Path("assets/bg_musics")
    if not bgm_dir.exists():
        return None

    tags = " ".join(story.tags).lower()
    if "funny" in tags or "comedy" in tags:
        bgm_path = bgm_dir / "Funny_Cartoon_bgm.webm"
    elif "energetic" in tags or "action" in tags:
        bgm_path = bgm_dir / "energetic_kids_bgm.mp4"
    elif "exciting" in tags or "adventure" in tags:
        bgm_path = bgm_dir / "exciting_kids_bgm.webm"
    elif "slow" in tags or "sad" in tags or "calm" in tags:
        bgm_path = bgm_dir / "slow_paced_bgm.mp4"
    else:
        bgm_path = bgm_dir / "instrumental_kids_music.mp4"

    if not bgm_path.exists():
        files = list(bgm_dir.glob("*.*"))
        bgm_path = random.choice(files) if files else None

    if not bgm_path or not bgm_path.exists():
        return None

    logger.info(f"  Adding BGM: {bgm_path.name}")
    bgm_clip = AudioFileClip(str(bgm_path))
    bgm_clip = bgm_clip.with_volume_scaled(0.06)

    if bgm_clip.duration < target_duration:
        bgm_clip = bgm_clip.with_effects([AudioLoop(duration=target_duration)])
    else:
        bgm_clip = bgm_clip.subclipped(0, target_duration)

    return bgm_clip


def _concat_scene_audio(scene_tracks: list[dict]) -> tuple[AudioFileClip, list[dict]]:
    """
    Concatenate per-scene audio files into one track.
    Returns (combined_audio, combined_subs_with_offset).
    """
    audio_clips = []
    combined_subs = []
    time_offset = 0.0

    for track in scene_tracks:
        clip = AudioFileClip(str(track["audio"]))
        audio_clips.append(clip)

        # Offset each scene's subtitle timestamps
        for sub in track["subs"]:
            combined_subs.append({
                "text": sub["text"],
                "start": sub["start"] + time_offset,
                "end": sub["end"] + time_offset,
            })

        time_offset += clip.duration

    combined_audio = concatenate_audioclips(audio_clips)
    return combined_audio, combined_subs


# ═══════════════════════════════════════════════════════════════════════
#  Short-Form Assembly (9:16)
# ═══════════════════════════════════════════════════════════════════════

def _assemble_short(image_paths: list[Path], voice_data: dict, story,
                    output_dir: Path) -> Path:
    """Assemble the 9:16 YouTube Short from short narration tracks."""
    output_path = output_dir / "final_short.mp4"
    logger.info("  ── Assembling SHORT (9:16) ──")

    short_tracks = voice_data["short"]
    narration_audio, combined_subs = _concat_scene_audio(short_tracks)

    # Build per-scene Ken Burns clips based on each scene's audio duration
    scene_clips = []
    time_cursor = 0.0

    for i, (img_path, track) in enumerate(zip(image_paths, short_tracks)):
        scene_audio = AudioFileClip(str(track["audio"]))
        duration = max(2.0, scene_audio.duration)
        scene_audio.close()

        logger.info(f"    Scene {i+1}: {duration:.1f}s")
        clip = _apply_ken_burns(
            img_path, duration,
            VIDEO_WIDTH, VIDEO_HEIGHT,
            ZOOM_START, ZOOM_END,
        )
        scene_clips.append(clip)
        time_cursor += duration

    video = concatenate_videoclips(scene_clips, method="compose")
    sub_clips = _create_subtitle_clips(combined_subs, VIDEO_WIDTH, FONT_SIZE, SUBTITLE_Y_POSITION)

    # Mix BGM
    bgm = _pick_bgm(story, narration_audio.duration)
    final_audio = CompositeAudioClip([narration_audio, bgm]) if bgm else narration_audio

    final = CompositeVideoClip(
        [video] + sub_clips,
        size=(VIDEO_WIDTH, VIDEO_HEIGHT),
    )
    final = final.with_audio(final_audio)
    final = final.with_duration(min(final.duration, final_audio.duration))

    logger.info(f"    Exporting SHORT ({final.duration:.1f}s)...")
    final.write_videofile(
        str(output_path), fps=VIDEO_FPS,
        codec=VIDEO_CODEC, audio_codec=AUDIO_CODEC, logger=None,
    )

    narration_audio.close()
    logger.info(f"    Short saved: {output_path.name} ({output_path.stat().st_size // (1024*1024)} MB) ✓")
    return output_path


# ═══════════════════════════════════════════════════════════════════════
#  Long-Form Assembly (16:9)
# ═══════════════════════════════════════════════════════════════════════

def _assemble_long(image_paths: list[Path], voice_data: dict, story,
                   output_dir: Path) -> Path:
    """Assemble the 16:9 Long-Form video from long narration tracks."""
    output_path = output_dir / "final_long.mp4"
    logger.info("  ── Assembling LONG (16:9) ──")

    long_tracks = voice_data["long"]
    narration_audio, combined_subs = _concat_scene_audio(long_tracks)

    # Build per-scene Ken Burns clips — stretch images to 16:9
    scene_clips = []

    for i, (img_path, track) in enumerate(zip(image_paths, long_tracks)):
        scene_audio = AudioFileClip(str(track["audio"]))
        duration = max(2.0, scene_audio.duration)
        scene_audio.close()

        logger.info(f"    Scene {i+1}: {duration:.1f}s")
        clip = _apply_ken_burns(
            img_path, duration,
            LONG_VIDEO_WIDTH, LONG_VIDEO_HEIGHT,
            LONG_ZOOM_START, LONG_ZOOM_END,
            contain_mode=True,
            stretch_x=LONG_IMAGE_STRETCH_X,
        )
        scene_clips.append(clip)

    video = concatenate_videoclips(scene_clips, method="compose")
    sub_clips = _create_subtitle_clips(
        combined_subs, LONG_VIDEO_WIDTH, LONG_FONT_SIZE, LONG_SUBTITLE_Y_POSITION,
    )

    # Mix BGM
    bgm = _pick_bgm(story, narration_audio.duration)
    final_audio = CompositeAudioClip([narration_audio, bgm]) if bgm else narration_audio

    final = CompositeVideoClip(
        [video] + sub_clips,
        size=(LONG_VIDEO_WIDTH, LONG_VIDEO_HEIGHT),
    )
    final = final.with_audio(final_audio)
    final = final.with_duration(min(final.duration, final_audio.duration))

    logger.info(f"    Exporting LONG ({final.duration:.1f}s)...")
    final.write_videofile(
        str(output_path), fps=VIDEO_FPS,
        codec=VIDEO_CODEC, audio_codec=AUDIO_CODEC, logger=None,
    )

    narration_audio.close()
    logger.info(f"    Long saved: {output_path.name} ({output_path.stat().st_size // (1024*1024)} MB) ✓")
    return output_path


# ═══════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════

def assemble_video(
    image_paths: list[Path],
    voice_data: dict,
    story,
    output_dir: Path,
) -> tuple[Path, Path]:
    """
    Assemble both video formats from the dual voice data.
    Returns (short_path, long_path).
    """
    logger.info("  Assembling Dual-Engine videos...")

    short_path = _assemble_short(image_paths, voice_data, story, output_dir)
    long_path = _assemble_long(image_paths, voice_data, story, output_dir)

    logger.info("  Both videos assembled ✓")
    return short_path, long_path
