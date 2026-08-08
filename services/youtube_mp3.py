import json
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Any

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from services.youtube_parser import YouTubeParseError, is_youtube_url

logger = logging.getLogger(__name__)

MEDIA_DIR = Path(__file__).resolve().parent.parent / "media" / "youtube"
FILE_TTL_SECONDS = 60 * 60  # 1 hour
MP3_QUALITY = "192"


def _sanitize_filename(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title).strip()
    cleaned = re.sub(r"\s+", " ", cleaned) or "download"
    return f"{cleaned[:180]}.mp3"


def _metadata_path(file_id: str) -> Path:
    return MEDIA_DIR / f"{file_id}.json"


def _mp3_path(file_id: str) -> Path:
    return MEDIA_DIR / f"{file_id}.mp3"


def cleanup_expired_mp3_files(ttl_seconds: int = FILE_TTL_SECONDS) -> int:
    if not MEDIA_DIR.exists():
        return 0

    removed = 0
    cutoff = time.time() - ttl_seconds
    for meta_path in MEDIA_DIR.glob("*.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            created_at = float(meta.get("created_at", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            created_at = meta_path.stat().st_mtime

        if created_at > cutoff:
            continue

        file_id = meta_path.stem
        for path in (meta_path, _mp3_path(file_id)):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to delete expired file: %s", path)
        removed += 1

    if removed:
        logger.info("Cleaned up expired MP3 files: count=%d", removed)
    return removed


def get_mp3_file(file_id: str) -> tuple[Path, str] | None:
    if not re.fullmatch(r"[0-9a-f]{32}", file_id):
        return None

    mp3_path = _mp3_path(file_id)
    meta_path = _metadata_path(file_id)
    if not mp3_path.is_file() or not meta_path.is_file():
        return None

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        created_at = float(meta.get("created_at", 0))
        filename = str(meta.get("filename") or f"{file_id}.mp3")
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None

    if created_at and time.time() - created_at > FILE_TTL_SECONDS:
        mp3_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
        return None

    return mp3_path, filename


def download_youtube_as_mp3(url: str) -> dict[str, Any]:
    """
    Download a YouTube video's audio, convert it to MP3 with ffmpeg via yt-dlp,
    and store it for temporary download from this API.
    """
    if not is_youtube_url(url):
        raise YouTubeParseError(
            "Invalid YouTube URL. Only YouTube video, music, or shorts URLs are supported."
        )

    cleanup_expired_mp3_files()
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex
    work_dir = MEDIA_DIR / f".tmp-{file_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(work_dir / "%(id)s.%(ext)s")

    # Matches yt-dlp preset `-t mp3`: bestaudio preferring mp3, then extract/convert.
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "format": "ba[acodec^=mp3]/ba/b",
        "outtmpl": outtmpl,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": MP3_QUALITY,
            }
        ],
    }

    logger.info("Starting YouTube MP3 conversion: url=%s file_id=%s", url, file_id)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise YouTubeParseError("No metadata returned for this URL")
            if info.get("_type") == "playlist":
                raise YouTubeParseError(
                    "Playlist URLs are not supported. Provide a single video URL."
                )
            safe = ydl.sanitize_info(info) or {}
    except YouTubeParseError:
        _cleanup_work_dir(work_dir)
        raise
    except (DownloadError, ExtractorError) as exc:
        _cleanup_work_dir(work_dir)
        logger.error("yt-dlp MP3 conversion failed: url=%s error=%s", url, exc)
        message = str(exc)
        if "ffmpeg" in message.lower() or "ffprobe" in message.lower():
            raise YouTubeParseError(
                "MP3 conversion requires ffmpeg/ffprobe to be installed on the server."
            ) from exc
        raise YouTubeParseError(message) from exc
    except Exception as exc:
        _cleanup_work_dir(work_dir)
        logger.exception("Unexpected MP3 conversion failure: url=%s", url)
        raise YouTubeParseError(f"MP3 conversion failed: {exc}") from exc

    mp3_files = list(work_dir.glob("*.mp3"))
    if not mp3_files:
        _cleanup_work_dir(work_dir)
        raise YouTubeParseError("MP3 conversion finished but no MP3 file was produced")

    source_mp3 = mp3_files[0]
    title = str(safe.get("title") or safe.get("fulltitle") or "Unknown title")
    filename = _sanitize_filename(title)
    dest_mp3 = _mp3_path(file_id)
    dest_meta = _metadata_path(file_id)

    try:
        source_mp3.replace(dest_mp3)
        dest_meta.write_text(
            json.dumps(
                {
                    "file_id": file_id,
                    "title": title,
                    "filename": filename,
                    "video_id": safe.get("id"),
                    "created_at": time.time(),
                    "filesize": dest_mp3.stat().st_size,
                }
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        _cleanup_work_dir(work_dir)
        dest_mp3.unlink(missing_ok=True)
        dest_meta.unlink(missing_ok=True)
        raise YouTubeParseError(f"Failed to store MP3 file: {exc}") from exc
    finally:
        _cleanup_work_dir(work_dir)

    filesize = dest_mp3.stat().st_size
    logger.info(
        "YouTube MP3 conversion completed: file_id=%s title=%r filesize=%d",
        file_id,
        title,
        filesize,
    )

    return {
        "file_id": file_id,
        "title": title,
        "filename": filename,
        "ext": "mp3",
        "filesize": filesize,
        "expires_in_seconds": FILE_TTL_SECONDS,
    }


def _cleanup_work_dir(work_dir: Path) -> None:
    if not work_dir.exists():
        return
    for path in work_dir.iterdir():
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Failed to delete temp file: %s", path)
    try:
        work_dir.rmdir()
    except OSError:
        logger.warning("Failed to remove temp dir: %s", work_dir)
