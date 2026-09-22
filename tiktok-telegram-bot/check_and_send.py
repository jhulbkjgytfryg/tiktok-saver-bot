#!/usr/bin/env python3
"""
Watches TikTok accounts listed in accounts.txt.
Downloads any video it hasn't seen before and sends it straight to a
Telegram chat via a bot. Keeps track of what's already been sent in
seen.json so it never re-sends the same video twice.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import requests

ACCOUNTS_FILE = Path("accounts.txt")
SEEN_FILE = Path("seen.json")
DOWNLOAD_DIR = Path("downloads")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
MAX_TELEGRAM_BYTES = 50 * 1024 * 1024  # Telegram bot API file size limit


def load_seen() -> dict:
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return {}


def save_seen(seen: dict) -> None:
    SEEN_FILE.write_text(json.dumps(seen, indent=2))


def load_accounts() -> list[str]:
    if not ACCOUNTS_FILE.exists():
        print("No accounts.txt found — nothing to check.")
        return []
    lines = ACCOUNTS_FILE.read_text().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def list_videos(account_url: str) -> list[dict]:
    """Ask yt-dlp for the video list of an account without downloading anything."""
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--playlist-end", "20",  # only look at the 20 most recent uploads
        account_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    videos = []
    for line in result.stdout.splitlines():
        try:
            videos.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return videos


def download_video(url: str, out_path: Path) -> bool:
    cmd = [
        "yt-dlp",
        "-o", str(out_path),
        "--no-playlist",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return out_path.exists()


def send_to_telegram(video_path: Path, caption: str) -> bool:
    size = video_path.stat().st_size
    if size > MAX_TELEGRAM_BYTES:
        # Too big for Telegram's bot API — send a text note instead.
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            data={"chat_id": CHAT_ID, "text": f"{caption}\n\n(Video too large for Telegram, {size // 1_000_000}MB)"},
        )
        return False
    with open(video_path, "rb") as f:
        resp = requests.post(
            f"{TELEGRAM_API}/sendVideo",
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"video": f},
            timeout=300,
        )
    return resp.ok


def main() -> None:
    accounts = load_accounts()
    if not accounts:
        return

    seen = load_seen()
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    for account in accounts:
        print(f"Checking {account} ...")
        seen_ids = set(seen.get(account, []))
        try:
            videos = list_videos(account)
        except Exception as e:
            print(f"  Failed to list videos for {account}: {e}")
            continue

        new_videos = [v for v in videos if v.get("id") not in seen_ids]
        if not new_videos:
            print("  Nothing new.")
            continue

        for video in reversed(new_videos):  # oldest new video first
            vid_id = video.get("id")
            url = video.get("url") or video.get("webpage_url")
            title = (video.get("title") or vid_id)[:150]
            print(f"  New video: {vid_id} — downloading...")

            out_template = DOWNLOAD_DIR / f"{vid_id}.%(ext)s"
            ok = download_video(url, out_template)
            if not ok:
                print(f"  Could not download {vid_id}, will retry next run.")
                continue

            downloaded_files = list(DOWNLOAD_DIR.glob(f"{vid_id}.*"))
            if not downloaded_files:
                continue
            video_file = downloaded_files[0]

            sent = send_to_telegram(video_file, caption=f"{account}\n{title}")
            if sent:
                print(f"  Sent {vid_id} to Telegram.")
            else:
                print(f"  Could not send {vid_id} to Telegram.")

            video_file.unlink(missing_ok=True)
            seen_ids.add(vid_id)

        seen[account] = list(seen_ids)

    save_seen(seen)


if __name__ == "__main__":
    sys.exit(main())
