"""
utils.py — Shared helpers for StoryMaker 3.
Logging setup, directory management, and cleanup utilities.
"""

import logging
import shutil
from pathlib import Path
from datetime import datetime

from config import OUTPUT_DIR


def setup_logging() -> logging.Logger:
    """Configure and return the project-wide logger."""
    logger = logging.getLogger("StoryMaker")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s │ %(levelname)-8s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    console.setFormatter(fmt)
    logger.addHandler(console)

    return logger


def create_run_directory() -> Path:
    """Create a timestamped output directory for this pipeline run."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def cleanup_temp_files(run_dir: Path, keep_final: bool = True) -> None:
    """
    Optionally clean up intermediate files after a successful upload.
    If keep_final is True, only the final video is kept.
    """
    if not run_dir.exists():
        return

    if keep_final:
        keep_names = {"final_short.mp4", "final_long.mp4"}
        for f in run_dir.iterdir():
            if f.name not in keep_names and f.is_file():
                f.unlink()
    else:
        shutil.rmtree(run_dir)


# Pre-initialize the logger for other modules to import
logger = setup_logging()
