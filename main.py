"""
main.py — StoryMaker 3 Dual-Engine Pipeline Orchestrator.
Generates BOTH a YouTube Short (9:16) and a Long-Form video (16:9).

Usage:
    python main.py                 # Full pipeline (generate + upload)
    python main.py --skip-upload   # Generate only, no YouTube upload
"""

import sys
import argparse
import traceback
import os

from notify import send_telegram_alert
from utils import logger, create_run_directory, cleanup_temp_files
from story_picker import pick_story, mark_used
from image_generator import generate_images
from voice_generator import generate_voice
from video_assembler import assemble_video
from youtube_uploader import upload_video
from schedule_manager import get_next_schedule_time, update_last_schedule


def main():
    parser = argparse.ArgumentParser(description="StoryMaker 3 — Dual-Engine YouTube Pipeline")
    parser.add_argument("--skip-upload", action="store_true", help="Skip YouTube upload (testing mode)")
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("  StoryMaker 3 — Dual-Engine Pipeline Starting")
    logger.info("=" * 50)

    try:
        # ── Step 1: Pick a story ─────────────────────────
        logger.info("\n📖 STEP 1: Picking story...")
        story = pick_story()
        logger.info(f'  Title: "{story.title}"')
        logger.info(f'  Moral: "{story.moral}"')

        # ── Step 2: Create output directory ──────────────
        run_dir = create_run_directory()
        logger.info(f"  Output: {run_dir}")

        # ── Step 3: Generate images ──────────────────────
        logger.info("\n🎨 STEP 2: Generating images...")
        image_paths = generate_images(story, run_dir)

        # ── Step 4: Generate dual voiceover ──────────────
        logger.info("\n🎙️ STEP 3: Generating dual voiceover...")
        voice_data = generate_voice(story, run_dir)

        # ── Step 5: Assemble BOTH videos ─────────────────
        logger.info("\n🎬 STEP 4: Assembling dual videos...")
        short_path, long_path = assemble_video(image_paths, voice_data, story, run_dir)

        # ── Step 6: Upload to YouTube ────────────────────
        if args.skip_upload:
            logger.info("\n⏭️ STEP 5: Upload skipped (--skip-upload)")
            logger.info(f"  Short ready at: {short_path}")
            logger.info(f"  Long  ready at: {long_path}")
        else:
            logger.info("\n📤 STEP 5: Uploading & Scheduling to YouTube...")
            
            # ── Upload Short ──
            short_publish_at = get_next_schedule_time(is_short=True)
            logger.info(f"  Scheduling Short for: {short_publish_at} (UTC)")
            short_url = upload_video(short_path, story, is_short=True, publish_at=short_publish_at)
            update_last_schedule(is_short=True, dt_str=short_publish_at)
            logger.info(f"  Short Scheduled: {short_url}")

            # ── Upload Long ──
            long_publish_at = get_next_schedule_time(is_short=False)
            logger.info(f"  Scheduling Long for: {long_publish_at} (UTC)")
            long_url = upload_video(long_path, story, is_short=False, publish_at=long_publish_at)
            update_last_schedule(is_short=False, dt_str=long_publish_at)
            logger.info(f"  Long Scheduled: {long_url}")

            # Silent success notification
            send_telegram_alert(
                f"✅ StoryMaker 3 done!\n"
                f"📖 Story: {story.title}\n"
                f"▶️ Short: {short_url}\n"
                f"🎬 Long: {long_url}",
                silent=True
            )

        # ── Step 7: Cleanup Temporary Files ────────────────
        logger.info("\n🧹 STEP 6: Cleaning up output directory...")
        cleanup_temp_files(run_dir, keep_final=args.skip_upload)

        logger.info("\n" + "=" * 50)
        logger.info("  ✅ Dual-Engine Pipeline complete!")
        logger.info(f"  📹 Short: {short_path}")
        logger.info(f"  📹 Long:  {long_path}")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"\n❌ Pipeline failed: {e}")
        traceback.print_exc()
        
        # Send Telegram alert
        error_msg = f"🔴 <b>StoryMaker 3 Pipeline Crash</b>\n<b>Type:</b> <code>{type(e).__name__}</code>\n<b>Message:</b> <code>{str(e)[:500]}</code>"
        
        # Add link to GitHub Actions log if running in workflow
        run_id = os.environ.get("GITHUB_RUN_ID")
        repo = os.environ.get("GITHUB_REPOSITORY")
        if run_id and repo:
            error_msg += f"\n\n🔗 <a href='https://github.com/{repo}/actions/runs/{run_id}'>View Log</a>"

        send_telegram_alert(error_msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
