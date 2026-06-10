import logging
from typing import Any

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from schemas.youtube import AudioFormat, ParseYouTubeResponse

logger = logging.getLogger(__name__)

MAX_AUDIO_FORMATS = 5

YDL_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "format": "ba/bestaudio/best",
}


class YouTubeParseError(Exception):
    pass


def _is_audio_format(fmt: dict[str, Any]) -> bool:
    if not fmt.get("url"):
        return False

    vcodec = fmt.get("vcodec")
    acodec = fmt.get("acodec")

    if vcodec == "none":
        return acodec not in (None, "none")

    return acodec not in (None, "none") and vcodec in (None, "none")


def _bitrate(fmt: dict[str, Any]) -> float:
    for key in ("abr", "tbr"):
        value = fmt.get(key)
        if value is not None:
            return float(value)
    return 0.0


def _to_audio_format(fmt: dict[str, Any]) -> AudioFormat:
    headers = fmt.get("http_headers") or {}
    return AudioFormat(
        format_id=str(fmt.get("format_id", "")),
        ext=str(fmt.get("ext", "")),
        url=str(fmt["url"]),
        abr=fmt.get("abr"),
        filesize=fmt.get("filesize"),
        filesize_approx=fmt.get("filesize_approx"),
        acodec=fmt.get("acodec"),
        protocol=fmt.get("protocol"),
        http_headers={str(k): str(v) for k, v in headers.items()},
    )


def _pick_thumbnail(info: dict[str, Any]) -> str | None:
    thumbnail = info.get("thumbnail")
    if thumbnail:
        return str(thumbnail)

    thumbnails = info.get("thumbnails") or []
    if thumbnails:
        return str(thumbnails[-1].get("url"))

    return None


def parse_youtube_url(url: str) -> ParseYouTubeResponse:
    logger.info("Starting YouTube extraction: url=%s", url)

    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                logger.error("yt-dlp returned no metadata: url=%s", url)
                raise YouTubeParseError("No metadata returned for this URL")

            safe = ydl.sanitize_info(info)
    except (DownloadError, ExtractorError) as exc:
        logger.error("yt-dlp extraction failed: url=%s error=%s", url, exc)
        raise YouTubeParseError(str(exc)) from exc

    if not safe:
        logger.error("Failed to sanitize yt-dlp metadata: url=%s", url)
        raise YouTubeParseError("Failed to sanitize metadata for this URL")

    if safe.get("_type") == "playlist":
        logger.warning("Playlist URL rejected: url=%s", url)
        raise YouTubeParseError("Playlist URLs are not supported. Provide a single video URL.")

    formats = safe.get("formats") or []
    audio_formats = sorted(
        (_to_audio_format(fmt) for fmt in formats if _is_audio_format(fmt)),
        key=lambda fmt: _bitrate({"abr": fmt.abr, "tbr": None}),
        reverse=True,
    )[:MAX_AUDIO_FORMATS]

    if not audio_formats:
        logger.error("No audio formats found: url=%s total_formats=%d", url, len(formats))
        raise YouTubeParseError("No downloadable audio formats found for this URL")

    video_id = str(safe.get("id", ""))
    title = str(safe.get("title") or safe.get("fulltitle") or "Unknown title")
    webpage_url = str(safe.get("webpage_url") or url)

    logger.info(
        "YouTube extraction completed: id=%s title=%r audio_formats=%d recommended=%s",
        video_id,
        title,
        len(audio_formats),
        audio_formats[0].format_id,
    )

    return ParseYouTubeResponse(
        id=video_id,
        title=title,
        uploader=safe.get("uploader"),
        channel=safe.get("channel"),
        duration=safe.get("duration"),
        thumbnail=_pick_thumbnail(safe),
        webpage_url=webpage_url,
        recommended_format_id=audio_formats[0].format_id,
        audio_formats=audio_formats,
    )
