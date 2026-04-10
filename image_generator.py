"""
image_generator.py — Downloads AI-generated images.
Primary:  Cloudflare Workers AI (fast, high quality)
Tier 2:   GhostAPI (fallback for Cloudflare rate limits)
Tier 3:   Bytez API (DALL-E-3)
Last:     Local Pillow placeholder image
"""
from huggingface_hub import InferenceClient
import os
import time
import base64
import requests
import textwrap
import random
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont

from config import VIDEO_WIDTH, VIDEO_HEIGHT, IMAGE_RETRY_ATTEMPTS, IMAGE_RETRY_DELAY, IMAGE_API_URL, FONT_PATH
from utils import logger
from story_picker import StoryData

# NVIDIA NIM API Key — Flux.2-Klein-4B (Primary)
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")

# NVIDIA NIM API Key — SD3 Medium (Backup)
NVIDIA_SD3_API_KEY = os.environ.get("NVIDIA_SD3_API_KEY")

# NVIDIA NIM API Key — Flux.1-Dev (Backup)
NVIDIA_FLUX1_API_KEY = os.environ.get("NVIDIA_FLUX1_API_KEY")

# 1. Paste your Hugging Face token here (Starts with hf_)
HF_API_KEY = os.environ.get("HF_API_KEY")

# 2. GhostAPI Key (Fallback for Cloudflare)
GHOST_API_KEY = os.environ.get("GHOST_API_KEY")

# 3. Bytez API Key (DALL-E-3 Fallback)
BYTEZ_API_KEY = os.environ.get("BYTEZ_API_KEY")


# ── Timeouts & Config ────────────────────────────────────────────────────────



def _truncate_prompt(prompt: str, max_len: int = 800) -> str:
    if len(prompt) <= max_len:
        return prompt
    return prompt[:max_len].rsplit(" ", 1)[0]


# ── Tier 1: NVIDIA Flux.2-Klein-4B (Primary) ─────────────────────────────────

def _generate_via_nvidia(prompt: str, save_path: Path) -> bool:
    """Generate images using NVIDIA NIM API (Black Forest Labs Flux.2-Klein-4B)"""
    if not NVIDIA_API_KEY:
        return False
        
    api_url = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    # Append vibrant styling!
    stylized_prompt = f"{prompt}, highly detailed, vibrant, colorful, eye-catching, cute cartoon children's book illustration style"
    
    # Generate at native 1024x1024 (best quality)
    # cfg_scale MUST be > 0 per API docs, seed=0 for random variety
    payload = {
        "prompt": stylized_prompt,
        "height": 1024,
        "width": 1024,
        "cfg_scale": 1,
        "samples": 1,
        "seed": 0,
        "steps": 4
    }
    
    for attempt in range(IMAGE_RETRY_ATTEMPTS):
        try:
            resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
            
            if resp.status_code == 429:
                logger.warning(f"  --> NVIDIA 429 Rate Limit. Waiting {IMAGE_RETRY_DELAY}s (Attempt {attempt+1}/{IMAGE_RETRY_ATTEMPTS})...")
                time.sleep(IMAGE_RETRY_DELAY)
                continue
                
            resp.raise_for_status()
            data = resp.json()
            
            # Flux returns images under "artifacts" key
            artifacts = data.get("artifacts", [])
            if not artifacts:
                logger.warning(f"  --> NVIDIA Flux error: No 'artifacts' in response: {str(data)[:200]}")
                return False
            
            img_b64 = artifacts[0].get("base64")
            if not img_b64:
                logger.warning(f"  --> NVIDIA Flux error: No base64 data in artifact")
                return False
                
            # Decode base64 image and save
            img_bytes = base64.b64decode(img_b64)
            save_path.write_bytes(img_bytes)
            
            logger.info(f"  --> NVIDIA Flux OK: Image saved successfully (1024x1024).")
            return True
            
        except Exception as e:
            logger.warning(f"  --> NVIDIA Flux error: {e}")
            break
            
    return False


# ── Tier 2: Cloudflare ────────────────────────────────────────────────────────

def _generate_via_cloudflare(prompt: str, save_path: Path) -> bool:
    """Generate images using Cloudflare Workers AI (Extremely fast & reliable)"""
    
    ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
    
    if not ACCOUNT_ID or not API_TOKEN:
        logger.warning("  --> Cloudflare API credentials not set in .env")
        return False
    
    # Using Cloudflare's hosted SDXL Lightning model
    MODEL = "@cf/lykon/dreamshaper-8-lcm" 
    api_url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/{MODEL}"
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # SDXL generates 1024x1024 by default. We will resize it in Python.
    # We add a fixed seed (42) to lock in the art style and character traits across scenes.
    payload = {
        "prompt": prompt,
        "seed": 42
    }
    
    for attempt in range(IMAGE_RETRY_ATTEMPTS):
        try:
            resp = requests.post(
                api_url, 
                headers=headers, 
                json=payload, 
                timeout=30
            )
            
            if resp.status_code == 429:
                logger.warning(f"  --> Cloudflare 429 Rate Limit. Waiting {IMAGE_RETRY_DELAY}s (Attempt {attempt+1}/{IMAGE_RETRY_ATTEMPTS})...")
                time.sleep(IMAGE_RETRY_DELAY)
                continue
                
            resp.raise_for_status()
            
            # Save image at native resolution (video assembler handles resizing)
            save_path.write_bytes(resp.content)
            
            logger.info(f"  --> Cloudflare OK: Image saved at native resolution.")
            return True
            
        except Exception as e:
            logger.warning(f"  --> Cloudflare error: {e}")
            break
            
    return False


# ── Tier 2: GhostAPI (Fallback) ───────────────────────────────────────────────

def _generate_via_ghostapi(prompt: str, save_path: Path) -> bool:
    """Generate images using GhostAPI (OpenAI-compatible) as a fallback."""
    if not GHOST_API_KEY:
        return False
        
    api_url = "https://api.infip.pro/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {GHOST_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # We use a non-async model like flux-schnell. Size 1024x1792 is a native 9:16 vertical ratio.
    payload = {
        "model": "flux-schnell",
        "prompt": prompt + ", high definition, 4k, digital art, masterpiece, detailed",
        "n": 1,
        "size": "1024x1792",
        "response_format": "url"
    }
    
    try:
        resp = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        
        image_url = data.get("data", [{}])[0].get("url")
        if not image_url:
            logger.warning("  --> GhostAPI: No image URL returned in response.")
            return False
            
        # Download the image from the returned URL
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        
        save_path.write_bytes(img_resp.content)
        
        logger.info(f"  --> GhostAPI OK: Image saved at native resolution.")
        return True
        
    except Exception as e:
        logger.warning(f"  --> GhostAPI error: {e}")
        return False



# ── Tier 3: Bytez API (Fallback) ──────────────────────────────────────────────

def _generate_via_bytez(prompt: str, save_path: Path) -> bool:
    """Generate images using Bytez API (openai/dall-e-3)."""
    if not BYTEZ_API_KEY:
        return False
        
    try:
        from bytez import Bytez
    except ImportError:
        logger.error("  --> Bytez library missing! Please run 'pip install bytez'.")
        return False
        
    try:
        client = Bytez(BYTEZ_API_KEY)
        model = client.model("openai/dall-e-3")
        
        # We add some styling modifiers. DALL-E-3 typically produces squares unless otherwise instructed.
        res = model.run(prompt + ", vertical portrait, masterpiece, digital art, highly detailed")
        
        # Handle custom Bytez output parsing
        error_msg = getattr(res, "error", None)
        if error_msg:
            logger.warning(f"  --> Bytez explicitly returned API error: {error_msg}")
            return False
            
        output_data = getattr(res, "output", None)
        image_url = None
        
        if isinstance(output_data, str) and output_data.startswith("http"):
            image_url = output_data
        elif isinstance(output_data, list) and len(output_data) > 0 and isinstance(output_data[0], dict):
            image_url = output_data[0].get("url")
            
        if not image_url:
            logger.warning(f"  --> Bytez: Could not extract URL from output: {output_data}")
            return False
            
        # Download the image from the returned URL
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        
        save_path.write_bytes(img_resp.content)
        
        logger.info(f"  --> Bytez OK: Image saved at native resolution via DALL-E-3.")
        return True
        
    except Exception as e:
        logger.warning(f"  --> Bytez error: {e}")
        return False


# ── Tier 4: Pollinations AI (Free Fallback) ───────────────────────────────────

def _generate_via_pollinations(prompt: str, save_path: Path) -> bool:
    """Generate images using the free, unmetered Pollinations AI API."""
    safe_prompt = quote(prompt)
    api_url = IMAGE_API_URL.format(prompt=safe_prompt, w=1080, h=1920)
    
    try:
        resp = requests.get(api_url, timeout=60)
        resp.raise_for_status()
        
        save_path.write_bytes(resp.content)
        logger.info(f"  --> Pollinations OK: Image saved at native resolution.")
        return True
    except Exception as e:
        logger.warning(f"  --> Pollinations error: {e}")
        return False


# ── Tier 5: Local placeholder ─────────────────────────────────────────────────

def _create_fallback_image(text: str, save_path: Path):
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color=(20, 30, 60))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, 60)
    except IOError:
        font = ImageFont.load_default()
    wrapped = "\n".join(textwrap.wrap(f"API unavailable\n\nScene:\n{text}", width=40))
    d.text((100, VIDEO_HEIGHT // 3), wrapped, fill=(255, 255, 255), font=font)
    img.save(save_path)
    logger.info("  --> Local fallback image created")


# ── Main Generator Function ───────────────────────────────────────────────────

def generate_images(story: StoryData, output_dir: Path) -> list[Path]:
    """
    6-tier image generation pipeline:
      1. NVIDIA NIM API (Primary)
      2. Cloudflare Workers AI (Secondary Fallback)
      3. GhostAPI (Tertiary Fallback)
      4. Bytez API (Quaternary Fallback)
      5. Pollinations AI (Free Fallback)
      6. Local Fallback
    """
    image_paths = []
    total = len(story.scenes)

    for i, scene in enumerate(story.scenes, start=1):
        save_path = output_dir / f"scene_{i}.png"
        logger.info(f"  Scene {i}/{total} — Generating image...")
        success = False

        # Tier 1: NVIDIA
        success = _generate_via_nvidia(scene.image_prompt, save_path)
        if success and i < total:
            time.sleep(1) 

        # Tier 2: Cloudflare
        if not success:
            logger.info(f"  Scene {i} — NVIDIA Failed. Trying Cloudflare backup...")
            success = _generate_via_cloudflare(scene.image_prompt, save_path)
            if success and i < total:
                time.sleep(1) # Small delay to be polite to the free API

        # Tier 3: GhostAPI
        if not success and GHOST_API_KEY:
            logger.info(f"  Scene {i} — Cloudflare Failed. Trying GhostAPI backup...")
            success = _generate_via_ghostapi(scene.image_prompt, save_path)
            if success and i < total:
                time.sleep(2)

        # Tier 3: Bytez API
        if not success and BYTEZ_API_KEY:
            logger.info(f"  Scene {i} — Earlier tiers failed. Trying Bytez backup...")
            success = _generate_via_bytez(scene.image_prompt, save_path)
            if success and i < total:
                time.sleep(2)

        # Tier 4: Pollinations AI
        if not success:
            logger.info(f"  Scene {i} — Paid APIs failed. Trying free Pollinations AI backup...")
            success = _generate_via_pollinations(scene.image_prompt, save_path)
            if success and i < total:
                time.sleep(2)

        # Tier 5: Local Fallback
        if not success:
            logger.error(f"  Scene {i} — APIs failed. Using local placeholder.")
            _create_fallback_image(scene.image_prompt, save_path)

        image_paths.append(save_path)

    logger.info(f"  All {len(image_paths)} images ready ✓")
    return image_paths