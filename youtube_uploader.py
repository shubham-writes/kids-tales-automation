"""
youtube_uploader.py — Uploads the final video to YouTube Shorts
using YouTube Data API v3 with OAuth2 authentication.
"""

import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import (
    YOUTUBE_CLIENT_SECRETS,
    YOUTUBE_TOKEN_PATH,
    YOUTUBE_CATEGORY_ID,
    YOUTUBE_PRIVACY,
)
from utils import logger
from story_picker import StoryData

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_authenticated_service():
    """Authenticate and return a YouTube API service object."""
    creds = None

    # Load cached token
    if os.path.exists(YOUTUBE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(YOUTUBE_TOKEN_PATH, SCOPES)

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(YOUTUBE_CLIENT_SECRETS):
                raise FileNotFoundError(
                    f"client_secrets.json not found at: {YOUTUBE_CLIENT_SECRETS}\n"
                    "Download it from Google Cloud Console → APIs → Credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future runs
        with open(YOUTUBE_TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(video_path: Path, story: StoryData, is_short: bool = True, publish_at: str = None) -> str:
    """
    Upload the video to YouTube (Shorts or Long-Form) with COPPA-compliant metadata 
    and optional scheduling. Returns the YouTube video URL.
    """
    logger.info("  Authenticating with YouTube...")
    youtube = _get_authenticated_service()

    if is_short:
        title = f"{story.title} | Kids Moral Story #Shorts"
    else:
        title = f"{story.title} | Kids Moral Story"
    # Truncate title to YouTube's 100-char limit
    if len(title) > 100:
        title = title[:97] + "..."

    status = {
        "privacyStatus": YOUTUBE_PRIVACY,
        "selfDeclaredMadeForKids": True,  # COPPA compliance
    }

    if publish_at:
        status["privacyStatus"] = "private"  # Scheduled videos MUST be private initially
        status["publishAt"] = publish_at

    body = {
        "snippet": {
            "title": title,
            "description": story.description,
            "tags": story.tags[:30],  # YouTube limits tags
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": status,
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 8,  # 8 MB chunks
    )

    logger.info(f"  Uploading: \"{title}\"...")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"  Upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    if is_short:
        video_url = f"https://youtube.com/shorts/{video_id}"
    else:
        video_url = f"https://youtube.com/watch?v={video_id}"
    logger.info(f"  Upload complete! {video_url} ✓")

    return video_url
